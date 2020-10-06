#!/usr/bin/env python

""" Package versioning constraints. """

import semver


Version = semver.Version
VersionConstraint = semver.VersionConstraint


class PackageConstraint:
    """ PackageConstraint is a package version constraint. """

    def __init__(self, name: str, constraint: VersionConstraint):
        """ Initialize PackageConstraint.

        Args:
            name: Name of the package.
            constraint: Version constraint of the requirement.
        """

        self._name = name
        self._constraint = constraint

    @property
    def name(self):
        return self._name

    @property
    def constraint(self):
        return self._constraint

    def __eq__(self, other):
        return self.name == other.name and self.constraint == other.constraint

    @property
    def __str__(self):
        return f'{self.name} {self.constraint}'


def parse_version(version_string: str) -> Version:
    """ Parse version string.

    Args:
        version_string: Version string.
    Returns:
        Version object.
    """

    return Version.parse(version_string)


def parse_version_constraint(constraint_expression: str) -> VersionConstraint:
    """ Parse version constraint.

    Args:
        constraint_expression: Expression syntax: "[[op][version]]+".
    Returns:
        The resulting VersionConstraint object.
    """

    return semver.parse_constraint(constraint_expression)


def parse_package_constraint(constraint_expression: str) -> PackageConstraint:
    """ Parse "dependency" string.

    Args:
        constraint_expression: Expression syntax "[package name] [[op][version]]+".
    Returns:
        PackageConstraint object.
    """

    pkgrequirement = list(reversed(constraint_expression.strip().split(' ', 1)))
    pkgname = pkgrequirement.pop()
    version_constraint_expression = '*'
    if pkgrequirement:
        version_constraint_expression = pkgrequirement.pop()
    constraint = parse_version_constraint(version_constraint_expression)
    return PackageConstraint(pkgname, constraint)

