#!/usr/bin/env python

import functools
import typing

import docker
import swsssdk

from sonic_py_common.device_info import get_sonic_version_info

from sonic_package_manager import database
from sonic_package_manager import constraint, repository
from sonic_py_common import multi_asic
from sonic_package_manager import feature, image, metadata, monit, systemd, initcfg
from sonic_package_manager.errors import *
from sonic_package_manager.logger import get_logger


def skip_if_force_install_requested(func):
    """ Decorates a function, so that if force keyword
    argument is passed and the value is True, the exception
    is suppressed and warning is printed but the operation
    continues.
    """

    @functools.wraps(func)
    def wrapped_function(*args, **kwargs):
        force = False
        if 'force' in kwargs:
            force = kwargs.pop('force')
        try:
            return func(*args, **kwargs)
        except PackageInstallationError as err:
            if force:
                get_logger().warning(f'Ignoring error: {err}')
            else:
                raise

    return wrapped_function


def install_package(database, repository, version=None, force=False):
    """ Install a package from repository. """

    name = repository.get_name()
    version = version or repository.get_default_version()
    sonicver = get_sonic_compatibility_version()

    docker_client = docker.from_env()
    connectors = _get_db_connectors()
    host_db_connector = connectors['host']

    get_logger().info(_get_installation_request_msg(name, version, force))

    check_package_is_not_installed(repository, force=force)

    try:
        image.pull(docker_client, repository, version)
        metadata.install_metadata(docker_client, repository)

        check_sonic_version_compatibility(repository, sonicver, force=force)
        check_installation(database, repository, version, force=force)

        systemd.install_service(database, repository)
        monit.generate_monit_conf(repository)
        feature.register(host_db_connector, repository)

        repository.update_installation_status('installed', version)
        database.update_repository(repository)

        initcfg.load_default_config(connectors, repository)

    except PackageInstallationError as err:
        feature.deregister(host_db_connector, repository)
        monit.remove_monit_conf(repository)
        systemd.uninstall_service(repository)

        metadata.uninstall_metadata(repository)
        image.remove(docker_client, repository, version)

        # re-raise exception
        raise

    get_logger().info(f'Package {name} is succesfully installed!')


def uninstall_package(database, repository, force=False):
    """ Uninstall a package. """

    name = repository.get_name()
    version = repository.get_installed_version()

    docker_client = docker.from_env()
    connectors = _get_db_connectors()
    host_db_connector = connectors['host']

    get_logger().info(f'Request to uninstall {name}')

    check_package_is_installed(repository, force=force)

    check_uninstallation(database, repository, version, force=force)

    feature.deregister(host_db_connector, repository)
    monit.generate_monit_conf(repository)
    systemd.uninstall_service(repository)

    metadata.uninstall_metadata(repository)
    image.remove(docker_client, repository, version)

    repository.update_installation_status('not-installed', None)
    database.update_repository(repository)

    get_logger().info(f'Package {name} succesfully uninstalled!')


def get_sonic_compatibility_version():
    """ Returns: SONiC compatibility version string. """

    version = get_sonic_version_info()['sonic_compatibility_version']
    return constraint.Version.parse(version)


@skip_if_force_install_requested
def check_sonic_version_compatibility(repo: repository.Repository,
                                      sonicver: constraint.Version):
    """ Verify SONiC base image version meets the requirement
    of the package.

    Args:
        repo: Repository object.
        sonicver: SONiC compatibility version number.
    Raises:
        PackageSonicRequirementError: if requirement is not met.
    """

    package = repo.get_package()
    version_constraint = package.get_sonic_version_constraint()
    if not version_constraint.allows_all(sonicver):
        raise PackageSonicRequirementError(repo.get_name(), version_constraint, sonicver)


@skip_if_force_install_requested
def check_installation(database: database.RepositoryDatabase,
                       repo: repository.Repository,
                       version: constraint.Version):
    """ Verify that package dependencies are satisfied
    and the installation won't break any other package.

    Args:
        database:  Repository database.
        repo: Repository that is going to be installed.
        version: Version to install.
    Raises:
        PackageDependencyError: Raised when the dependency is not installed
                                or does not match the version pattern.
        PackageConflictError: Raised when the package conflicts with another package.
    """

    deps_dict = _build_repository_deps_dict(database)

    name = repo.get_name()
    package = repo.get_package()
    dependencies = package.get_dependencies()
    conflicts = package.get_conflicts()

    deps_dict[name] = {
        'dependencies': dependencies,
        'conflicts': conflicts,
        'version': version
    }
    _check_repository_deps_dict(deps_dict)


@skip_if_force_install_requested
def check_uninstallation(database: database.RepositoryDatabase,
                         repo: repository.Repository):
    """ Verify that all package dependencies will be satisfied
    after the installation.

    Args:
        database:  Repository database.
        repo: Repository that is going to be installed.
        version: Version to install.
    Raises:
        PackageDependencyError: Raised when the dependency is not installed
            or does not match the version pattern.
        PackageConflictError: Raised when the package conflicts with another package.
    """

    deps_dict = _build_repository_deps_dict(database)
    name = repo.get_name()
    try:
        deps_dict.pop(name)
    except KeyError:
        pass
    _check_repository_deps_dict(deps_dict)


@skip_if_force_install_requested
def check_package_is_not_installed(repository):
    if repository.is_installed():
        raise PackageInstallationError(
            f'{repository.get_name()} is already installed, uninstall'
            f' first if you try to upgrade.'
        )


@skip_if_force_install_requested
def check_package_is_installed(repository):
    if not repository.is_installed():
        raise PackageInstallationError(
            f'{repository.get_name()} is not installed.'
        )


def _build_repository_deps_dict(database):
    deps_dict = dict()

    for repo in database:
        if not repo.is_installed():
            continue

        pkg = repo.get_package()
        version = repo.get_installed_version()
        dependencies = pkg.get_dependencies()
        conflicts = pkg.get_conflicts()

        deps_dict[repo.get_name()] = {
            'dependencies': dependencies,
            'conflicts': conflicts,
            'version': version,
        }

    return deps_dict


def _check_repository_deps_dict(deps_dict):
    for package_name, info in deps_dict.items():
        for dependency in info['dependencies']:
            if dependency.name not in deps_dict:
                raise PackageDependencyError(package_name, dependency)

            installed_version = deps_dict[dependency.name]['version']
            if not dependency.constraint.allows_all(installed_version):
                raise PackageDependencyError(package_name, dependency, installed_version)
        for conflict in info['conflicts']:
            if conflict.name not in deps_dict:
                continue

            installed_version = deps_dict[conflict.name]['version']
            if conflict.constraint.allows_all(installed_version):
                raise PackageConflictError(package_name, conflict, installed_version)


def _get_installation_request_msg(name, version, force):
    """ Return the installation request log message. """

    msg = 'requested'
    if force:
        msg = msg + ' force'
    msg += f' installation of {name}'
    if version:
        msg += f' version {version}'

    return msg


def _get_db_connectors() -> typing.Dict[typing.Optional[str], swsssdk.ConfigDBConnector]:
    """ Returns: a dict of CONFIG DB connectors (namespace -> connector). """

    # Assumption: all namespaces in SONiC are asic$N and there is no namespace called 'host'
    # so we can use 'host' as a key for host DB connector instead of None key.
    result = {'host': swsssdk.ConfigDBConnector()}

    for roles, namespaces in multi_asic.get_all_namespaces():
        for namespace in namespaces:
            result[namespace] = swsssdk.ConfigDBConnector(namespace=namespace)

    return result

