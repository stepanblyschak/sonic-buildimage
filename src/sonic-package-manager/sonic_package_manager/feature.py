#!/usr/bin/env python

""" This module implements the logic of feature registration and de-registration in CONFIG DB. """

import typing

import swsssdk

from sonic_package_manager import common
from sonic_package_manager import package
from sonic_package_manager import repository
from sonic_package_manager.logger import get_logger

FEATURE_TABLE_NAME = 'FEATURE'


def register(connector: swsssdk.ConfigDBConnector,
             repo: repository.Repository):
    """ Register new feature package.

    Args:
        connector: Config DB connector.
        repo: Repository object.
    """

    pkg = repo.get_package()
    table = FEATURE_TABLE_NAME
    key = pkg.get_feature_name()
    cfg_entries = get_configurable_feature_entries(pkg)
    non_cfg_entries = get_non_configurable_feature_entries(pkg)

    connector.connect()

    running_cfg = connector.get_entry(table, key)

    cfg = cfg_entries.copy()
    # Override configurable entries with CONFIG DB data.
    cfg.update(running_cfg)
    # Override CONFIG DB data with non configurable entries.
    cfg.update(non_cfg_entries)

    connector.mod_entry(table, key, cfg)

    common.run_command('config save -y')

    get_logger().info(f'Registered feature: {key}')


def deregister(connector: swsssdk.ConfigDBConnector,
               repo: repository.Repository):
    """ Register new feature package.

    Args:
        connector: Config DB connector.
        repo: Repository object.
    """

    pkg = repo.get_package()
    table = FEATURE_TABLE_NAME
    key = pkg.get_feature_name()

    connector.connect()
    connector.set_entry(table, key, None)

    # TODO: update persistent config db seperately
    common.run_command('config save -y')

    get_logger().info(f'De-registered feature: {key}')


def get_configurable_feature_entries(pkg: package.Package) \
        -> typing.Dict[str, str]:
    """
    Get configurable feature table entries: e.g. 'state', 'auto_restart', etc..

    Args:
        pkg: Package object.

    Returns:
        Dictionary of field values.
    """

    return {
        'state': 'disabled',
        'auto_restart': 'enabled',
        'high_mem_alert': 'disabled',
    }


def is_feature_enabled(connector: swsssdk.ConfigDBConnector,
                       repository: repository.Repository) -> bool:
    """ Check if the feature is enabled or not.
    Args:
        connector: CONFIG DB connector.
        repository: Repository object.

    Returns:
        True if enabled, otherwise False.
    """

    connector.connect()
    name = repository.get_package().get_feature_name()
    state = connector.get_entry(FEATURE_TABLE_NAME, name).get('state')
    return state == 'enabled'


def get_non_configurable_feature_entries(pkg: package.Package) \
        -> typing.Dict[str, str]:
    """
    Get non-configurable feature table entries: e.g. 'has_timer'.

    Args:
        pkg: Package object.

    Returns:
        Dictionary of field values.
    """

    return {
        'has_per_asic_scope': str(pkg.is_asic_service()),
        'has_global_scope': str(pkg.is_host_service()),
        'has_timer': 'False',  # TODO: include timer if package requires
    }
