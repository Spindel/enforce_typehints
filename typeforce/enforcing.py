"""Enforce mypy type checks at _runtime_ when code is imported.

This uses runtime interception of the module loaders in order to run mypy on
code before it gets loaded into the program.
This causes huge delays when importing something, and is questionable behaviour
at best, but I can do it so I did.
"""
import sys
import logging

from typing import Sequence, Union
from types import ModuleType
from importlib.machinery import ModuleSpec
from importlib.abc import MetaPathFinder
import importlib.machinery

import mypy.api


_LOG = logging.getLogger(__name__)

_Path = Union[bytes, str]


def mypy_self() -> None:
    """Run mypy on this file.

    This is needed to run and make mypy load dependencies early on before we
    hook too much of the importer, otherwise we will import things while we
    import things, which is definitely going to cause some pain.
    """
    mypy_run_file(__file__, strict=False)


class ImportTypeError(ImportError):
    """Type error when importing file."""


def mypy_run_file(filename: str, *, strict: bool) -> None:
    """Run mypy on the filename."""
    _LOG.debug("Running mypy on %s", filename)
    argv = []
    if strict:
        argv.append("--strict")
    argv.append(filename)
    result = mypy.api.run(argv)
    if result[-1] != 0:
        _LOG.error("mypy report stdout: %s", result[0])
        _LOG.error("mypy report stderr: %s", result[1])
        raise ImportTypeError("Type error on file", filename, result[0])


def mypy_run_module(module: str, *, strict: bool) -> None:
    """Run mypy on the filename."""
    _LOG.debug("Running mypy on %s", module)
    argv = []
    if strict:
        argv.append("--strict")
    argv.append("-m")
    argv.append(module)
    result = mypy.api.run(argv)
    if result[-1] != 0:
        _LOG.error("mypy report stdout: %s", result[0])
        _LOG.error("mypy report stderr: %s", result[1])
        raise ImportTypeError("Type error on file", module, result[0])


def maybe_run_mypy(spec: ModuleSpec | None) -> None:
    """Checks if res is something we should run mypy on, and does it."""
    ignore = {
        "_virtualenv",
        "_distutils_hack",
        "mypy",
    }
    if spec is None:
        return
    if spec.name in sys.builtin_module_names:
        return
    if spec.name in sys.stdlib_module_names:
        return
    if spec.parent in sys.stdlib_module_names:
        return
    # Ignore private/hidden packages
    if "._" in spec.name or spec.name.startswith("_"):
        return

    if spec.name in ignore:
        return
    if (
        spec
        and spec.has_location
        and spec.origin
        and spec.origin.endswith("py")
    ):
        filename = str(spec.origin)
        _LOG.debug(
            "name=%s parent=%s, filename=%s, locations=%s",
            spec.name,
            spec.parent,
            filename,
            spec.submodule_search_locations,
        )
        # Technically we could do something better here.
        # But this is good enough
        if "site-packages" in filename:
            _LOG.debug("Parsing %s as a module", spec.name)
            mypy_run_module(spec.name, strict=False)
        else:
            _LOG.debug("Parsing %s as a file", filename)
            mypy_run_file(filename, strict=True)


class TypeMetaPathFinder(MetaPathFinder):
    """A meta path locator that type checks imported files before
    continuing."""

    @classmethod
    def find_spec(
        cls,
        fullname: str,
        path: Sequence[_Path] | None,
        target: ModuleType | None = None,
    ) -> ModuleSpec | None:
        """Find a module spec, just wraps a standard PathFinder object"""
        _LOG.debug(
            "looking for:fullname=%s, path=%s, target=%s",
            fullname,
            path,
            target,
        )
        res = importlib.machinery.PathFinder.find_spec(fullname, path, target)
        maybe_run_mypy(res)
        return res


class TypePathEntryFinder(importlib.machinery.FileFinder):
    """A path entry finder that also type checks."""

    def find_spec(
        self, fullname: str, target: ModuleType | None = None
    ) -> ModuleSpec | None:
        _LOG.debug("looking for:fullname=%s, target=%s", fullname, target)
        res = super().find_spec(fullname, target)
        # print(f"Type Path result {res}")
        maybe_run_mypy(res)
        return res


def install_hooks() -> None:
    """Install the hooks in the running program."""
    loader_details = (
        importlib.machinery.SourceFileLoader,
        importlib.machinery.SOURCE_SUFFIXES,
    )
    # there is a bug in the type hints for FileLoader and subclasses
    # see https://github.com/python/typeshed/issues/7085
    hook = TypePathEntryFinder.path_hook(loader_details)  # type: ignore

    # print("Path hooks before", sys.path_hooks)
    # print("Meta finders before", sys.meta_path)

    sys.meta_path.insert(0, TypeMetaPathFinder())
    sys.path_hooks.append(hook)
    # print("Path hooks after", sys.path_hooks)
    # print("Meta finders after", sys.meta_path)


def check_all_loaded() -> None:
    """Type check all loaded modules."""
    modules = list(sys.modules.values())
    for mod in modules:
        if hasattr(mod, "__spec__"):
            spec = mod.__spec__
            try:
                maybe_run_mypy(spec)
            except ImportError:
                print(spec)
                raise


mypy_self()
install_hooks()
# force to use the hook
sys.path_importer_cache.clear()
