#!/usr/bin/env python

import semver

from collections import namedtuple


Version = semver.Version
VersionConstraint = semver.VersionConstraint


class PackageConstraint:
    ''' PackageConstraint is a package version constraint. '''

    def __init__(self, name, constraint, positive=True):
        ''' Intiailize PackageConstraint.

        Args:
            name       (str): Name of the package.
            constraint (VersionConstraint): Version constraint of the requirement.
        '''

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

    def __str__(self):
        return '{} {}'.format(self.name, self.constraint)


def invert_version_constraint(constraint):
    ''' Inverts version constraint.
    If intput is '>1.0.0', the output will be '<=1.0.0'.

    Args:
        constraint (VersionConstraint): input constraint
    Returns:
        (VersionConstraint): inverted constraint.
    '''

    return parse_version_constraint('*').difference(constraint)


def parse_version_constraint(constraint_expression):
    ''' Parse version constraint.

    Args:
        constraint_expression (str): Expression syntax: "[[op][version]]+".
    Returns:
        VersionConstraint: The resulting VersionConstraint object.
    '''

    return semver.parse_constraint(constraint_expression)



def parse_package_constraint(constraint_expression):
    ''' Parse "dependency" string.

    Args:
        constraint_expression (str): Expression syntax "[packagename] [[op][version]]+".
        positive (bool): Whether to create a positive constraint.
    Returns:
        PackageConstraint: PackageConstraint object.
    '''

    pkgrequirement = list(reversed(constraint_expression.strip().split(' ', 1)))
    pkgname = pkgrequirement.pop()
    version_constraint_expression = '*'
    if pkgrequirement:
        version_constraint_expression = pkgrequirement.pop()
    constraint = parse_version_constraint(version_constraint_expression)
    return PackageConstraint(pkgname, constraint)

