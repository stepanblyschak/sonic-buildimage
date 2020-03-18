#!/usr/bin/python

from __future__ import print_function

import sys
import struct
import json
import socket
import argparse

DEFAULT_WJH_SOCKET_PATH = '/var/run/wjh/wjh.sock'
RECV_BATCH_SIZE = 4096

def send_request(sock, request):
    request_encoded = json.dumps(request).encode()
    request_length = len(request_encoded)
    length = struct.pack('>l', request_length)
    print(struct.unpack('>l', length))
    sock.sendall(length)
    return sock.sendall(request_encoded)

def recv_response(sock):
    length_bytes_count = len(struct.pack('>l', 0))
    length_packed = b''
    while len(length_packed) < length_bytes_count:
        length_packed += sock.recv(length_bytes_count - len(length_packed))
    (response_length,) = struct.unpack('>l', length_packed)
    response_encoded = b''
    print(response_length)
    while len(response_encoded) < response_length:
        response_encoded += sock.recv(RECV_BATCH_SIZE)
    print(response_encoded)
    return json.loads(response_encoded.decode())

def pull(sock, channel_name):
    send_request(sock, {'request': 'pull', 'channel': channel_name})
    response = recv_response(sock)
    if 'err' in response:
        print('Error reply from daemon: {}'.format(response['err']), file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description='What Just Happened command line interface',
                                     version='0.0.1',
                                     formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-s', '--socket', type=str, default=DEFAULT_WJH_SOCKET_PATH,
            help='What Just Happened daemon Unix socket path')
    parser.add_argument('-p', '--pull', action='store_true', help='Pull What Just Happened channel')
    parser.add_argument('-c', '--channel', type=str, help='What Just Happened channel name')
    args = parser.parse_args()

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        sock.connect(('localhost', 9999))
    except socket.error as err:
        print('Failed to connect to daemon: {}'.format(err), file=sys.stderr)
        sys.exit(1)

    sock.settimeout(5)

    try:
        if args.pull:
            pull(sock, args.channel)
    except Exception as err:
        print('Exception: {}'.format(err), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

