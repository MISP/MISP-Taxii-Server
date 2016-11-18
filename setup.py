#!/usr/bin/env python3

# Setup script for ThreatIntel Conversion

from setuptools import setup
import os

setup(
    name="misp_taxii_hooks",
    description="A little package just to install hooks to PYTHONPATH",
    version="0.1",
    author="Hannah Ward",
    author_email="hannah.ward2@baesystems.com",
    packages=['misp_taxii_hooks'],
    install_requires=["pymisp>=2.4.53", "pyaml>=3.11", "cabby>=0.1", "nose>=1.3.7"],
)

