#!/usr/bin/env python

"""The setup script."""

from setuptools import find_packages, setup

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = ["httpx"]

test_requirements = []

setup(
    author="Reinier Hernández",
    author_email='sasuke.reinier@gmail.com',
    python_requires='>=3.7',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
    description="Non official, but friendly CryptoBot library for the Python language",
    install_requires=requirements,
    license="MIT license",
    long_description=readme + '\n\n' + history,
    include_package_data=True,
    keywords='cryptobot',
    name='cryptobot_python',
    packages=find_packages(where='.', exclude=['tests', '*.tests', '*.tests.*', 'tests.*']),
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/ragnarok22/cryptobot_python',
    version='0.1.0',
    zip_safe=False,
)
