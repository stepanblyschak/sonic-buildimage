#!/usr/bin/env python

from unittest import mock

import jinja2

from sonic_package_manager import monit, common
from sonic_package_manager import package
from sonic_package_manager import repository


def manifest_one_process():
    return


def manifest_no_processes():
    return {'service': {'name': 'test_service'}}

def test_monit_install():
    repo = mock.Mock(repository.Repository)
    manifest = {'service': {'name': 'test_service'},
                'processes': [
                    {'name': "testd",
                     'command': 'testd',
                     'critical': True}
                ]}
    pkg = package.Package(manifest)
    repo.get_package = mock.Mock(return_value=pkg)

    common.render_template = mock.Mock()
    common.run_command = mock.Mock()

    monit.generate_monit_conf(repo)

    common.render_template.assert_called_once_with(
        common.get_template(monit.MONIT_CONF_TEMPLATE),
        monit.get_monit_conf_path(manifest['service']['name']),
        {
            'feature': manifest['service']['name'],
            'processes': manifest['processes'],
        })
    common.run_command.assert_called_once_with('systemctl reload monit')


def test_monit_install_no_processes():
    repo = mock.Mock(repository.Repository)
    manifest = {'service': {'name': 'test_service'}}
    pkg = package.Package(manifest)
    repo.get_package = mock.Mock(return_value=pkg)

    common.render_template = mock.Mock()
    common.run_command = mock.Mock()

    monit.generate_monit_conf(repo)

    common.render_template.assert_not_called()


def test_monit_uninstall():
    repo = mock.Mock(repository.Repository)
    manifest = {'service': {'name': 'test_service'},
                'processes': [
                    {'name': "testd",
                     'command': 'testd',
                     'critical': True}
                ]}
    pkg = package.Package(manifest)
    repo.get_package = mock.Mock(return_value=pkg)

    common.run_command = mock.Mock()

    with mock.patch('os.path.exists') as mock_os_path_exists:
        mock_os_path_exists.return_value = True
        with mock.patch('os.remove') as mock_os_remove:
            monit.remove_monit_conf(repo)
            mock_os_path_exists.assert_called_once_with(
                monit.get_monit_conf_path(manifest['service']['name'])
            )
            mock_os_remove.assert_called_once_with(
                monit.get_monit_conf_path(manifest['service']['name'])
            )

    common.run_command.assert_called_once_with('systemctl reload monit')
