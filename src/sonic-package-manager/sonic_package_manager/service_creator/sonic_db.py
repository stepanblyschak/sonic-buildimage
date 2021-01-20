#!/usr/bin/env python
import contextlib
import json
import os

import swsssdk
from swsscommon import swsscommon

from sonic_package_manager.service_creator import ETC_SONIC_PATH
from sonic_package_manager.service_creator.utils import in_chroot

CONFIG_DB = 'CONFIG_DB'
CONFIG_DB_JSON = os.path.join(ETC_SONIC_PATH, 'config_db.json')
INIT_CFG_JSON = os.path.join(ETC_SONIC_PATH, 'init_cfg.json')


def is_db_alive():
    """ Check if database is alive or not. """

    # In chroot we can connect to a running
    # DB via TCP socket, we should ignore this case.
    if in_chroot():
        return False

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
    """ swsscommon.Table adapter for persistent DBs. """

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
        fvs_dict = table.get(key, {})
        fvs = list(fvs_dict.items())
        return exists, fvs

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


class SonicDB:
    """ Store different DB access objects for
    running DB and also for persistent and initial
    configs. """

    _running = None

    @classmethod
    def running_table(cls, table):
        """ Returns running DB table. """

        if not is_db_alive():
            return None

        if cls._running is None:
            cls._running = swsscommon.DBConnector(CONFIG_DB, 0)

        return swsscommon.Table(cls._running, table)

    @classmethod
    def persistent_table(cls, table):
        """ Returns persistent DB table. """

        if not os.path.exists(CONFIG_DB_JSON):
            return None

        return FileDbTable(CONFIG_DB_JSON, table)

    @classmethod
    def initial_table(cls, table):
        """ Returns initial DB table. """

        return FileDbTable(INIT_CFG_JSON, table)
