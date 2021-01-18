#!/usr/bin/env python
import contextlib
import os
import stat
import subprocess
from typing import Dict

import jinja2 as jinja2
from prettyprinter import pformat

from sonic_package_manager.logger import log
from sonic_package_manager.package import Package
from sonic_package_manager.service_creator import ETC_SONIC_PATH
from sonic_package_manager.service_creator.feature import FeatureRegistry
from sonic_package_manager.service_creator.utils import in_chroot

SERVICE_FILE_TEMPLATE = 'sonic.service.j2'
TIMER_UNIT_TEMPLATE = 'timer.unit.j2'

SYSTEMD_LOCATION = '/usr/lib/systemd/system'

SERVICE_MGMT_SCRIPT_TEMPLATE = 'service_mgmt.sh.j2'
SERVICE_MGMT_SCRIPT_LOCATION = '/usr/local/bin'

DOCKER_CTL_SCRIPT_TEMPLATE = 'docker_image_ctl.j2'
DOCKER_CTL_SCRIPT_LOCATION = '/usr/bin'

MONIT_CONF_TEMPLATE = 'monit.conf.j2'
MONIT_CONF_LOCATION = '/etc/monit/conf.d/'

DEBUG_DUMP_SCRIPT_TEMPLATE = 'dump.sh.j2'
DEBUG_DUMP_SCRIPT_LOCATION = '/usr/bin/debug-dump/'

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

    log.debug(f'Rendering {in_template} to {outfile} with {pformat(render_ctx)}')

    with open(in_template, 'r') as instream:
        template = jinja2.Template(instream.read())

    with open(outfile, 'w') as outstream:
        outstream.write(template.render(**render_ctx))

    if executable:
        set_executable_bit(outfile)


def get_tmpl_path(template_name: str) -> str:
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

    log.debug(f'running command: {command}')

    proc = subprocess.Popen(command,
                            shell=True,
                            executable='/bin/bash',
                            stdout=subprocess.PIPE)
    (out, _) = proc.communicate()
    if proc.returncode != 0:
        raise ServiceCreatorError(f'Failed to execute "{command}"')


class ServiceCreator:
    """ Creates and registers services in SONiC based on the package
     manifest. """

    def __init__(self, feature_registry: FeatureRegistry, sonic_db):
        self.feature_registry = feature_registry
        self.sonic_db = sonic_db

    def create(self,
               package: Package,
               register_feature=True,
               state='enabled',
               owner='local'):
        try:
            self.generate_container_mgmt(package)
            self.generate_service_mgmt(package)
            self.update_dependent_list_file(package)
            self.generate_systemd_service(package)
            self.generate_monit_conf(package)
            self.generate_dump_script(package)

            self.set_initial_config(package)

            self.post_install()

            if register_feature:
                self.feature_registry.register(package.manifest,
                                               state, owner)
        except (Exception, KeyboardInterrupt):
            self.remove(package, not register_feature)
            raise

    def remove(self, package: Package, deregister_feature=True):
        name = package.manifest['service']['name']

        def remove_file(path):
            if os.path.exists(path):
                os.remove(path)
                log.info(f'removed {path}')

        remove_file(os.path.join(MONIT_CONF_LOCATION, f'monit_{name}'))
        remove_file(os.path.join(SYSTEMD_LOCATION, f'{name}.service'))
        remove_file(os.path.join(SYSTEMD_LOCATION, f'{name}@.service'))
        remove_file(os.path.join(SERVICE_MGMT_SCRIPT_LOCATION, f'{name}.sh'))
        remove_file(os.path.join(DOCKER_CTL_SCRIPT_LOCATION, f'{name}.sh'))
        remove_file(os.path.join(DEBUG_DUMP_SCRIPT_LOCATION, f'{name}'))

        self.update_dependent_list_file(package, remove=True)

        self.post_install()

        if deregister_feature:
            self.feature_registry.deregister(package.manifest['service']['name'])

    def post_install(self):
        if not in_chroot():
            run_command('systemctl daemon-reload')
            run_command('systemctl reload monit')

    def generate_container_mgmt(self, package: Package):
        repository = package.repository
        name = package.manifest['service']['name']
        container_spec = package.manifest['container']
        script_path = os.path.join(DOCKER_CTL_SCRIPT_LOCATION, f'{name}.sh')
        script_template = get_tmpl_path(DOCKER_CTL_SCRIPT_TEMPLATE)
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

    def generate_service_mgmt(self, package: Package):
        name = package.manifest['service']['name']
        multi_instance_services = self.feature_registry.get_multi_instance_features()
        script_path = os.path.join(SERVICE_MGMT_SCRIPT_LOCATION, f'{name}.sh')
        scrip_template = get_tmpl_path(SERVICE_MGMT_SCRIPT_TEMPLATE)
        render_ctx = {
            'source': get_tmpl_path(SERVICE_MGMT_SCRIPT_TEMPLATE),
            'manifest': package.manifest.unmarshal(),
            'multi_instance_services': multi_instance_services,
        }
        render_template(scrip_template, script_path, render_ctx, executable=True)
        log.info(f'generated {script_path}')

    def generate_systemd_service(self, package: Package):
        name = package.manifest['service']['name']
        multi_instance_services = self.feature_registry.get_multi_instance_features()

        template = get_tmpl_path(SERVICE_FILE_TEMPLATE)
        template_vars = {
            'source': get_tmpl_path(SERVICE_FILE_TEMPLATE),
            'manifest': package.manifest.unmarshal(),
            'multi_instance': False,
            'multi_instance_services': multi_instance_services,
        }
        output_file = os.path.join(SYSTEMD_LOCATION, f'{name}.service')
        render_template(template, output_file, template_vars)
        log.info(f'generated {output_file}')

        if package.manifest['service']['asic-service']:
            output_file = os.path.join(SYSTEMD_LOCATION, f'{name}@.service')
            template_vars['multi_instance'] = True
            render_template(template, output_file, template_vars)
            log.info(f'generated {output_file}')

        if package.manifest['service']['delayed']:
            template_vars = {
                'source': get_tmpl_path(TIMER_UNIT_TEMPLATE),
                'manifest': package.manifest.unmarshal(),
                'multi_instance': False,
            }
            output_file = os.path.join(SYSTEMD_LOCATION, f'{name}.timer')
            template = os.path.join(TEMPLATES_PATH, TIMER_UNIT_TEMPLATE)
            render_template(template, output_file, template_vars)
            log.info(f'generated {output_file}')

            if package.manifest['service']['asic-service']:
                output_file = os.path.join(SYSTEMD_LOCATION, f'{name}@.timer')
                template_vars['multi_instance'] = True
                render_template(template, output_file, template_vars)
                log.info(f'generated {output_file}')

    def generate_monit_conf(self, package: Package):
        name = package.manifest['service']['name']
        processes = package.manifest['processes']
        output_filename = os.path.join(MONIT_CONF_LOCATION, f'monit_{name}')
        render_template(get_tmpl_path(MONIT_CONF_TEMPLATE), output_filename,
                        {'source': get_tmpl_path(MONIT_CONF_TEMPLATE),
                         'feature': name,
                         'processes': processes})
        log.info(f'generated {output_filename}')

    def update_dependent_list_file(self, package: Package, remove=False):
        name = package.manifest['service']['name']
        dependent_of = package.manifest['service']['dependent-of']
        host_service = package.manifest['service']['host-service']
        asic_service = package.manifest['service']['asic-service']

        def update_dependent(service, name, multi_inst):
            if multi_inst:
                filename = f'{service}_multi_inst_dependent'
            else:
                filename = f'{service}_dependent'

            filepath = os.path.join(ETC_SONIC_PATH, filename)

            dependent_services = set()
            if os.path.exists(filepath):
                with open(filepath) as fp:
                    dependent_services.update({line.strip() for line in fp.readlines()})
            if remove:
                with contextlib.suppress(KeyError):
                    dependent_services.remove(name)
            else:
                dependent_services.add(name)
            with open(filepath, 'w') as fp:
                fp.write('\n'.join(dependent_services))

        for service in dependent_of:
            if host_service:
                update_dependent(service, name, multi_inst=False)
            if asic_service:
                update_dependent(service, name, multi_inst=True)

    def generate_dump_script(self, package):
        name = package.manifest['service']['name']

        if not package.manifest['package']['debug-dump']:
            return

        if not os.path.exists(DEBUG_DUMP_SCRIPT_LOCATION):
            os.mkdir(DEBUG_DUMP_SCRIPT_LOCATION)

        scrip_template = os.path.join(TEMPLATES_PATH, DEBUG_DUMP_SCRIPT_TEMPLATE)
        script_path = os.path.join(DEBUG_DUMP_SCRIPT_LOCATION, f'{name}')
        render_ctx = {
            'source': get_tmpl_path(SERVICE_MGMT_SCRIPT_TEMPLATE),
            'manifest': package.manifest.unmarshal(),
        }
        render_template(scrip_template, script_path, render_ctx, executable=True)
        log.info(f'generated {script_path}')

    def set_initial_config(self, package):
        init_cfg = package.manifest['package']['init-cfg']

        def get_tables(table_name):
            tables = []

            running_table = self.sonic_db.running_table(table_name)
            if running_table is not None:
                tables.append(running_table)

            persistent_table = self.sonic_db.persistent_table(table_name)
            if persistent_table is not None:
                tables.append(persistent_table)

            initial_table = self.sonic_db.initial_table(table_name)
            if initial_table is not None:
                tables.append(initial_table)

            return tables

        for tablename, content in init_cfg.items():
            if not isinstance(content, dict):
                continue

            tables = get_tables(tablename)

            for key in content:
                for table in tables:
                    cfg = content[key]
                    exists, old_fvs = table.get(key)
                    if exists:
                        cfg.update(old_fvs)
                    fvs = list(cfg.items())
                    table.set(key, fvs)
