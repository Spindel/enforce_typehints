import sys
from types import ModuleType
from importlib.machinery import ModuleSpec
from importlib.abc import MetaPathFinder, Loader
from importlib.machinery import PathFinder
from importlib.machinery import FileFinder

import mypy.api

import importlib.machinery


def mypy_self():
    """Run mypy on this file.

    This is needed to run and make mypy load dependencies early on before we
    hook too much of the importer, otherwise we will import things while we
    import things, which is definitely going to cause some pain.
    """
    print(f"Priming mypy on {__file__}")
    result = mypy.api.run(["--strict", __file__])
    print(result)


class SpamMetaPathFinder(PathFinder):
    @classmethod
    def find_spec(cls, fullname, path, target=None):
        print(f"Meta Path Finder:{cls} {fullname}, {path}, {target}")
        res = PathFinder.find_spec(fullname, path, target)
        if res is None:
            return res
        if res.name in sys.builtin_module_names:
            return res
        if res.name in sys.stdlib_module_names:
            return res
        if res.parent in sys.stdlib_module_names:
            return res
        if res and res.has_location and res.origin and res.origin.endswith("py"):
            filename = str(res.origin)
            print(
                res,
                dir(res),
                res.parent,
                res.origin,
                res.submodule_search_locations,
                res.parent,
            )
            print(f"about to execute mypy.api.run([{filename}])")
            checked = mypy.api.run(["--strict", filename])
            print(checked)
        return res


class SpamPathEntryFinder(FileFinder):
    # This isn't used at all here, but hey
    def find_spec(self, fullname, target):
        print(f"Spam Entry Finder {self}, {fullname}, {target}")
        res = super().find_spec(fullname, target)
        print(f"Spam result {res}")
        return res


loader_details = (
    importlib.machinery.SourceFileLoader,
    importlib.machinery.SOURCE_SUFFIXES,
)

print("hooks before")
print(sys.path_hooks)
print(sys.meta_path)
mypy_self()

sys.meta_path.insert(0, SpamMetaPathFinder)
sys.path_hooks.append(SpamPathEntryFinder.path_hook(loader_details))

# force to use the hook
sys.path_importer_cache.clear()

print("hooks after")
print(sys.path_hooks)
print(sys.meta_path)
print("module done")
