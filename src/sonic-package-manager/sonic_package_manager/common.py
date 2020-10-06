#!/usr/bin/env python

""" Common functions and utilities. """

import os
import stat
import subprocess
import typing

import jinja2

from sonic_package_manager.logger import get_logger
from sonic_package_manager.errors import PackageManagerError

SONIC_PACKAGE_MANAGER_PATH = os.path.join('/', 'var', 'lib', 'sonic-package-manager')
SONIC_PACKAGE_METADATA_PATH = os.path.join('/', 'var', 'lib', 'sonic-package')
TEMPLATES_PATH = os.path.join('/', 'usr', 'share', 'sonic', 'templates')


def get_sonic_packages_file():
    """ Return packages.yml path in SONiC OS. """

    return os.path.join(SONIC_PACKAGE_MANAGER_PATH, 'packages.yml')


def get_package_metadata_folder(name: str) -> str:
    """ Return a base path for package. """

    return os.path.join(SONIC_PACKAGE_MANAGER_PATH, name)


def get_package_image_metadata_folder():
    """ Return a path to image metadata folder. """

    return SONIC_PACKAGE_METADATA_PATH


def render_template(intemplate: str, outfile: str, renderctx: typing.Dict):
    """ Template renderer helper routine.

    Args:
        intemplate: Input file with template content.
        outfile: Output file to render template to.
        renderctx: Dictionary used to generate jinja2 template
    """

    with open(intemplate, 'r') as instream:
        template = jinja2.Template(instream.read())

    with open(outfile, 'w') as outstream:
        outstream.write(template.render(**renderctx))


def get_template(templatename: str) -> str:
    """ Returns a path to a template.

    Args:
        templatename: Template file name.
    """

    return os.path.join(TEMPLATES_PATH, templatename)


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

    get_logger().debug(f'Running command: {command}')

    proc = subprocess.Popen(command,
                            shell=True,
                            executable='/bin/bash',
                            stdout=subprocess.PIPE)
    (out, _) = proc.communicate()
    if proc.returncode != 0:
        raise PackageManagerError(f'Failed to execute "{command}"')
