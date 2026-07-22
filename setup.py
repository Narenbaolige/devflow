"""Minimal setup.py for editable install."""
from setuptools import setup, find_packages

setup(
    name="devflow",
    version="0.1.0",
    packages=find_packages(),
    python_requires=">=3.11",
)
