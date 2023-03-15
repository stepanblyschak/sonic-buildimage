#!/usr/bin/env python3

""" This script prepares startup arguments for orchagent and starts it """

import os
import yaml
from swsscommon import swsscommon


SONIC_VERSION_FILE = "/etc/sonic/sonic_version.yml"
MGMT_IFACE = "eth0"
SWSS_LOG_DIR = "/var/log/swss"
ORCHAGENT_PATH = "/usr/bin/orchagent"


class OrchagentParameters:
    def __init__(self):
        with open(SONIC_VERSION_FILE) as sv:
            self.sonic_version_dict = yaml.safe_load(sv)

        config_db = swsscommon.ConfigDBConnector()
        config_db.connect()
        self.device_metadata = config_db.get_entry(
            "DEVICE_METADATA", "localhost")

    @property
    def platform(self):
        return self.sonic_version_dict["asic_type"]

    @property
    def sub_platform(self):
        return self.sonic_version_dict["asic_subtype"]

    @property
    def mac_address(self):
        if "mac" in self.device_metadata:
            return self.device_metadata["mac"]

        with open(f"/sys/class/net/{MGMT_IFACE}/address") as stream:
            return stream.read().strip()

    @property
    def is_sync_mode_enabled(self):
        return self.device_metadata.get("synchronous_mode") == "enable"

    @property
    def asic_id(self):
        """
        Check if there is an "asic_id field" in the DEVICE_METADATA in configDB.
        "DEVICE_METADATA": {
            "localhost": {
                ....
                "asic_id": "0",
            }
        },
        ID field could be integers just to denote the asic instance like 0,1,2...
        OR could be PCI device ID's which will be strings like "03:00.0"
        depending on what the SAI/SDK expects.
        """

        return self.device_metadata.get("asic_id")

    @property
    def namespace_id(self):
        """ For multi asic platforms add the asic name to the record file names """

        return os.getenv("NAMESPACE_ID")


def get_orchagent_args():
    params = OrchagentParameters()
    cmdline_args = [ORCHAGENT_PATH, "-d", f"{SWSS_LOG_DIR}", "-b", "8192"]

    if params.is_sync_mode_enabled:
        cmdline_args.append("-s")

    asic_id = params.asic_id
    if asic_id is not None:
        cmdline_args += ["-i", f"{asic_id}"]

    namespace_id = params.namespace_id
    if namespace_id is not None:
        cmdline_args += ["-f", f"swss.asic{namespace_id}.rec"]
        cmdline_args += ["-j" f"sairedis.asic{namespace_id}.rec"]

    platform = params.platform

    # Add platform specific arguments if necessary
    if platform in ("mellanox",):
        # Don't pass MAC on nvidia/mellanox platform
        pass
    else:
        cmdline_args += ["-m", f"{params.mac_address}"]

    return cmdline_args


def main():
    # Create a folder for SwSS record files
    os.makedirs(SWSS_LOG_DIR, exist_ok=True)
    orchagent_args = get_orchagent_args()
    os.execv(ORCHAGENT_PATH, orchagent_args)


if __name__ == "__main__":
    main()
