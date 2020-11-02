#!/usr/bin/env python

""" Package version constraints module. """
import re
from abc import ABC
from dataclasses import dataclass

import semver


class VersionConstraint(semver.VersionConstraint, ABC):
    """ Extends VersionConstraint from semver package. """

    @staticmethod
    def parse(constraint_expression: str) -> 'VersionConstraint':
        """ Parse version constraint.

        Args:
            constraint_expression: Expression syntax: "[[op][version]]+".
        Returns:
            The resulting VersionConstraint object.
        """

        return semver.parse_constraint(constraint_expression)


@dataclass
class PackageConstraint:
    """ PackageConstraint is a package version constraint. """

    name: str
    constraint: VersionConstraint

    def __str__(self):
        return f'{self.name} {self.constraint}'

    @staticmethod
    def parse(constraint_expression: str) -> 'PackageConstraint':
        """ Parse package constraint string which contains a package
        name separated by a space with zero, one or more version constraint
        expressions. A variety of version matching operators are supported
        including >, <, ==, !=, ^, *. See Examples.

        Args:
            constraint_expression: Expression syntax "[package name] [[op][version]]+".

        Returns:
            PackageConstraint object.

        Examples:
            >>> PackageConstraint.marshal('syncd^1.0.0').constraint
            <VersionRange (>=1.0.0,<2.0.0)>
            >>> PackageConstraint.marshal('swss>1.3.2 <4.2.1').constraint
            <VersionRange (>1.3.2,<4.2.1)>
            >>> PackageConstraint.marshal('swss').constraint
            <VersionRange (*)>
        """

        REQUIREMENT_SPECIFIER_RE = \
            r'(?P<name>[A-Za-z0-9_-]+)(?P<constraint>.*)'

        match = re.match(REQUIREMENT_SPECIFIER_RE, constraint_expression)
        if match is None:
            raise ValueError(f'Invalid constraint {constraint_expression}')
        groupdict = match.groupdict()
        name = groupdict.get('name')
        constraint = groupdict.get('constraint') or '*'
        return PackageConstraint(name, VersionConstraint.parse(constraint))


