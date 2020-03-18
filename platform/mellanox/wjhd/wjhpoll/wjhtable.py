import time
import socket
import tabulate

class WjhTable:
    HEADERS = [
        "#",
        "Timestamp",
        "sPort",
        "dPort",
        "VLAN",
        "sMAC",
        "dMAC",
        "EthType",
        "SrcIP:Port",
        "DstIP:Port",
        "IP Proto",
        "Drop Group",
        "Severity",
        "Drop Reason - Recommended Action"
    ]

    IPPROTO_TABLE = {
        num: name[len("IPPROTO_"):] for name, num in vars(socket).items() if name.startswith("IPPROTO")
    }

    ETHTYPE_TABLE = {
        0x8100: 'Dot1Q',
        0x0800: 'IPv4',
        0x0806: 'ARP',
        0x86dd: 'IPv6',
    }

    def __init__(self, data):
        self._data = data

    def to_string(self):
        ''' Format data into table
        >>> data = [{}]
        >>> data[0]['timestamp'] = 1584457123.913561
        >>> data[0]['sport'] = 'Ethernet120'
        >>> data[0]['dport'] = 'Ethernet124'
        >>> data[0]['vlan'] = 1000
        >>> data[0]['smac'] = '00:aa:bb:cc:dd:ff'
        >>> data[0]['dmac'] = '00:ff:dd:cc:bb:aa'
        >>> data[0]['ethtype'] = 0x0800
        >>> data[0]['sip'] = '11.11.11.11'
        >>> data[0]['sl4port'] = 3123
        >>> data[0]['dip'] = '127.0.0.1'
        >>> data[0]['dl4port'] = 8080
        >>> data[0]['ipproto'] = 0x6
        >>> data[0]['group'] = 'L3'
        >>> data[0]['severity'] = 'Error'
        >>> data[0]['reason'] = 'Destination IP is loopback address - Bad packet was received from the peer'
        >>> print WjhTable(data).to_string()
          #  Timestamp                sPort        dPort          VLAN  sMAC               dMAC               EthType    SrcIP:Port        DstIP:Port       IP Proto    Drop Group    Severity    Drop Reason - Recommended Action
        ---  -----------------------  -----------  -----------  ------  -----------------  -----------------  ---------  ----------------  ---------------  ----------  ------------  ----------  -------------------------------------
          1  2020/03/17 14:58:43.913  Ethernet120  Ethernet124    1000  00:aa:bb:cc:dd:ff  00:ff:dd:cc:bb:aa  IPv4       11.11.11.11:3123  127.0.0.1:       TCP         L3            Error       Destination IP is loopback address -
                                                                                                                                           8080 (http-alt)                                        Bad packet was received from the peer
        '''
        table_rows = []
        for index, event in enumerate(self._data):
            row = [
                index + 1,
                WjhTable.format_timestamp(event['timestamp']),
                event['sport'],
                event.get('dport', 'N/A'),
                event.get('vlan', 'N/A'),
                event.get('smac', 'N/A'),
                event.get('dmac', 'N/A'),
                WjhTable.format_ethtype(event.get('ethtype')),
                WjhTable.compact_string(
                    WjhTable.format_ip_port(
                        event.get('sip'),
                        event.get('sl4port')
                    ),
                    ':',
                    21
                ),
                WjhTable.compact_string(
                    WjhTable.format_ip_port(
                        event.get('dip'),
                        event.get('dl4port')
                    ),
                    ':',
                    21
                ),
                WjhTable.format_ipproto(event.get('ipproto')),
                event.get('group', 'N/A'),
                event.get('severity', 'N/A'),
                WjhTable.compact_string(
                    event.get('reason', 'N/A'),
                    ' ',
                    45
                )
            ]
            table_rows.append(row)
        return tabulate.tabulate(table_rows, self.HEADERS)

    @staticmethod
    def format_timestamp(timestamp):
        ''' Serialize timestamp in format %Y/%m/%d %T.%usec
        >>> print WjhTable.format_timestamp(1584457123.913561)
        2020/03/17 14:58:43.913
        '''
        timestruct = time.gmtime(timestamp)
        result = time.strftime('%Y/%m/%d %T', timestruct)
        usec = int((timestamp - int(timestamp)) * 1E3)
        result = '{}.{}'.format(result, usec)
        return result

    @staticmethod
    def format_ethtype(typenum):
        '''
        >>> print WjhTable.format_ethtype(0x0800)
        IPv4
        >>> print WjhTable.format_ethtype(0x1234)
        0x1234
        '''
        if typenum is None:
            return 'N/A'
        ethprotoname = WjhTable.ETHTYPE_TABLE.get(typenum)
        if ethprotoname is None:
            return hex(typenum)
        return ethprotoname

    @staticmethod
    def format_ipproto(proto):
        '''
        >>> print WjhTable.format_ipproto(0x6)
        TCP
        >>> print WjhTable.format_ipproto(0x1)
        ICMP
        >>> print WjhTable.format_ipproto(0x66)
        0x66
        '''
        if proto is None:
            return 'N/A'
        protoname = WjhTable.IPPROTO_TABLE.get(proto)
        if protoname is None:
            return hex(proto)
        return protoname

    @staticmethod
    def format_ip_port(ip, port):
        '''
        >>> print WjhTable.format_ip_port(None, None)
        N/A
        >>> print WjhTable.format_ip_port('192.168.0.188', 80)
        192.168.0.188:80 (http)
        >>> print WjhTable.format_ip_port('fe80::7efe:90ff:fe6f::39bb', None)
        fe80::7efe:90ff:fe6f::39bb
        >>> print WjhTable.format_ip_port('fe80::7efe:90ff:fe6f::39bb', 12345)
        [fe80::7efe:90ff:fe6f::39bb]:12345
        '''
        result = 'N/A'
        if ip is None:
            return result
        result = '{}'.format(ip)
        if port is None:
            return result
        if ':' in result:
            result = '[{}]'.format(result)
        result = '{}:{}'.format(result, port)
        try:
            result = '{} ({})'.format(result, socket.getservbyport(port))
        except socket.error:
            pass
        return result

    @staticmethod
    def compact_string(string, delimiter, width):
        '''
        >>> print WjhTable.compact_string('Ingress VLAN membership filter - Please check configuration on both ends of the link', ' ', 45)
        Ingress VLAN membership filter - Please check
        configuration on both ends of the link
        >>> print WjhTable.compact_string('[abab:baba:abab:baba:abab:baba:abab:baba]:8080 (http-alt)', ':', 21)
        [abab:baba:abab:baba:
        abab:baba:
        abab:
        baba]:8080 (http-alt)
        '''
        if len(string) < width:
            return string
        result = ''
        tokens = string.split(delimiter)
        firstpart = delimiter.join(tokens[:len(tokens)/2])
        secondpart= delimiter.join(tokens[len(tokens)/2:])
        if delimiter in firstpart and len(firstpart) > width:
            firstpart = WjhTable.compact_string(firstpart, delimiter, width)
        if delimiter in secondpart and len(secondpart) > width:
            secondpart = WjhTable.compact_string(secondpart, delimiter, width)
        result = '{}\n'.format('' if delimiter.isspace() else delimiter).join([firstpart, secondpart])
        return result




