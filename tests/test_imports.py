import importlib
import pkgutil

import pytest


@pytest.mark.parametrize(
    "module_name", [name for _, name, _ in pkgutil.walk_packages(["app"])]
)
def test_import_module(module_name):
    """Ensure every submodule in app/ can be imported without side-effects errors."""
    importlib.import_module(f"app.{module_name}")
