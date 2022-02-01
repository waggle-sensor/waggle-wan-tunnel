#!/usr/bin/env python3
import argparse
from configparser import ConfigParser
from pathlib import Path
from socket import gethostbyname
import sys
import subprocess
import re
import logging
import os


def get_interface_subnets(interface):
    try:
        output = subprocess.check_output(["ip", "addr", "show", interface]).decode()
    except subprocess.CalledProcessError:
        return []
    return scan_interface_subnets(output)


def scan_interface_subnets(s):
    return re.findall("inet ([0-9/.]+)", s)


def get_excluded_subnets_from_config(config):
    """get list of space separated subnets from wan-tunnel.exclude."""
    return config.get("wan-tunnel", "exclude", fallback="").split()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true", help="enable verbose logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s %(message)s",
        datefmt="%Y/%m/%d %H:%M:%S")

    logging.info("running sshuttle")
    
    # get node and reverse tunnel config
    node_id = Path("/etc/waggle/node-id").read_text().strip()

    config = ConfigParser()
    config.read("/etc/waggle/config.ini")

    section = config["reverse-tunnel"]
    bk_host = section["host"]
    bk_port = section["port"]
    bk_key = section["key"]
    ssh_options = section.get("ssh-options", "")
    ssh_keepalive_interval = section.getint("keepalive-interval", 60)
    ssh_keepalive_count = section.getint("keepalive-count", 3)
    bk_ip = gethostbyname(bk_host)
    bk_user = f"node-{node_id}"

    excluded_subnets_from_config = get_excluded_subnets_from_config(config)

    excluded_subnets = [
        "127.0.0.1/24",                 # localhost
        "10.0.0.0/8",                   # class A networks
        "172.16.0.0/12",                # class B networks
        "192.168.0.0/16",               # class C networks
        f"{bk_ip}/16",                  # beekeeper
        *excluded_subnets_from_config,  # additional subnets from config
    ]

    # NOTE the following important networks are excluded via the class A, B, C rules above:
    # 1. kubernetes pod network is 10.42.0.0/16 (class A)
    # 2. kubernetes service network is 10.43.0.0/16 (class A)
    # 3. docker network is 172.17.0.1/16 (class B)
    # 4. lan network is 10.31.81.0/24 (class A)
    # 5. wan0 and wifi0 networks are hopefully class A, B or C

    cmd_args = [
        "--listen", "12300",
        "--ssh-cmd", f"ssh {ssh_options} -o ServerAliveInterval={ssh_keepalive_interval} -o ServerAliveCountMax={ssh_keepalive_count} -i {bk_key}",
        "--remote", f"{bk_user}@{bk_host}:{bk_port}",
    ]

    # --debug flag enables verbose sshuttle logging too
    if args.debug:
        cmd_args += ["--verbose"]

    # add excluded subnets
    for subnet in sorted(set(excluded_subnets)):
        cmd_args += ["--exclude", subnet]

    # route all non-excluded subnets
    cmd_args += ["0/0"]

    # NOTE I am not using the --dns flag as this forwards DNS through the tunnel,
    # as opposed to excludes. the actual iptables rule added with the flag is:
    # -t nat -A sshuttle-12300 -j REDIRECT --dest 127.0.0.53/32 -p udp --dport 53 --to-ports 12300 -m ttl ! --ttl 42

    # construct command with args
    cmd = ["sshuttle"] + cmd_args
    logging.debug("running %s", " \\\n\t".join(map(repr, cmd)))

    # run sshuttle and watch output
    with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT) as proc:
        # wait until connected to indicate that service is ready
        while True:
            line = proc.stdout.readline()
            # should only receive this output when unexpectedly terminated
            if line == b"":
                logging.info("sshuttle terminated unexpectedly")
                break
            # notify systemd that service is ready
            if b"Connected." in line:
                logging.info("sshuttle is connected. notifying systemd")
                subprocess.check_call(["systemd-notify", "--ready"])
                break
        # copy remaining output to stdout
        while True:
            line = proc.stdout.readline()
            if line == b"":
                break
            sys.stdout.write(line)
        # wait for sshuttle returncode
        returncode = proc.wait()

    sys.exit(returncode)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
