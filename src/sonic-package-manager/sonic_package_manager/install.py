#!/usr/bin/env python

import copy
import functools
import os
import shutil
import docker
import swsssdk

from sonic_py_common.device_info import get_sonic_version_info

from sonic_package_manager import constraint
from sonic_package_manager import feature, imagepull, metadata, monit, systemd, initcfg
from sonic_package_manager.database import RepositoryDatabase
from sonic_package_manager.errors import *
from sonic_package_manager.logger import get_logger


def skip_if_force_install_requested(func):
    ''' Decorates a function, so that if force keyword
    argument is passed and the value is True, the exception
    is suppressed and warning is printed but the operation
    continues.
    '''

    @functools.wraps(func)
    def wrapped_function(*args, **kwargs):
        force = False
        if 'force' in kwargs:
            force = kwargs.pop('force')
        try:
            return func(*args, **kwargs)
        except PackageInstallationError as err:
            if force:
                get_logger().warn('Ignoring error: {}'.format(err))
            else:
                raise

    return wrapped_function


def get_sonic_compatibility_version():
    ''' Returns: SONiC compatiblity version string. '''

    return get_sonic_version_info()['sonic_compatibility_version']


@skip_if_force_install_requested
def check_sonic_version_compatibility(repository, sonicver):
    ''' Verify SONiC base image version meets the requirement
    of the package.

    Args:
        package (Package): Package object.
    Raises:
        PackageSonicRequirementError: if requirement is not met.
    '''

    package = repository.get_package()
    version_constraint = package.get_sonic_version_constraint()
    if not version_constraint.allows_all(sonicver):
        raise PackageSonicRequirementError(repository.get_name(), version_constraint, sonicver)


@skip_if_force_install_requested
def check_installation(database, repository, version):
    ''' Verify that package dependencies are satisfied
    and the installation won't break any other package.

    Args:
        database (RepositoryDatabase): Repository database.
        repository (Repository): Repository that is going to be installed.
        version (Version): Version to install.
    Raises:
        PackageDependencyError: Raised when the dependency is not installed
            or does not match the version pattern.
        PackageConflictError: Raised when the package conflicts with another package.
    '''

    graph = _build_repository_graph(database)

    name = repository.get_name()
    package = repository.get_package()
    dependencies = package.get_dependencies()
    conflicts = package.get_conflicts()

    graph[name] = {
        'dependencies': dependencies,
        'conflicts': conflicts,
        'version': version
    }

    _check_repository_graph(database, graph)


@skip_if_force_install_requested
def check_uninstallation(database, repository, version):
    ''' Verify that all package dependencies will be satisfied
    after the installation.

    Args:
        database (RepositoryDatabase): Repository database.
        repository (Repository): Repository that is going to be installed.
        version (Version): Version to install.
    Raises:
        PackageDependencyError: Raised when the dependency is not installed
            or does not match the version pattern.
        PackageConflictError: Raised when the package conflicts with another package.
    '''

    graph = _build_repository_graph(database)

    name = repository.get_name()

    try:
        graph.pop(name)
    except KeyError:
        pass

    _check_repository_graph(database, graph)


@skip_if_force_install_requested
def check_package_is_not_installed(repository):
    if repository.is_installed():
        raise PackageInstallationError(('{} is already installed, uninstall'
            ' first if you try to upgrade.').format(repository.get_name()))


@skip_if_force_install_requested
def check_package_is_installed(repository):
    if not repository.is_installed():
        raise PackageInstallationError('{} is not installed.'.format(repository.get_name()))


def _build_repository_graph(database):
    graph = dict()

    for repo in database:
        if not repo.is_installed():
            continue

        pkg = repo.get_package()
        version = repo.get_installed_version()
        dependencies = pkg.get_dependencies()
        conflicts = pkg.get_conflicts()

        graph[repo.get_name()] = {
            'dependencies': dependencies,
            'conflicts': conflicts,
            'version': version,
        }

    return graph


def _check_repository_graph(database, graph):
    for package_name, info in graph.iteritems():
        for dependency in info['dependencies']:
            if dependency.name not in graph:
                raise PackageDependencyError(package_name, dependency)

            installed_version = graph[dependency.name]['version']
            if not dependency.constraint.allows_all(installed_version):
                raise PackageDependencyError(package_name, dependency, installed_version)
        for conflict in info['conflicts']:
            if conflict.name not in graph:
                continue

            installed_version = graph[conflict.name]['version']
            if conflict.constraint.allows_all(installed_version):
                raise PackageConflictError(package_name, conflict, installed_version)


def install(database, repository, version=None, force=False):
    ''' Install a package from repository. '''

    connector = swsssdk.ConfigDBConnector()
    docker_client = docker.from_env()

    sonicver = get_sonic_compatibility_version()
    sonicver = constraint.Version.parse(sonicver)

    if version is None:
        version = repository.get_default_version()

    connector.connect()

    check_package_is_not_installed(repository, force=force)

    try:
        imagepull.install_docker_image(docker_client, repository, version)
        metadata.install_metadata(docker_client, repository, version)

        check_sonic_version_compatibility(repository, sonicver, force=force)
        check_installation(database, repository, version, force=force)

        systemd.install_service(database, repository)
        monit.install_monit_conf(repository)
        feature.register_feature(connector, repository, version)

        repository.update_installation_status('installed', version)
        database.update_repository(repository)

        initcfg.load_default_config(repository)

    except PackageInstallationError as err:
        # restore
        try:
            feature.deregister_feature(connector, repository, version)
            monit.uninstall_monit_conf(repository)
            systemd.uninstall_service(repository)

            metadata.uninstall_metadata(repository, version)
            imagepull.uninstall_docker_image(docker_client, repository, version)
        except PackageManagerError as err:
            get_logger().error(err)
            # continue restoring

        # re-raise exception
        raise err



def uninstall(database, repository, force=False):
    ''' Uninstall a package. '''

    connector = swsssdk.ConfigDBConnector()
    docker_client = docker.from_env()
    version = None

    connector.connect()

    check_package_is_installed(repository, force=force)
    check_uninstallation(database, repository, version, force=force)

    feature.deregister_feature(connector, repository, version)
    monit.uninstall_monit_conf(repository)
    systemd.uninstall_service(repository)

    metadata.uninstall_metadata(repository, version)
    imagepull.uninstall_docker_image(docker_client, repository, version)

    repository.update_installation_status('not-installed', None)
    database.update_repository(repository)
