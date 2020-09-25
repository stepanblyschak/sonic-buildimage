#!/usr/bin/env python

import json
import os

import yaml

from sonic_package_manager import common
from sonic_package_manager.errors import PackageManagerError


def get_manifest(package):
    ''' Reads the content of package manifest.

    Args:
        package (PackageEntry): SONiC Package Database Entry.
    Returns:
        dict: manifest file content.
    Raises:
        PackageManagerError: if failed to read manifest.
    '''

    name         = package.get_name()
    package_path = common.get_package_metadata_folder(package)

    manifests_locations = [
        os.path.join(package_path, 'manifest.json'),
        os.path.join(package_path, 'manifest.yml'),
        os.path.join(package_path, 'manifest.yaml'),
    ]

    for manifest in manifests_locations:
        try:
            with open(manifest) as stream:
                if manifest.endswith('.json'):
                    return json.load(stream)
                else:
                    return yaml.safe_load(stream)
        except IOError:
            continue

    raise PackageManagerError("Failed to locate manifest file for {}".format(name))
