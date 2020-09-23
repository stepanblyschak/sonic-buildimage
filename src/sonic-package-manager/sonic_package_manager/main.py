#!/usr/bin/env python

import os
import click
import tabulate
import natsort
import yaml
import docker

import package as pkg
import database
import installer

from sonic_package_manager.errors import *
from sonic_package_manager.installer import PackageInstallation


@click.group()
def cli():
    pass


@cli.command()
def list():
    db = database.PackageDatabase()
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
    try:
        db = database.PackageDatabase()
        pkg = db.get_package(name)
        if not pkg.is_installed():
            raise PackageManagerError('{} is not installed'.format(name))
        click.echo(yaml.safe_dump(pkg.get_manifest()))
    except PackageManagerError as err:
        click.secho("Failed to describe package {}: {}".format(name, err), fg="red")


@cli.command()
@click.argument("name")
def install(name):
    if os.geteuid() != 0:
        click.secho("Root privileges required for this operation", fg="red")
        raise click.Abort()
    try:
        installation = PackageInstallation(name)
        installation.install_package()
    except PackageManagerError as err:
        click.secho("Failed to install package {}: {}".format(name, err), fg="red")
        return


@cli.command()
@click.argument("name")
def uninstall(name):
    if os.geteuid() != 0:
        click.secho("Root privileges required for this operation", fg="red")
        raise click.Abort()
    try:
        installation = PackageInstallation(name)
        installation.uninstall_package()
    except PackageManagerError as err:
        click.secho("Failed to uninstall package {}: {}".format(name, err), fg="red")
        return
    click.secho("Package {} succesfully uninstalled!".format(name), fg="green")


if __name__ == "__main__":
    cli()

