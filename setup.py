"""Compatibility entry point for editable installs.

Project metadata and dependencies live exclusively in ``pyproject.toml``.
Duplicating them here caused legacy editable installs to omit runtime
dependencies and leave incompatible LangChain packages in the environment.
"""
from setuptools import find_packages, setup

setup(packages=find_packages())
