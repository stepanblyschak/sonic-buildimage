#!/usr/bin/env python

""" This module implements monit configuration file auto-generation. """
import functools
import os
import typing

from sonic_package_manager import repository
from sonic_package_manager.logger import get_logger
from sonic_package_manager import common


MONIT_CONF_TEMPLATE = 'monit.conf.j2'
MONIT_CONF_PATTERN = 'monit_{}'
MONIT_CONF_PATH = os.path.join('/', 'etc', 'monit', 'conf.d')


def reload_monit(func: typing.Callable) -> typing.Callable:
    """ Decorates a function. After function execution
    monit daemon configuration is reloaded.

    Args:
        func: Callable object to decorate.
    Returns:
        A wrapper function.
    """

    @functools.wraps(func)
    def wrapped_function(*args, **kwargs):
        ret = func(*args, **kwargs)
        common.run_command('systemctl reload monit')
        return ret

    return wrapped_function


@reload_monit
def generate_monit_conf(repo: repository.Repository):
    """ Generate monit configuration for a pacakge and reload monit service.

    Args:
        repo: Repository object.
    """

    package = repo.get_package()
    manifest = package.get_manifest()
    processes = manifest.get('processes')
    if processes is None:
        return

    outputfilename = get_monit_conf_path(package.get_feature_name())
    common.render_template(common.get_template(MONIT_CONF_TEMPLATE), outputfilename,
                           {'feature': package.get_feature_name(), 'processes': processes})
    get_logger().info(f'Generated {outputfilename}')


@reload_monit
def remove_monit_conf(repo: repository.Repository):
    """ Uninstalls monit configuration for a package and reload monit service.

    Args:
        repo: Repository object.
    """

    package = repo.get_package()
    outputfilename = get_monit_conf_path(package.get_feature_name())

    if os.path.exists(outputfilename):
        os.remove(outputfilename)
        get_logger().info(f'Removed {outputfilename}')


def get_monit_conf_path(feature_name: str) -> str:
    """ Returns monit output file path.
    Args:
        feature_name: Name of the feature.
    Returns:
        Path to monit configuration file for this feature.
    """

    return os.path.join(MONIT_CONF_PATH, MONIT_CONF_PATTERN.format(feature_name))
