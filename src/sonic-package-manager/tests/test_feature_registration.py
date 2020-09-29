#!/usr/bin/env python

import pytest
import mock
import swsssdk

from sonic_package_manager import feature
from sonic_package_manager.repository import Repository
from sonic_package_manager.package import Package
from sonic_package_manager.errors import *


def test_feature_installation_no_feature_config():
    conn = mock.Mock(swsssdk.ConfigDBConnector)
    repo = mock.Mock(Repository)
    package = mock.Mock(Package)
    feature.run_command = mock.Mock()

    package.get_feature_name = mock.MagicMock(return_value='test')
    repo.get_package = mock.MagicMock(return_value=package)

    version = '1.0.0'
    conn.get_entry = mock.Mock(return_value={})
    feature.register_feature(conn, repo, version)
    conn.mod_entry.assert_called_once_with('FEATURE', 'test',
        {'state': 'disabled',
         'has_timer': False,
         'auto_restart': 'enabled',
         'high_mem_alert': 'disabled'}
    )


def test_feature_installation_existing_feature_config():
    conn = mock.Mock(swsssdk.ConfigDBConnector)
    repo = mock.Mock(Repository)
    package = mock.Mock(Package)
    feature.run_command = mock.Mock()

    package.get_feature_name = mock.MagicMock(return_value='test')
    repo.get_package = mock.MagicMock(return_value=package)

    version = '1.0.0'
    conn.get_entry = mock.Mock(return_value={'FEATURE': {'test': {}}})
    feature.register_feature(conn, repo, version)
    conn.mod_entry.assert_not_called()


def test_feature_uninstallation():
    conn = mock.Mock(swsssdk.ConfigDBConnector)
    repo = mock.Mock(Repository)
    package = mock.Mock(Package)
    feature.run_command = mock.Mock()

    package.get_feature_name = mock.MagicMock(return_value='test')
    repo.get_package = mock.MagicMock(return_value=package)

    version = '1.0.0'
    feature.deregister_feature(conn, repo, version)
    conn.set_entry.assert_called_once_with('FEATURE', 'test', None)


def test_feature_uninstallation_when_feature_is_enabled():
    conn = mock.Mock(swsssdk.ConfigDBConnector)
    repo = mock.Mock(Repository)
    package = mock.Mock(Package)
    feature.run_command = mock.Mock()

    package.get_feature_name = mock.MagicMock(return_value='test')
    repo.get_package = mock.MagicMock(return_value=package)
    conn.get_entry = mock.Mock(return_value={'state': 'enabled'})

    version = '1.0.0'
    with pytest.raises(PackageInstallationError):
        feature.deregister_feature(conn, repo, version)

