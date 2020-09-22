#!/usr/bin/env python

''' This module implements the logic of feature registration and deregistration in CONFIG DB. '''

from __future__ import print_function

import os
import json
import stat
import subprocess
import jinja2
from sonic_py_common.device_info import get_sonic_version_info

from sonic_package_manager.errors import PackageInstallationError


class FeatureTableUpdater:
    ''' The installation action performs an update in CONFIG DB FEATURE table
    to register a SONiC package as a new feature.
    '''

    FEATURE_TABLE_NAME = 'FEATURE'

    def __init__(self, connector, package):
        ''' Initialize FeatureTableUpdater.

        Args:
            self (FeatureTableUpdater): Feature Table Updater instance to initialize.
            connector (swsssdk.ConfigDBConnector): Config DB connector
            package (Package): SONiC Package instance.

        Returns:
            None.
        '''

        self._conn = connector
        self._conn.connect()
        self._package = package

    def _get_feature_default_configuration(self):
        ''' Returns default feature configuration.

        Args:
            self (FeatureTableUpdater): Feature Table Updater instance.

        Returns:
            Tuple (table (str), key (str), entries (entries))
        '''

        table   = self.FEATURE_TABLE_NAME
        key     = self._package.get_name()
        entries = dict(state='disabled',
                       has_timer=False, # TODO: include timer if needed
                       auto_restart='enabled',
                       high_mem_alert='disabled')

        return table, key, entries

    def _update_running_config(self, remove=False):
        ''' Update running configuration database with new feature package.

        Args:
            self (FeatureTableUpdater): Feature Table Updater instance.

        Returns:
            None.
        '''

        if not remove:
            self._conn.mod_entry(*self._get_feature_default_configuration())
        else:
            entries = self._conn.get_entry(self.FEATURE_TABLE_NAME, self._package.get_name())
            if entries.get('state', '') == 'enabled':
                raise PackageInstallationError('Package feature is enabled, cannot remove. Disable the feature first.')
            self._conn.set_entry(self.FEATURE_TABLE_NAME, self._package.get_name(), None)

    def _update_startup_config(self, remove=False):
        ''' Update startup configuration database with new feature package.

        Args:
            self (FeatureTableUpdater): Feature Table Updater instance.

        Returns:
            None.
        '''

        for filepath in ('/etc/sonic/config_db.json', '/etc/sonic/init_cfg.json'):
            with open(filepath, 'r+') as cfgfile:
                cfg = json.load(cfgfile)

                table, key, entries = self._get_feature_default_configuration()

                if not remove:
                    cfg.update({
                        '{}{}{}'.format(table, self._conn.TABLE_NAME_SEPARATOR, key): entries
                    })
                else:
                    try:
                        cfg.pop('{}{}{}'.format(table, self._conn.TABLE_NAME_SEPARATOR, key))
                    except KeyError:
                        pass

                cfgfile.seek(0)
                cfgfile.truncate()

                json.dump(cfg, cfgfile)

    def execute(self):
        ''' Register new feature package.

        Args:
            self (FeatureTableUpdater): Feature Table Updater instance.

        Returns:
            None.
        '''

        self._update_running_config()
        self._update_startup_config()

    def restore(self):
        ''' Unregister new feature package.

        Args:
            self (FeatureTableUpdater): Feature Table Updater instance.

        Returns:
            None.
        '''

        self._update_startup_config(remove=True)
        self._update_running_config(remove=True)

