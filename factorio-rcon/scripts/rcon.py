#!/usr/bin/env python3
"""Minimal Factorio RCON client.

Usage:
    python rcon.py "cmd1" "cmd2" ...
Env overrides: RCON_HOST, RCON_PORT, RCON_PWD
Lua commands must carry the console prefix, e.g. '/c rcon.print("hi")'.
"""
import os
import socket
import struct
import sys

HOST = os.environ.get("RCON_HOST", "127.0.0.1")
PORT = int(os.environ.get("RCON_PORT", "25575"))
PWD = os.environ.get("RCON_PWD", "")


def pack(rid, ptype, body):
    b = body.encode("utf-8") + b"\x00\x00"
    return struct.pack("<iii", 4 + 4 + len(b), rid, ptype) + b


def recv(sock):
    hdr = b""
    while len(hdr) < 12:
        chunk = sock.recv(12 - len(hdr))
        if not chunk:
            raise EOFError("connection closed")
        hdr += chunk
    length, rid, ptype = struct.unpack("<iii", hdr)
    body = b""
    want = length - 8
    while len(body) < want:
        chunk = sock.recv(want - len(body))
        if not chunk:
            break
        body += chunk
    return rid, ptype, body.rstrip(b"\x00").decode("utf-8", "replace")


def main(cmds):
    s = socket.create_connection((HOST, PORT), timeout=120)
    s.sendall(pack(1, 3, PWD))
    rid, _ptype, _body = recv(s)
    if rid == -1:
        print("AUTH FAILED")
        return 2
    out = []
    for i, cmd in enumerate(cmds):
        s.sendall(pack(i + 2, 2, cmd))
        _rid, _ptype, body = recv(s)
        out.append(body)
        print(body)
    s.close()
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    sys.exit(main(sys.argv[1:]))
