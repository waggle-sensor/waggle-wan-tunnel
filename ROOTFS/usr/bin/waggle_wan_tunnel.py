#!/usr/bin/env python3
import argparse
from configparser import ConfigParser
from pathlib import Path
from socket import gethostbyname
import subprocess
import re
import logging


def get_interface_subnets(interface):
    try:
        output = subprocess.check_output(["ip", "addr", "show", interface]).decode()
    except subprocess.CalledProcessError:
        return []
    return scan_interface_subnets(output)


def scan_interface_subnets(s):
    return re.findall("inet ([0-9/.]+)", s)


def log_and_run(cmd):
    logging.debug("run %s", " \\\n\t".join(map(repr, cmd)))
    subprocess.run(cmd, check=True)


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

    excluded_subnets = [
        "127.0.0.1/24",                    # localhost
        "10.31.81.0/24",                   # lan
        "10.42.0.0/16",                    # kube pods
        "10.43.0.0/16",                    # kube services
        "172.17.0.1/16",                   # docker
        f"{bk_ip}/16",                     # beekeeper
        "10.0.0.1/8",                      # node build network
        *get_interface_subnets("wan0"),    # local wan
        *get_interface_subnets("wifi0"),   # local wifi
        *get_interface_subnets("modem0"),  # local modem (maybe not needed? for dns?)
    ]

    cmd_args = [
        "--listen", "12300",
        "--ssh-cmd", f"ssh {ssh_options} -o ServerAliveInterval={ssh_keepalive_interval} -o ServerAliveCountMax={ssh_keepalive_count} -i {bk_key}",
        "--remote", f"{bk_user}@{bk_host}:{bk_port}",
    ]

    # --debug flag enables verbose sshuttle logging too
    if args.debug:
        cmd_args += ["--verbose"]

    # add excluded subnets
    for subnet in excluded_subnets:
        cmd_args += ["--exclude", subnet]

    # route all non-excluded subnets
    cmd_args += ["0/0"]

    log_and_run(["sshuttle"] + cmd_args)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
