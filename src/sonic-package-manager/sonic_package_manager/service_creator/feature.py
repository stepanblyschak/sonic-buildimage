#!/usr/bin/env python

""" This module implements new feature registration/de-registration in SONiC system. """
import contextlib
import json
from typing import Dict

import swsssdk
from swsscommon import swsscommon

from sonic_package_manager.logger import log
from sonic_package_manager.manifest import Manifest

CONFIG_DB = 'CONFIG_DB'
FEATURE = 'FEATURE'
CONFIG_DB_JSON = '/etc/sonic/config_db.json'
INIT_CFG_JSON = '/etc/sonic/init_cfg.json'


def is_db_alive():
    # FIXME: swsscommon immediately crashes the whole python process
    #        in case redis connection failed. This is not possible to handle
    #        but installing a package while database is not running is completely
    #        OK for this application. Requires a fix in pyswsscommon
    conn = swsssdk.ConfigDBConnector()
    try:
        conn.connect()
        return True
    except Exception:
        return False


class FileDbTable:
    def __init__(self, file, table):
        self._file = file
        self._table = table

    def keys(self):
        with open(self._file) as stream:
            config = json.load(stream)
            return config.get(self._table, {}).keys()

    def get(self, key):
        with open(self._file) as stream:
            config = json.load(stream)

        table = config.get(self._table, {})
        exists = key in table
        fvs = table.get(key, {})
        return exists, list(fvs.items())

    def set(self, key, fvs):
        with open(self._file) as stream:
            config = json.load(stream)

        table = config.setdefault(self._table, {})
        table.update({key: dict(fvs)})

        with open(self._file, 'w') as stream:
            json.dump(config, stream, indent=4)

    def _del(self, key):
        with open(self._file) as stream:
            config = json.load(stream)

        with contextlib.suppress(KeyError):
            config[self._table].pop(key)

        with open(self._file, 'w') as stream:
            json.dump(config, stream, indent=4)


class FeatureRegistry:
    def __init__(self, persistent, initial, running=None):
        self._persistent = persistent
        self._initial = initial
        self._running = running
        self._tables = [self._persistent, self._initial]
        if self._running:
            self._tables.append(self._running)

    @staticmethod
    def create() -> 'FeatureRegistry':
        tables = {}

        if is_db_alive():  # this is Ok if database is not running
            db = swsscommon.DBConnector(CONFIG_DB, 0)
            table = swsscommon.Table(db, FEATURE)
            tables['running'] = table
        else:
            log.warning(f'database is not running')

        tables['persistent'] = FileDbTable(CONFIG_DB_JSON, FEATURE)
        tables['initial'] = FileDbTable(INIT_CFG_JSON, FEATURE)

        return FeatureRegistry(**tables)

    def register(self, name: str, manifest: Manifest):
        for table in self._tables:
            cfg_entries = self.get_default_feature_entries()
            non_cfg_entries = self.get_non_configurable_feature_entries(manifest)

            exists, running_cfg = table.get(name)

            cfg = cfg_entries.copy()
            # Override configurable entries with CONFIG DB data.
            cfg = {**cfg, **dict(running_cfg)}
            # Override CONFIG DB data with non configurable entries.
            cfg = {**cfg, **non_cfg_entries}

            table.set(name, list(cfg.items()))

    def deregister(self, name: str):
        for table in self._tables:
            table._del(name)

    def is_feature_enabled(self, name: str) -> bool:
        """ Returns whether the feature is current enabled
        or not. Accesses running CONFIG DB. If no running CONFIG_DB
        table is found in tables returns False. """

        if self._running is None:
            return False

        exists, cfg = self._running.get(name)
        if not exists:
            return False
        cfg = dict(cfg)
        if cfg.get('state') == 'enabled':
            return True

        return False

    def get_multi_instance_features(self):
        res = []
        for feature in self._persistent.keys():
            exists, cfg = self._persistent.get(feature)
            assert exists
            cfg = dict(cfg)
            if cfg.get('has_per_asic_scope', 'False').lower() == 'true':
                res.append(feature)
        return res

    @staticmethod
    def get_default_feature_entries() -> Dict[str, str]:
        """ Get configurable feature table entries:
        e.g. 'state', 'auto_restart', etc. """

        return {
            'state': 'disabled',
            'auto_restart': 'enabled',
            'high_mem_alert': 'disabled',
        }

    @staticmethod
    def get_non_configurable_feature_entries(manifest) -> Dict[str, str]:
        """ Get non-configurable feature table entries: e.g. 'has_timer' """

        return {
            'has_per_asic_scope': str(manifest['service']['asic-service']),
            'has_global_scope': str(manifest['service']['host-service']),
            'has_timer': 'False',  # TODO: include timer if package requires
        }
