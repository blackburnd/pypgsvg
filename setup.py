from setuptools import setup, find_packages

setup(
    name="pypgsvg",
    version="1.2.51",
    description="Lightweight PostgreSQL ERD generator with interactive SVG output",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="Daniel Blackburn",
    author_email="blackburnd@gmail.com",
    url="https://github.com/blackburnd/pypgsvg",
    project_urls={
        "Bug Tracker": "https://github.com/blackburnd/pypgsvg/issues",
        "Documentation": "https://github.com/blackburnd/pypgsvg#readme",
        "Source Code": "https://github.com/blackburnd/pypgsvg",
    },
    packages=find_packages(),
    install_requires=[
        "graphviz>=0.20.1",
    ],
    python_requires=">=3.8",
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "pytest-mock>=3.11.0",
        ]
    },
    entry_points={
        'console_scripts': [
            'pypgsvg=pypgsvg:main',
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Intended Audience :: Information Technology",
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
    keywords="postgresql erd entity-relationship-diagram database schema visualization graphviz svg",
)
