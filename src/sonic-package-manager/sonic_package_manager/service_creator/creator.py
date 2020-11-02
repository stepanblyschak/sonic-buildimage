#!/usr/bin/env python
import os
import stat
import subprocess
from typing import Dict

import jinja2 as jinja2

from sonic_package_manager.logger import log
from sonic_package_manager.package import Package
from sonic_package_manager.service_creator.feature import FeatureRegistry

SERVICE_FILE_TEMPLATE = 'sonic.service.j2'
SERVICE_FILE_LOCATION = '/usr/lib/systemd/system'
SERVICE_MGMT_SCRIPT_TEMPLATE = 'service_mgmt.sh.j2'
SERVICE_MGMT_SCRIPT_LOCATION = '/usr/local/bin'
DOCKER_CTL_SCRIPT_TEMPLATE = 'docker_image_ctl.j2'
DOCKER_CTL_SCRIPT_LOCATION = '/usr/bin'
MONIT_CONF_TEMPLATE = 'monit.conf.j2'
MONIT_CONF_LOCATION = '/etc/monit/conf.d/'

ETC_SONIC_PATH = '/etc/sonic'

TEMPLATES_PATH = '/usr/share/sonic/templates'


class ServiceCreatorError(Exception):
    pass


def render_template(in_template: str,
                    outfile: str,
                    render_ctx: Dict,
                    executable: bool = False):
    """ Template renderer helper routine.
    Args:
        in_template: Input file with template content
        outfile: Output file to render template to
        render_ctx: Dictionary used to generate jinja2 template
        executable: Set executable bit on rendered file
    """

    with open(in_template, 'r') as instream:
        template = jinja2.Template(instream.read())

    with open(outfile, 'w') as outstream:
        outstream.write(template.render(**render_ctx))

    if executable:
        set_executable_bit(outfile)


def get_template(template_name: str) -> str:
    """ Returns a path to a template.
    Args:
        template_name: Template file name.
    """

    return os.path.join(TEMPLATES_PATH, template_name)


def set_executable_bit(filepath):
    """ Sets +x on filepath. """

    st = os.stat(filepath)
    os.chmod(filepath, st.st_mode | stat.S_IEXEC)


def run_command(command: str):
    """ Run arbitrary bash command.
    Args:
        command: String command to execute as bash script
    Raises:
        PackageManagerError: Raised when the command return code
                             is not 0.
    """

    log.info(f'running command: {command}')

    proc = subprocess.Popen(command,
                            shell=True,
                            executable='/bin/bash',
                            stdout=subprocess.PIPE)
    (out, _) = proc.communicate()
    if proc.returncode != 0:
        raise ServiceCreatorError(f'Failed to execute "{command}"')


def in_chroot() -> bool:
    root_stat = os.stat('/')
    init_root_stat = os.stat('/proc/1/root')

    return (root_stat.st_dev, root_stat.st_ino) != \
           (init_root_stat.st_dev, init_root_stat.st_ino)


class ServiceCreator:
    def __init__(self, feature_registry: FeatureRegistry):
        self.feature_registry = feature_registry

    def create(self, package: Package, root='/', register_feature=True):
        try:
            self.generate_container_mgmt(package, root)
            self.generate_service_mgmt(package, root)
            self.generate_systemd_service(package, root)
            self.generate_monit_conf(package, root)

            if not in_chroot():
                run_command('systemctl daemon-reload')
                run_command('systemctl reload monit')

            if register_feature:
                self.feature_registry.register(package.name, package.manifest)
        except Exception:
            self.remove(package, root, not register_feature)
            raise
        except KeyboardInterrupt:
            self.remove(package, root, not register_feature)

    def remove(self, package: Package, root='/', deregister_feature=True):
        name = package.manifest['service']['name']

        def remove_file(path):
            if os.path.exists(path):
                os.remove(path)
                log.info(f'removed {path}')

        remove_file(os.path.join(root, MONIT_CONF_LOCATION, f'monit_{name}'))
        remove_file(os.path.join(root, SERVICE_FILE_LOCATION, f'{name}.service'))
        remove_file(os.path.join(root, SERVICE_FILE_LOCATION, f'{name}@.service'))
        remove_file(os.path.join(root, SERVICE_MGMT_SCRIPT_LOCATION, f'{name}.sh'))
        remove_file(os.path.join(root, DOCKER_CTL_SCRIPT_LOCATION, f'{name}.sh'))

        if not in_chroot():
            run_command('systemctl daemon-reload')
            run_command('systemctl reload monit')

        if deregister_feature:
            self.feature_registry.deregister(package.name)

    def generate_container_mgmt(self, package: Package, root='/'):
        repository = package.repository
        name = package.manifest['service']['name']
        container_spec = package.manifest['container']
        script_path = os.path.join(DOCKER_CTL_SCRIPT_LOCATION, f'{name}.sh')
        script_template = os.path.join(root, TEMPLATES_PATH, DOCKER_CTL_SCRIPT_TEMPLATE)
        run_opt = []

        if container_spec['privileged']:
            run_opt.append('--privileged')

        run_opt.append('-t')

        for volume in container_spec['volumes']:
            run_opt.append(f'-v {volume}')

        for mount in container_spec['mounts']:
            mount_type, source, target = mount['type'], mount['source'], mount['target']
            run_opt.append(f'--mount type={mount_type},source={source},target={target}')

        for env_name, value in container_spec['environment'].items():
            run_opt.append(f'-e {env_name}={value}')

        run_opt = ' '.join(run_opt)
        render_ctx = {
            'docker_container_name': name,
            'docker_image_name': repository,
            'docker_image_run_opt': run_opt,
        }
        render_template(script_template, script_path, render_ctx, executable=True)
        log.info(f'generated {script_path}')

    def generate_service_mgmt(self, package: Package, root='/'):
        name = package.manifest['service']['name']
        dependent_services = []
        multiasic_dependent_services = []
        scrip_template = os.path.join(TEMPLATES_PATH, SERVICE_MGMT_SCRIPT_TEMPLATE)
        script_path = os.path.join(root, SERVICE_MGMT_SCRIPT_LOCATION, f'{name}.sh')
        render_ctx = {
            'source': get_template(SERVICE_MGMT_SCRIPT_TEMPLATE),
            'name': name,
            'dependent_services': dependent_services,
            'multiasic_dependent_services': multiasic_dependent_services,
        }
        render_template(scrip_template, script_path, render_ctx, executable=True)
        log.info(f'generated {script_path}')

    def generate_systemd_service(self, package: Package, root='/'):
        name = package.manifest['service']['name']
        template = os.path.join(TEMPLATES_PATH, SERVICE_FILE_TEMPLATE)
        multi_instance_services = self.feature_registry.get_multi_instance_features()

        template_vars = {
            'source': get_template(MONIT_CONF_TEMPLATE),
            'manifest': package.manifest.unmarshal(),
            'multi_instance': False,
            'multi_instance_services': multi_instance_services,
        }

        output_file = os.path.join(root, SERVICE_FILE_LOCATION, f'{name}.service')
        render_template(template, output_file, template_vars)
        log.info(f'generated {output_file}')

        if package.manifest['service']['asic-service']:
            output_file = os.path.join(root, SERVICE_FILE_LOCATION, f'{name}@.service')
            template_vars['multi_instance'] = True
            render_template(template, output_file, template_vars)
            log.info(f'generated {output_file}')

    def generate_monit_conf(self, package: Package, root='/'):
        name = package.manifest['service']['name']
        processes = package.manifest['processes']
        output_filename = os.path.join(root, MONIT_CONF_LOCATION, f'monit_{name}')
        render_template(get_template(MONIT_CONF_TEMPLATE), output_filename,
                        {'source': get_template(MONIT_CONF_TEMPLATE),
                         'feature': name,
                         'processes': processes})
        log.info(f'generated {output_filename}')
