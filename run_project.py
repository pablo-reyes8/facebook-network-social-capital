#!/usr/bin/env python3
"""Punto de entrada del pipeline completo."""
import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).resolve().parent / "src" / "run_all.py"), run_name="__main__")
