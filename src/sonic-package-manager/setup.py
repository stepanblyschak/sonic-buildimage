#!/usr/bin/env python

from setuptools import setup
import glob

setup(
    name='sonic-package-manager',
    version='1.0',
    description='SONiC Package Manager',
    author='Stepan Blyshchak',
    author_email='stepanb@nvidia.com',
    url='https://github.com/Azure/sonic-buildimage',
    data_files=[
        ('/usr/share/sonic/templates', glob.glob('templates/*')),
    ],
    packages=[
        'sonic_package_manager',
    ],
    python_requires='>=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*',
    classifiers = [
        'Intended Audience :: Developers',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
)

