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
    install_requires = [
        'jinja2>=2.10',
        'pyyaml',
        'click',
        'docker',
        'sonic-py-common',
        'swsssdk',
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
    entry_points={
        'console_scripts': [
            'sonic-package-manager = sonic_package_manager.main:cli',
            'spm = sonic_package_manager.main:cli',
         ]
    }
)

