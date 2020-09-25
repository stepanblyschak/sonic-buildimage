#!/usr/bin/env python

import os
import stat
import subprocess

import jinja2

from sonic_package_manager.logger import get_logger
from sonic_package_manager.errors import PackageManagerError


SONIC_PACKAGE_MANAGER_PATH = os.path.join('/', 'var', 'lib', 'sonic-package-manager')
SONIC_PACKAGE_METADATA_PATH = os.path.join('/', 'var', 'lib', 'sonic-package')
TEMPLATES_PATH = os.path.join('/', 'usr', 'share', 'sonic', 'templates')


def get_sonic_packages_file():
    ''' Return packages.yml path in SONiC OS. '''

    return os.path.join(SONIC_PACKAGE_MANAGER_PATH, 'packages.yml')


def get_package_metadata_folder(package):
    ''' Return a base path for package. '''

    return os.path.join(SONIC_PACKAGE_MANAGER_PATH, package.get_name())


def get_package_image_metadata_folder():
    ''' Return a path to image metadat folder. '''

    return SONIC_PACKAGE_METADATA_PATH


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


def get_template(templatename):
    ''' Returns a path to a template. '''

    return os.path.join(TEMPLATES_PATH, templatename)


def set_executable_bit(filepath):
    ''' Sets +x on filepath. '''

    st = os.stat(filepath)
    os.chmod(filepath, st.st_mode | stat.S_IEXEC)


def run_command(command):
    ''' Run arbitary bash command. '''

    get_logger().info('Running command: {}'.format(command))

    proc = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
    (out, _) = proc.communicate()
    if proc.returncode != 0:
        raise PackageManagerError('Failed to execute "{}"'.format(command))