#!/usr/bin/env python
from unittest import mock

import pytest
import swsssdk
from sonic_py_common import multi_asic

from sonic_package_manager import repository, package, initcfg, common


@pytest.mark.parametrize('asic_service,host_service,is_multi_asic',
                         [
                             (True, True, True),
                             (False, True, True),
                             (True, False, True),
                             (True, True, False),
                             (False, True, False),
                             (True, False, False),
                         ])
def test_load_default_config(asic_service, host_service, is_multi_asic):
    repo = mock.Mock(repository.Repository)
    manifest = {'service': {'name': 'test_service',
                            'asic-service': asic_service,
                            'host-service': host_service}}
    init_cfg = {"TEST_TABLE": {"test_key":{}}}
    pkg = package.Package(manifest)
    pkg.get_manifest = mock.Mock(return_value=manifest)
    pkg.get_initial_config = mock.Mock(return_value=init_cfg)
    repo.get_package = mock.Mock(return_value=pkg)
    common.run_command = mock.Mock()
    multi_asic.is_multi_asic = mock.Mock(return_value=is_multi_asic)

    connectors = {}

    # global connector
    connector = mock.Mock(swsssdk.ConfigDBConnector)
    connectors[None] = connector

    # connectors per namespace
    if is_multi_asic:
        asic1_connector = mock.Mock(swsssdk.ConfigDBConnector)
        connectors['asic1'] = asic1_connector

    initcfg.load_default_config(connectors, repo)

    if is_multi_asic:
        if asic_service:
            asic1_connector.mod_config.assert_called_once_with(init_cfg)
        if host_service:
            connector.mod_config.assert_called_once_with(init_cfg)
        if not host_service:
            connector.mod_config.assert_not_called()
        if not asic_service:
            asic1_connector.mod_config.assert_not_called()
    else:
        connector.mod_config.assert_called_once_with(init_cfg)
