#!/usr/bin/env python
from unittest import mock

import swsssdk

from sonic_package_manager import repository, package, common, feature


def test_feature_registration():
    repo = mock.Mock(repository.Repository)
    manifest = {'service': {'name': 'test_service',
                            'asic-service': True,
                            'host-service': False}}
    pkg = package.Package(manifest)
    repo.get_package = mock.Mock(return_value=pkg)
    connector = mock.MagicMock(swsssdk.ConfigDBConnector)
    common.run_command = mock.Mock()

    connector.get_entry = mock.Mock(return_value={})

    feature.register(connector, repo)

    connector.get_entry.assert_called_once_with(
        feature.FEATURE_TABLE_NAME,
        manifest['service']['name']
    )
    connector.mod_entry.assert_called_once_with(
        feature.FEATURE_TABLE_NAME,
        manifest['service']['name'],
        {'auto_restart': 'enabled',
         'has_global_scope': 'False',
         'has_per_asic_scope': 'True',
         'has_timer': 'False',
         'high_mem_alert': 'disabled',
         'state': 'disabled'}
    )


def test_feature_registration_exitsting_config():
    repo = mock.Mock(repository.Repository)
    manifest = {'service': {'name': 'test_service',
                            'asic-service': True,
                            'host-service': False}}
    pkg = package.Package(manifest)
    repo.get_package = mock.Mock(return_value=pkg)
    connector = mock.MagicMock(swsssdk.ConfigDBConnector)
    common.run_command = mock.Mock()

    connector.get_entry = mock.Mock(return_value={
        'state': 'enabled',
    })

    feature.register(connector, repo)

    connector.get_entry.assert_called_once_with(
        feature.FEATURE_TABLE_NAME,
        manifest['service']['name']
    )
    connector.mod_entry.assert_called_once_with(
        feature.FEATURE_TABLE_NAME,
        manifest['service']['name'],
        {'auto_restart': 'enabled',
         'has_global_scope': 'False',
         'has_per_asic_scope': 'True',
         'has_timer': 'False',
         'high_mem_alert': 'disabled',
         'state': 'enabled'}
    )


def test_feature_registration_exitsting_non_configurable():
    repo = mock.Mock(repository.Repository)
    manifest = {'service': {'name': 'test_service',
                            'asic-service': True,
                            'host-service': True}}
    pkg = package.Package(manifest)
    repo.get_package = mock.Mock(return_value=pkg)
    connector = mock.MagicMock(swsssdk.ConfigDBConnector)
    common.run_command = mock.Mock()

    connector.get_entry = mock.Mock(return_value={
        'has_global_scope': 'False',
        'has_per_asic_scope': 'True',
    })

    feature.register(connector, repo)

    connector.get_entry.assert_called_once_with(
        feature.FEATURE_TABLE_NAME,
        manifest['service']['name']
    )
    connector.mod_entry.assert_called_once_with(
        feature.FEATURE_TABLE_NAME,
        manifest['service']['name'],
        {'auto_restart': 'enabled',
         'has_global_scope': 'True',
         'has_per_asic_scope': 'True',
         'has_timer': 'False',
         'high_mem_alert': 'disabled',
         'state': 'disabled'}
    )


def test_feature_deregistration():
    repo = mock.Mock(repository.Repository)
    manifest = {'service': {'name': 'test_service',
                            'asic-service': True,
                            'host-service': True}}
    pkg = package.Package(manifest)
    repo.get_package = mock.Mock(return_value=pkg)
    connector = mock.MagicMock(swsssdk.ConfigDBConnector)
    common.run_command = mock.Mock()

    feature.deregister(connector, repo)

    connector.set_entry.assert_called_once_with(
        feature.FEATURE_TABLE_NAME,
        manifest['service']['name'],
        None
    )
