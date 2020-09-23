#!/usr/bin/env python

import os
import sys
import click
import tabulate
import natsort
import yaml
import docker

from sonic_package_manager.database import PackageDatabase
from sonic_package_manager.installation import PackageInstallation
from sonic_package_manager.errors import *


@click.group()
def cli():
    pass


@cli.command()
def list():
    ''' List available packages. '''

    db = PackageDatabase()
    table_header = ["Name", "Repository", "Description", "Version", "Status"]
    table_body = []

    for package in db:
        table_body.append([
            package.get_name(),
            package.get_repository(),
            package.get_description(),
            package.installed_version() or "N/A",
            package.status()
        ])
    print(tabulate.tabulate(table_body, table_header))


@cli.command()
@click.argument("name")
def describe(name):
    ''' Print the manifest content. '''

    try:
        db = PackageDatabase()
        pkg = db.get_package(name)
        if not pkg.is_installed():
            raise PackageManagerError('{} is not installed'.format(name))
        click.echo(yaml.safe_dump(pkg.get_manifest()))
    except PackageManagerError as err:
        click.secho("Failed to describe package {}: {}".format(name, err), fg="red")
        sys.exit(1)


@cli.command()
@click.argument("name")
@click.argument("repository")
@click.argument("default-version")
def add(name, repository, default_version):
    ''' Add a new package to database. '''

    if os.geteuid() != 0:
        click.secho("Root privileges required for this operation", fg="red")
        sys.exit(1)
    try:
        db = PackageDatabase()
        db.add_package(name, repository, description=None, default_version=default_version)
    except PackageManagerError as err:
        click.secho("Failed to add package {}: {}".format(name, err), fg="red")
        sys.exit(1)


@cli.command()
@click.argument("name")
def remove(name):
    ''' Remove a package from database. '''

    if os.geteuid() != 0:
        click.secho("Root privileges required for this operation", fg="red")
        sys.exit(1)
    try:
        db = PackageDatabase()
        db.remove_package(name)
    except PackageManagerError as err:
        click.secho("Failed to remove package {}: {}".format(name, err), fg="red")
        sys.exit(1)


@cli.command()
@click.argument("name")
def install(name):
    ''' Install a package. '''

    if os.geteuid() != 0:
        click.secho("Root privileges required for this operation", fg="red")
        sys.exit(1)
    try:
        installation = PackageInstallation(name)
        installation.install_package()
    except PackageManagerError as err:
        click.secho("Failed to install package {}: {}".format(name, err), fg="red")
        sys.exit(1)


@cli.command()
@click.argument("name")
def uninstall(name):
    ''' Uninstall a package. '''

    if os.geteuid() != 0:
        click.secho("Root privileges required for this operation", fg="red")
        sys.exit(1)
    try:
        installation = PackageInstallation(name)
        installation.uninstall_package()
    except PackageManagerError as err:
        click.secho("Failed to uninstall package {}: {}".format(name, err), fg="red")
        sys.exit(1)
    click.secho("Package {} succesfully uninstalled!".format(name), fg="green")


if __name__ == "__main__":
    cli()

