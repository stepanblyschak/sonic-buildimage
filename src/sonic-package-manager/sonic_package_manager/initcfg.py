#!/usr/bin/env python

''' This module implements the logic of feature registration and deregistration in CONFIG DB. '''

import os
import json

import swsssdk

from sonic_package_manager.errors import PackageInstallationError
from sonic_package_manager.logger import get_logger

from sonic_package_manager.common import (
    get_package_metadata_folder,
)


FEATURE_TABLE_NAME = 'FEATURE'


def load_default_config(connector, repo, version):
    ''' Register new feature package.

    Args:
        connector (swsssdk.ConfigDBConnector): Config DB connector
        repository (Repository): Repository object.
        version (str): SONiC package version to install.
    '''

    _update_running_config(connector, repo, version)
    _update_startup_config(repo, version)

    get_logger().info('Registered feature: {}'.format(
        repo.get_package().get_feature_name()))


def _get_feature_default_configuration(package):
    ''' Returns default feature configuration.

    Args:
        package (Package): Package object.

    Returns:
        Tuple (table (str), key (str), entries (entries))
    '''

    table   = FEATURE_TABLE_NAME
    key     = package.get_feature_name()
    entries = dict(state='disabled',
                    has_timer=False, # TODO: include timer if needed
                    auto_restart='enabled',
                    high_mem_alert='disabled')

    return table, key, entries


def _update_running_config(conn, repo):
    ''' Update running configuration database with new feature package.

    Args:
        connector (swsssdk.ConfigDBConnector): Config DB connector
        repository (Repository): Repository object.
        version    (str)       : SONiC package version to install.
        remove     (bool)      : If true, removes feature from DB, othewise adds.
    Raises:
        PackageInstallationError: raises when feature gets removed, but in
                                    config db it is enabled.
    '''

    package = repo.get_package()
    init_cfg = package.get_manifest().get('init-config')
    if init_cfg is None:
        return

    init_cfg = os.path.join(get_package_metadata_folder(package), init_cfg)

    run_command('sonic-cfggen -j {} --from-db --write-to-db'.format(init_cfg))
    run_command('sonic-cfggen -j {} -j {} --write-to-db'.format(init_cfg, '/etc/sonic/.json'))
    


    table, key, entries = _get_feature_default_configuration(package)

    if not remove:
        conn.mod_entry(table, key, entries)
    else:
        entries = conn.get_entry(table, key)
        if entries.get('state', '') == 'enabled':
            raise PackageInstallationError('Package feature is enabled, cannot remove. Disable the feature first.')
        conn.set_entry(FEATURE_TABLE_NAME, package.get_feature_name(), None)


def _update_persistent_config_file(filepath, repo, remove=False):
    ''' Update configuration file cfgfile with new feature package.

    Args:
        filepath   (str)       : file path to update.
        repository (Repository): Repository object.
        remove     (bool)      : If true, removes feature from DB, othewise adds.
    '''

    package = repo.get_package()

    with open(filepath, 'r+') as cfgfile:
        cfg = json.load(cfgfile)

        table, key, entries = _get_feature_default_configuration(package)

        if not remove:
            cfg.update({
                '{}{}{}'.format(table, swsssdk.ConfigDBConnector.TABLE_NAME_SEPARATOR, key): entries
            })
        else:
            try:
                cfg.pop('{}{}{}'.format(table, swsssdk.ConfigDBConnector.TABLE_NAME_SEPARATOR, key))
            except KeyError:
                pass

        cfgfile.seek(0)
        cfgfile.truncate()

        json.dump(cfg, cfgfile)

def _update_startup_config(repo, version, remove=False):
    ''' Update startup configuration database with new feature package.

    Args:
        repository (Repository): Repository object.
        version    (str)       : SONiC package version to install.
        remove     (bool)      : If true, removes feature from DB, othewise adds.
    '''

    for filepath in ('/etc/sonic/config_db.json', '/etc/sonic/init_cfg.json'):
        _update_persistent_config_file(filepath, repo, remove)
