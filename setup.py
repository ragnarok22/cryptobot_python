#!/usr/bin/env python

"""The setup script."""

from setuptools import find_packages, setup

from cryptobot import __author__, __email__, __version__

with open("README.md") as readme_file:
    readme = readme_file.read()

with open("HISTORY.md") as history_file:
    history = history_file.read()

requirements = ["httpx"]

test_requirements = []

setup(
    author=__author__,
    author_email=__email__,
    python_requires=">=3.7",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    description="Non official, but friendly CryptoBot library for the Python language",
    install_requires=requirements,
    license="MIT license",
    long_description=readme + "\n\n" + history,
    long_description_content_type="text/markdown",
    include_package_data=True,
    keywords="cryptobot",
    name="cryptobot_python",
    packages=find_packages(
        where=".", exclude=["tests", "*.tests", "*.tests.*", "tests.*"]
    ),
    test_suite="tests",
    tests_require=test_requirements,
    url="https://github.com/ragnarok22/cryptobot_python",
    version=__version__,
    zip_safe=False,
)
