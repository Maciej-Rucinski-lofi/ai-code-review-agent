"""Verify project package structure imports."""

import importlib

MODULES = [
    "app",
    "app.api",
    "app.collector",
    "app.analysis",
    "app.benchmark",
    "app.database",
]


def test_all_modules_import() -> None:
    """Each top-level application module should be importable."""
    for module_name in MODULES:
        module = importlib.import_module(module_name)
        assert module is not None
