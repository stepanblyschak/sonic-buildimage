#!/usr/bin/env python

""" This module implements an operation that integrates the package with systemd. """
import functools
import os
import typing

from sonic_py_common.device_info import get_sonic_version_info

from sonic_package_manager import common
from sonic_package_manager.logger import get_logger
from sonic_package_manager.errors import PackageInstallationError

SERVICE_FILE_TEMPLATE = 'sonic.service.sh.j2'
SERVICE_FILE_LOCATION = os.path.join('/', 'usr', 'lib', 'systemd', 'system')
SERVICE_MGMT_SCRIPT_TEMPLATE = 'service_mgmt.sh.j2'
SERVICE_MGMT_SCRIPT_LOCATION = os.path.join('/', 'usr', 'local', 'bin')
DOCKER_CTL_SCRIPT_TEMPLATE = 'docker_image_ctl.j2'
DOCKER_CTL_SCRIPT_LOCALTION = os.path.join('/', 'usr', 'bin')

ETC_SONIC_PATH = os.path.join('/', 'etc', 'sonic')


def get_service_file_path(package):
    name = package.get_feature_name()
    return os.path.join(SERVICE_FILE_LOCATION, f'{name}.service')


def get_service_file_parametrized_path(package):
    name = package.get_feature_name()
    return os.path.join(SERVICE_FILE_LOCATION, f'{name}@.service')


def get_service_mgmt_script_path(package):
    name = package.get_feature_name()
    return os.path.join(SERVICE_MGMT_SCRIPT_LOCATION, f'{name}.sh')


def get_docker_ctl_script_path(package):
    name = package.get_feature_name()
    return os.path.join(DOCKER_CTL_SCRIPT_LOCALTION, f'{name}.sh')


def reload_systemd(func: typing.Callable) -> typing.Callable:
    """ Decorates a function. After function execution
    systemd daemon is reloaded.

    Args:
        func: Callable object to decorate.
    Returns:
        A wrapper function.
    """

    @functools.wraps(func)
    def wrapped_function(*args, **kwargs):
        ret = func(*args, **kwargs)
        common.run_command('systemctl daemon-reload')
        return ret

    return wrapped_function


@reload_systemd
def install_service(database, repository):
    """ Generate required files/scripts to integrate
    a package with SONiC service management system """

    generate_systemd_service(database, repository)
    generate_service_mgmt_script(repository)
    update_dependent_list(repository)
    generate_docker_ctl_script(repository)


@reload_systemd
def uninstall_service(repository):
    """ Cleanup all generated files/scripts by generate() """

    package = repository.get_package()

    _cleanup_generated(get_service_file_path(package))
    _cleanup_generated(get_service_mgmt_script_path(package))
    _cleanup_generated(get_docker_ctl_script_path(package))

    update_dependent_list(repository, True)


def generate_systemd_service(database, repository):
    """ Generate systemd configuration for SONiC package

    TODO: Timer generation for delayed services.

    Args:
        database (RepositoryDatabase): RepositoryDatabase object.
        repository (Repository): Repository to install.
    """

    package = repository.get_package()
    manifest = package.get_manifest()
    service_props = manifest.get('service', dict())
    sonic_asic_platform = get_sonic_version_info()['asic_type']
    is_asic_service = service_props.get('asic-service', False)
    service_user = service_props.get('user', 'root')

    package = repository.get_package()
    description = repository.get_description()
    name = package.get_feature_name()
    requires = []
    requisite = []
    after = []
    before = []
    wanted_by = []

    unit_attributes = {
        'requires': requires,
        'requisite': requisite,
        'after': after,
        'before': before,
        'wanted-by': wanted_by,
    }

    for unit_attribute, services in unit_attributes.items():
        for unit in service_props.get(unit_attribute, []):
            unitinfo = dict(
                name=unit,
                is_package=database.is_package_installed(unit),
            )
            services.append(unitinfo)

    template_vars = {
        'description': description,
        'name': name,
        'requires': requires,
        'requisite': requisite,
        'after': after,
        'before': before,
        'wanted_by': wanted_by,
        'sonic_asic_platform': sonic_asic_platform,
        'user': service_user,
        'multi_instance': False,
    }

    outputfile = get_service_file_path(package)
    common.render_template(common.get_template(SERVICE_FILE_TEMPLATE), outputfile, template_vars)
    get_logger().info(f'Installed {outputfile}')

    if is_asic_service:
        outputfile = get_service_file_parametrized_path(package)
        template_vars['multi_instance'] = True
        common.render_template(common.get_template(SERVICE_FILE_TEMPLATE), outputfile, template_vars)
        get_logger().info(f'Installed {outputfile}')


def generate_service_mgmt_script(repository):
    """ Generate service management script under /usr/local/bin/<package-name>.sh """

    package = repository.get_package()
    dependent_services = []
    multiasic_dependent_services = []
    peer_service_name = package.get_manifest()['service'].get('peer', '')
    service_name = package.get_feature_name()
    sonic_asic_platform = get_sonic_version_info()['asic_type']

    common.render_template(common.get_template(SERVICE_MGMT_SCRIPT_TEMPLATE),
                           get_service_mgmt_script_path(package),
                           {
                               'dependent_services': dependent_services,
                               'multiasic_dependent_services': multiasic_dependent_services,
                               'peer_service_name': peer_service_name,
                               'service_name': service_name,
                               'sonic_asic_platform': sonic_asic_platform,
                           })

    common.set_executable_bit(get_service_mgmt_script_path(package))

    get_logger().info(f'Installed {get_service_mgmt_script_path(package)}')


def update_dependent_list(repository, remove=False):
    """ Generate dependent file list. """

    package = repository.get_package()
    service_name = package.get_feature_name()
    manifest = package.get_manifest()
    service_props = manifest.get('service', dict())
    dependent_of = service_props.get('dependent-of', [])
    is_multiasic_service = service_props.get('asic-service', False)

    for service in dependent_of:
        files = [f'{service}_dependent']
        if is_multiasic_service:
            files.append(f'{service}_multi_inst_dependent')

        if service != 'swss':
            raise PackageInstallationError(
                'Current only "swss" service can be in "dependent-of" list')

        for filename in files:
            with open(os.path.join(ETC_SONIC_PATH, filename), 'a+') as f:
                f.seek(0)
                dependent = set(f.read().strip().split())
                if remove:
                    try:
                        dependent.remove(service_name)
                    except ValueError:
                        pass
                else:
                    dependent.add(service_name)
                f.seek(0)
                f.truncate()
                f.write(' '.join(dependent))


def generate_docker_ctl_script(repository):
    """ Generate docker control script """

    package = repository.get_package()
    name = package.get_feature_name()
    repository = repository.get_repository()
    manifest = package.get_manifest()
    container_props = manifest['container']
    sonic_asic_platform = get_sonic_version_info()['asic_type']
    no_default_tmpfs_volume = container_props.get('no_default_tmpfs_volume', False)
    run_opt = []

    if container_props.get('privileged', False):
        run_opt.append('--privileged')

    run_opt.append('-t')

    for volume in container_props.get('volumes', []):
        run_opt.append(f'-v {volume}')

    for mount in container_props.get('mounts', []):
        type, source, target = mount['type'], mount['source'], mount['target']
        run_opt.append(f'--mount type={type},source={source},target={target}')

    for envname, value in container_props.get('environment', dict()).items():
        run_opt.append(f'-e {envname}={value}')

    run_opt = ' '.join(run_opt)

    common.render_template(common.get_template(DOCKER_CTL_SCRIPT_TEMPLATE),
                           get_docker_ctl_script_path(package),
                           {
                               'docker_container_name': name,
                               'docker_image_name': repository,
                               'docker_image_run_opt': run_opt,
                               'sonic_asic_platform': sonic_asic_platform,
                               'no_default_tmpfs_volume': no_default_tmpfs_volume,
                           })

    common.set_executable_bit(get_docker_ctl_script_path(package))

    get_logger().info(f'Installed {get_docker_ctl_script_path(package)}')


def _cleanup_generated(path):
    if os.path.exists(path):
        get_logger().info(f'Removing {path}')
        os.remove(path)
