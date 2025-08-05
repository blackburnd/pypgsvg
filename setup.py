from setuptools import setup, find_packages

setup(
    name="pypgsvg-erd-generator",
    version="1.0.07",
    description="Python ERD Generator from SQL dumps using Graphviz",
    author="blackburnd@gmail.com",
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
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    ],
)
