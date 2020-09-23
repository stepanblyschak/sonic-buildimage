#!/usr/bin/env python

from __future__ import print_function

import os
import stat
import subprocess
import jinja2
from sonic_py_common.device_info import get_sonic_version_info

from sonic_package_manager.operation import Operation
from sonic_package_manager.logger import get_logger
from sonic_package_manager.errors import PackageInstallationError

class TemplateGenerator:
    ''' Base class with helper utilities to render j2 templates. '''

    @staticmethod
    def render_template(intemplate, outfile, renderctx):
        ''' Template renderer helper routine.

        Args:
            instemplate (str): Input file with template content.
            outfile (str): Output file to render template to.
            renderctx (dict): Dictionary used to generate jinja2 template
        '''

        with open(intemplate, 'r') as instream:
            template = jinja2.Template(instream.read())

        with open(outfile, 'w') as outstream:
            outstream.write(template.render(**renderctx))


class SystemdGenerator(TemplateGenerator, Operation):
    ''' Generate all needed files for integration with systemd '''

    SERVICE_FILE_TEMPLATE        = '/usr/share/sonic/templates/sonic-service.j2'
    SERVICE_FILE_LOCATION        = '/usr/lib/systemd/system/'
    SERVICE_MGMT_SCRIPT_TEMPLATE = '/usr/share/sonic/templates/service-mgmt.sh.j2'
    SERVICE_MGMT_SCRIPT_LOCATION = '/usr/local/bin/'
    DOCKER_CTL_SCRIPT_TEMPLATE   = '/usr/share/sonic/templates/docker_image_ctl.j2'
    DOCKER_CTL_SCRIPT_LOCALTION  = '/usr/bin/'

    def __init__(self, database, package):
        self._database = database
        self._package = package

    @staticmethod
    def get_service_file_path(package):
        return os.path.join(SystemdGenerator.SERVICE_FILE_LOCATION,
            '{}.service'.format(package.get_name()))

    @staticmethod
    def get_service_file_parametrized_path(package):
        return os.path.join(SystemdGenerator.SERVICE_FILE_LOCATION,
            '{}@.service'.format(package.get_name()))

    @staticmethod
    def get_service_mgmt_script_path(package):
        return os.path.join(SystemdGenerator.SERVICE_MGMT_SCRIPT_LOCATION,
            '{}.sh'.format(package.get_name()))

    @staticmethod
    def get_docker_ctl_script_path(package):
        return os.path.join(SystemdGenerator.DOCKER_CTL_SCRIPT_LOCALTION,
            '{}.sh'.format(package.get_name()))

    @staticmethod
    def reload_systemd():
        ''' Executes systemctl 'daemon-reload' '''

        proc = subprocess.Popen("systemctl daemon-reload", shell=True, stdout=subprocess.PIPE)
        (out, _) = proc.communicate()
        if proc.returncode != 0:
            raise PackageInstallationError("Failed to execute 'systemctl daemon-reload'")

    def _generate_systemd_service(self, package):
        ''' Generate systemd configuration for SONiC package
        TODO: service name
        TODO: timer for delayed services
        TODO: user for services
        '''

        manifest = package.get_manifest()
        service_props = manifest.get('service', dict())
        sonic_asic_platform = get_sonic_version_info()['asic_type']

        description = package.get_description()
        name = package.get_name()
        requires = []
        requisite = []
        after = []
        before = []

        for servicelist, services in dict(
                requires=requires,
                requisite=requisite,
                after=after,
                before=before).iteritems():
            for service in service_props.get(servicelist, []):
                services.append(
                    dict(
                        name=service,
                        is_package=self._database.has_package(service)
                    )
                )

        is_asic_service = service_props.get('asic-service', False)

        outputfile = SystemdGenerator.get_service_file_path(package)
        SystemdGenerator.render_template(self.SERVICE_FILE_TEMPLATE,
            outputfile,
            {
                'description': description,
                'name': name,
                'requires': requires,
                'requisite': requisite,
                'after': after,
                'before': before,
                'sonic_asic_platform': sonic_asic_platform,
                'multi_instance': False,
            }
        )
        get_logger().info('Installed {}'.format(outputfile))

        if is_asic_service:
            outputfile = SystemdGenerator.get_service_file_parametrized_path(package)
            SystemdGenerator.render_template(self.SERVICE_FILE_TEMPLATE,
                outputfile,
                {
                    'description': description,
                    'name': name,
                    'requires': requires,
                    'requisite': requisite,
                    'after': after,
                    'before': before,
                    'sonic_asic_platform': sonic_asic_platform,
                    'multi_instance': True,
                }
            )
            get_logger().info('Installed {}'.format(outputfile))

    def _generate_service_mgmt_script(self, package):
        ''' Generate service management script under /usr/local/bin/<package-name>.sh '''

        dependent_services = []
        multiasic_dependent_services = []
        peer_service_name = package.get_manifest()['service'].get('peer', '')
        service_name = package.get_name()
        sonic_asic_platform = get_sonic_version_info()['asic_type']

        # Find reverse dependencies: pkgiter depends on package
        for pkgiter in self._database:
            if pkgiter.get_name() == service_name:
                continue
            if not pkgiter.is_installed():
                continue
            manifest = pkgiter.get_manifest()
            dependent_of = manifest.get('service', dict()).get('dependent-of')
            if not dependent_of:
                continue
            is_multiasic_service = manifest.get('service', dict()).get('asic-service', False)
            for service in dependent_of:
                if service == service_name:
                    if is_multiasic_service:
                        multiasic_dependent_services.append(pkgiter.get_name())
                    else:
                        dependent_services.append(pkgiter.get_name())

        SystemdGenerator.render_template(self.SERVICE_MGMT_SCRIPT_TEMPLATE,
            SystemdGenerator.get_service_mgmt_script_path(package),
            {
                'dependent_services': dependent_services,
                'multiasic_dependent_services': multiasic_dependent_services,
                'peer_service_name': peer_service_name,
                'service_name': service_name,
                'sonic_asic_platform': sonic_asic_platform,
            }
        )

        # Make it executable
        st = os.stat(SystemdGenerator.get_service_mgmt_script_path(package))
        os.chmod(SystemdGenerator.get_service_mgmt_script_path(package), st.st_mode | stat.S_IEXEC)

        get_logger().info('Installed {}'.format(SystemdGenerator.get_service_mgmt_script_path(package)))

    def _generate_service_mgmt_scripts(self, package):
        ''' Regenerate service management scripts '''

        # TODO: Here we need to regenerate all service management scripts
        # to hook up new dependent services in existing services.
        # It will require every and also essentail SONiC packages to support
        # service script autogeneration. Current it is done only for the package
        # been installed and for swss service.
        # for package in self._database:
        #    self._generate_service_mgmt_script(package)

        self._generate_service_mgmt_script(package)
        # skip swss service as well for now
        # self._generate_service_mgmt_script(self._database.get_package('swss'))

    def _generate_docker_ctl_script(self, package):
        ''' Generate docker control script '''

        name = package.get_name()
        repository = package.get_repository()
        manifest = package.get_manifest()
        container_props = manifest['container']
        run_opt = []
        sonic_asic_platform = get_sonic_version_info()['asic_type']

        if container_props.get('privileged', False):
            run_opt.append('--privileged')

        run_opt.append('-t')

        for mount in container_props.get('mounts', []):
            run_opt.append('-v {}'.format(mount))

        SystemdGenerator.render_template(self.DOCKER_CTL_SCRIPT_TEMPLATE,
            SystemdGenerator.get_docker_ctl_script_path(package),
            {
                'docker_container_name': name,
                'docker_image_name': repository,
                'docker_image_run_opt': ' '.join(run_opt),
                'sonic_asic_platform': sonic_asic_platform,
            }
        )

        # Make it executable
        st = os.stat(SystemdGenerator.get_docker_ctl_script_path(package))
        os.chmod(SystemdGenerator.get_docker_ctl_script_path(package), st.st_mode | stat.S_IEXEC)

        get_logger().info('Installed {}'.format(SystemdGenerator.get_docker_ctl_script_path(package)))

    def generate(self, package):
        ''' Generate required files/scripts to integrate
        a package with SONiC service management system '''

        self._generate_systemd_service(package)
        if package.get_name() != 'database':
            self._generate_service_mgmt_scripts(package)
        self._generate_docker_ctl_script(package)

        self.reload_systemd()

    def _cleanup_generated(self, path):
        if os.path.exists(path):
            get_logger().info('Removing {}'.format(path))
            os.remove(path)

    def cleanup_generated_files(self, package):
        ''' Cleanup all generated files/scripts by generate() '''

        self._cleanup_generated(SystemdGenerator.get_service_file_path(package))
        self._cleanup_generated(SystemdGenerator.get_service_mgmt_script_path(package))
        self._cleanup_generated(SystemdGenerator.get_docker_ctl_script_path(package))

        self.reload_systemd()

    def execute(self):
        try:
            self.generate(self._package)
        except PackageInstallationError as err:
            self.cleanup_generated_files(self._package)
            raise

    def restore(self):
        self.cleanup_generated_files(self._package)

