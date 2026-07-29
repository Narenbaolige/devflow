"""Minimal setup.py for editable install."""
from setuptools import find_packages, setup

setup(
    name="devflow",
    version="0.1.0",
    packages=find_packages(),
    python_requires=">=3.11",
)
