from natsort import natsorted
from .. import vlan


def get_dhcp_helper_address(ctx, vlan):
    cfg, _ = ctx
    vlan_dhcp_helper_data, _, _ = cfg
    vlan_config = vlan_dhcp_helper_data.get(vlan)
    if not vlan_config:
        return ""

    dhcp_helpers = vlan_config.get('dhcp_servers', [])

    return '\n'.join(natsorted(dhcp_helpers))


vlan.VlanBrief.COLUMNS.append(('DHCP Helper Address', get_dhcp_helper_address))


def register(cli):
    pass

