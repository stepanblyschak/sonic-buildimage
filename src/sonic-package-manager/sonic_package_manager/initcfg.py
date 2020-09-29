#!/usr/bin/env python

''' This module implements the logic of feature registration and deregistration in CONFIG DB. '''

import os
import json

import swsssdk

from sonic_package_manager.errors import PackageInstallationError
from sonic_package_manager.logger import get_logger

from sonic_package_manager.common import (
    get_package_metadata_folder,
    run_command,
)


FEATURE_TABLE_NAME = 'FEATURE'


def load_default_config(repo):
    ''' Register new feature package.

    Args:
        repository (Repository): Repository object.
        version (str): SONiC package version to install.
    '''

    package = repo.get_package()
    package_props = package.get_manifest().get('package', dict())
    init_cfg = package_props.get('initial-config')
    if init_cfg is None:
        return

    init_cfg = os.path.join(get_package_metadata_folder(repo), init_cfg)

    run_command('sonic-cfggen -j {} --write-to-db'.format(init_cfg))

    # TODO: instead of config save, we could update only
    #       needed tables in /etc/sonic/config_db.json
    run_command('config save -y')
