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


def mypy_self():
    """Run mypy on this file.

    This is needed to run and make mypy load dependencies early on before we
    hook too much of the importer, otherwise we will import things while we
    import things, which is definitely going to cause some pain.
    """
    mypy_run_file(__file__, strict=False)


class ImportTypeError(ImportError):
    """Type error when importing file."""


def mypy_run_file(filename: str, *, strict: bool):
    """Run mypy on the filename."""
    _LOG.debug(f"Running mypy on %s", filename)
    argv = []
    if strict:
        argv.append("--strict")
    argv.append(filename)
    result = mypy.api.run(argv)
    if result[-1] != 0:
        _LOG.error("mypy report stdout: %s", result[0])
        _LOG.error("mypy report stderr: %s", result[1])
        raise ImportTypeError("Type error on file", filename, result[0])


def maybe_run_mypy(spec):
    """Checks if res is something we should run mypy on, and does it."""
    if spec is None:
        return
    if spec.name in sys.builtin_module_names:
        return
    if spec.name in sys.stdlib_module_names:
        return
    if spec.parent in sys.stdlib_module_names:
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
    def find_spec(self, fullname, target=None):
        _LOG.debug("looking for:fullname=%s, target=%s", fullname, target)
        res = super().find_spec(fullname, target)
        # print(f"Type Path result {res}")
        maybe_run_mypy(res)
        return res


def install_hooks():
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


mypy_self()
install_hooks()
# force to use the hook
sys.path_importer_cache.clear()
