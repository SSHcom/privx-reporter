"""Test package for reporter-privx-dev."""

from pathlib import Path

_python = Path(__file__).resolve().parent / "python"
if _python.is_dir():
    __path__.append(str(_python))
