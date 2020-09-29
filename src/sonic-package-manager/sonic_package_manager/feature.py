#!/usr/bin/env python

''' This module implements the logic of feature registration and deregistration in CONFIG DB. '''

import os
import json

import swsssdk

from sonic_package_manager.errors import PackageInstallationError
from sonic_package_manager.logger import get_logger

from sonic_package_manager.common import run_command


FEATURE_TABLE_NAME = 'FEATURE'


def register_feature(connector, repo, version):
    ''' Register new feature package.

    Args:
        connector (swsssdk.ConfigDBConnector): Config DB connector
        repository (Repository): Repository object.
        version (str): SONiC package version to install.
    '''

    _update_running_config(connector, repo, version)

    get_logger().info('Registered feature: {}'.format(
        repo.get_package().get_feature_name()))

    # TODO: instead of config save, we could update only
    #       needed tables in /etc/sonic/config_db.json
    run_command('config save -y')


def deregister_feature(connector, repo, version):
    ''' Unregister new feature package.

    Args:
        connector (swsssdk.ConfigDBConnector): Config DB connector
        repository (Repository): Repository object.
        version (str): SONiC package version to install.
    '''

    _update_running_config(connector, repo, version, remove=True)

    get_logger().info('Deregistered feature: {}'.format(
        repo.get_package().get_feature_name()))

    # TODO: instead of config save, we could update only
    #       needed tables in /etc/sonic/config_db.json
    run_command('config save -y')


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


def _update_running_config(conn, repo, version, remove=False):
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
    table, key, entries = _get_feature_default_configuration(package)

    if not remove:
        conn.mod_entry(table, key, entries)
    else:
        entries = conn.get_entry(table, key)
        if entries.get('state', '') == 'enabled':
            raise PackageInstallationError('Package feature is enabled, cannot remove. Disable the feature first.')
        conn.set_entry(FEATURE_TABLE_NAME, package.get_feature_name(), None)
