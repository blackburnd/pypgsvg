#!/usr/bin/env python3
"""
Setup script for pypgsvg ERD Generator
"""

from setuptools import setup, find_packages
import os

# Read the README file for long description
def read_readme():
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "A PostgreSQL database schema to SVG ERD generator"

setup(
    name="pypgsvg",
    version="1.0.0",
    author="Daniel Blackburn",
    author_email="daniel@example.com",
    description="Generate SVG Entity Relationship Diagrams from PostgreSQL database dumps",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/danielblackburn/pypgsvg",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Database",
        "Topic :: Documentation",
        "Topic :: Software Development :: Documentation",
        "Topic :: Utilities",
    ],
    python_requires=">=3.8",
    install_requires=[
        "graphviz>=0.20.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=22.0.0",
            "flake8>=4.0.0",
            "mypy>=1.0.0",
        ],
        "test": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "pypgsvg=pypgsvg:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
    keywords="postgresql database erd diagram svg graphviz schema visualization",
    project_urls={
        "Bug Reports": "https://github.com/danielblackburn/pypgsvg/issues",
        "Source": "https://github.com/danielblackburn/pypgsvg",
        "Documentation": "https://github.com/danielblackburn/pypgsvg#readme",
    },
)
