
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import ipaddress
import socket
import subprocess
from concurrent.futures import ThreadPoolExecutor
from getpass import getpass
import urllib.request
import os
from datetime import datetime

"""
RTSP Discovery + Path Discovery + Snapshot + VLC Launcher

Funciones:
- Escaneo RTSP real
- Descubrimiento de paths
- Captura snapshot HTTP
- Lanzamiento VLC Android

Pensado para Termux + VLC Android
Sin librerías externas
"""

RTSP_PORTS = [554, 8554, 10554]

RTSP_PATHS = [
    "/",
    "/live",
    "/h264",
    "/mpeg4",
    "/Streaming/Channels/101",
    "/cam/realmonitor?channel=1&subtype=0",
    "/user=admin&password=&channel=1&stream=0.sdp",
    "/profile1",
    "/videoMain",
]

SNAPSHOT_PATHS = [
    "/cgi-bin/snapshot.cgi",
    "/ISAPI/Streaming/channels/101/picture",
    "/onvif-http/snapshot",
    "/snapshot.jpg",
]

SOCKET_TIMEOUT = 2

found_streams = []


def generate_ips(cidr):
    net = ipaddress.ip_network(cidr, strict=False)
    return [str(ip) for ip in net.hosts()]


def rtsp_request(ip, port, path, method):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(SOCKET_TIMEOUT)
        sock.connect((ip, port))

        req = f"{method} rtsp://{ip}:{port}{path} RTSP/1.0\r\nCSeq: 1\r\n\r\n"
        sock.send(req.encode())

        data = sock.recv(1024)
        sock.close()

        if b"RTSP" in data:
            return True
    except:
        return False

    return False


def discover_paths(ip, port):
    valid = []

    for path in RTSP_PATHS:
        if rtsp_request(ip, port, path, "DESCRIBE"):
            valid.append(path)

    return valid


def scan_host(ip):
    for port in RTSP_PORTS:
        if rtsp_request(ip, port, "/", "OPTIONS"):
            paths = discover_paths(ip, port)
            for p in paths:
                found_streams.append((ip, port, p))


def discover_rtsp(cidr):
    ips = generate_ips(cidr)
    print(f"[+] Escaneando {len(ips)} hosts...")

    with ThreadPoolExecutor(max_workers=40) as exe:
        exe.map(scan_host, ips)


def choose_stream():
    if not found_streams:
        print("[-] No se encontraron streams.")
        exit()

    print("\nStreams detectados:\n")

    for i, s in enumerate(found_streams):
        print(f"[{i}] {s[0]}:{s[1]}{s[2]}")

    while True:
        c = input("\nSelecciona stream: ")
        if c.isdigit() and int(c) < len(found_streams):
            return found_streams[int(c)]


def try_snapshot(ip, user=None, pwd=None):
    """
    Intenta obtener snapshot vía HTTP.

    Guarda imagen si tiene éxito.
    """

    print("\n[+] Intentando snapshot...")

    for path in SNAPSHOT_PATHS:
        try:
            if user:
                url = f"http://{user}:{pwd}@{ip}{path}"
            else:
                url = f"http://{ip}{path}"

            response = urllib.request.urlopen(url, timeout=3)
            data = response.read()

            if len(data) > 5000:
                fname = f"snapshot_{ip}_{datetime.now().strftime('%H%M%S')}.jpg"
                with open(fname, "wb") as f:
                    f.write(data)

                print(f"[✓] Snapshot guardado: {fname}")
                return True

        except:
            continue

    print("[-] Snapshot no disponible")
    return False


def launch_vlc(ip, port, path, user, pwd):

    if user:
        url = f"rtsp://{user}:{pwd}@{ip}:{port}{path}"
    else:
        url = f"rtsp://{ip}:{port}{path}"

    print("\n[+] Abriendo VLC...")

    subprocess.run([
        "am",
        "start",
        "-a", "android.intent.action.VIEW",
        "-d", url,
        "-n", "org.videolan.vlc/org.videolan.vlc.gui.video.VideoPlayerActivity"
    ])


def main():

    print("\n=== RTSP + PATH + SNAPSHOT TOOL ===\n")

    cidr = input("CIDR (ej: 192.168.1.0/24): ")

    discover_rtsp(cidr)

    ip, port, path = choose_stream()

    print("\nAutenticación (ENTER si no requiere)")
    user = input("Usuario: ")
    pwd = ""

    if user:
        pwd = getpass("Password: ")

    try_snapshot(ip, user, pwd)

    launch_vlc(ip, port, path, user, pwd)


if __name__ == "__main__":
    main()