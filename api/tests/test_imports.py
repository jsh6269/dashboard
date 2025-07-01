import importlib
import pkgutil

import pytest


@pytest.mark.parametrize(
    "module_name", [name for _, name, _ in pkgutil.walk_packages(["."])]
)
def test_import_module(module_name):
    """Ensure every submodule in api/ can be imported without side-effects errors."""
    importlib.import_module(f"{module_name}")
