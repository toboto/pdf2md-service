#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(
    name="pdf2md",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "requests",
        "oss2",
        "pyyaml",
    ]
) 