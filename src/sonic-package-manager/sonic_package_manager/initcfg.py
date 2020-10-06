#!/usr/bin/env python

""" This module laoding default package configuration in to CONFIG DB. """

import typing

import swsssdk
from sonic_py_common import multi_asic

from sonic_package_manager import common, repository


def load_default_config(connectors: typing.Dict[typing.Optional[str], swsssdk.ConfigDBConnector],
                        repo: repository.Repository):
    """ Loads default configuration into CONFIG DB.

    Args:
        connectors: List of CONFIG DB connectors.
        repo: Repository object.
    """

    package = repo.get_package()
    init_cfg = package.get_initial_config()
    if init_cfg is None:
        return

    for namespace, connector in connectors.items():
        if multi_asic.is_multi_asic() and package.is_asic_service():
            if namespace:
                connector.connect()
                connector.mod_config(init_cfg)
        if not multi_asic.is_multi_asic() or package.is_host_service():
            if namespace is None:
                connector.connect()
                connector.mod_config(init_cfg)

    # TODO: update persistent config db seperately
    common.run_command('config save -y')

