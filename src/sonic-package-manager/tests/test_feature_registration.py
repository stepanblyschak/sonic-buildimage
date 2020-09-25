#!/usr/bin/env python

import pytest
import mock
import swsssdk

from sonic_package_manager.errors import *
from sonic_package_manager.feature import *
from sonic_package_manager.repository import *
from sonic_package_manager.package import *


def test_feature_installation():
    conn = mock.Mock(swsssdk.ConfigDBConnector)
    repo = mock.Mock(Repository)
    package = mock.Mock(Package)

    package.get_feature_name = mock.MagicMock(return_value='test')
    repo.get_package = mock.MagicMock(return_value=package)

    version = '1.0.0'

    feature_installer = FeatureTableUpdater(conn)

    mopen = mock.mock_open(read_data='{}')
    with mock.patch('__builtin__.open', mopen, create=True):
        feature_installer.install(repo, version)

    conn.mod_entry.assert_called_once_with('FEATURE', 'test',
        {'state': 'disabled',
         'has_timer': False,
         'auto_restart': 'enabled',
         'high_mem_alert': 'disabled'}
    )


def test_feature_uninstallation():
    conn = mock.Mock(swsssdk.ConfigDBConnector)
    repo = mock.Mock(Repository)
    package = mock.Mock(Package)

    package.get_feature_name = mock.MagicMock(return_value='test')
    repo.get_package = mock.MagicMock(return_value=package)

    version = '1.0.0'

    feature_installer = FeatureTableUpdater(conn)

    mopen = mock.mock_open(read_data='{}')
    with mock.patch('__builtin__.open', mopen, create=True):
        feature_installer.uninstall(repo, version)

    conn.set_entry.assert_called_once_with('FEATURE', 'test', None)


def test_feature_uninstallation_when_feature_is_enabled():
    conn = mock.Mock(swsssdk.ConfigDBConnector)
    repo = mock.Mock(Repository)
    package = mock.Mock(Package)

    package.get_feature_name = mock.MagicMock(return_value='test')
    repo.get_package = mock.MagicMock(return_value=package)
    conn.get_entry = mock.Mock(return_value={'state': 'enabled'})

    version = '1.0.0'

    feature_installer = FeatureTableUpdater(conn)

    mopen = mock.mock_open(read_data='{}')
    with mock.patch('__builtin__.open', mopen, create=True):
        with pytest.raises(PackageInstallationError):
            feature_installer.uninstall(repo, version)

