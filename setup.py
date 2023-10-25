#!/usr/bin/env python

from setuptools import find_packages, setup

setup(
    name="wagtail-transfer",
    version="0.9.1",
    description="Content transfer for Wagtail",
    author="Matthew Westcott",
    author_email="matthew.westcott@torchbox.com",
    url="https://github.com/wagtail/wagtail-transfer",
    packages=find_packages(exclude=("tests",)),
    include_package_data=True,
    install_requires=["wagtail>=4.1"],
    extras_require={
        "docs": [
            "mkdocs>=1.0,<1.1",
            "mkdocs-material>=4.6,<4.7",
        ],
        "dev": [
            "ruff>=1.2.0",
        ],
    },
    python_requires=">=3.7",
    license="BSD",
    long_description="An extension for Wagtail allowing content to be transferred between multiple instances of a Wagtail project",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Framework :: Django",
        "Framework :: Wagtail",
        "Framework :: Wagtail :: 4",
    ],
)
