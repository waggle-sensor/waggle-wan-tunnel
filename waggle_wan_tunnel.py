#!/usr/bin/env python3
import argparse
from configparser import ConfigParser
from pathlib import Path
from socket import gethostbyname
import re
import subprocess
import logging


def remove_existing_sshuttle_state():
    output = subprocess.check_output(["iptables-save", "-t", "nat"]).decode()
    chains = re.findall(":(sshuttle-\d+)", output)
    rules = re.findall("-A(.*sshuttle.*)", output)

    for rule in rules:
        logging.debug("removing rule: %s", rule)
        subprocess.check_call(["iptables", "-t", "nat", "-D"] + rule.split())
    
    for chain in chains:
        logging.debug("removing chain: %s", chain)
        subprocess.check_call(["iptables", "-t", "nat", "-X", chain])


def run(cmd):
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

    logging.info("removing any existing sshuttle state")
    remove_existing_sshuttle_state()

    logging.info("running sshuttle")
    run([
        "sshuttle",
        "-e", f"ssh {ssh_options} -o ServerAliveInterval={ssh_keepalive_interval} -o ServerAliveCountMax={ssh_keepalive_count} -i {bk_key}",
        "-x", f"{bk_ip}/16",   # tunnel cidr
        "-x", "10.31.81.0/24", # lan cidr
        "-x", "10.42.0.0/16",  # k3s pod cidr
        "-x", "10.43.0.0/16",  # k3s svc cidr
        "-r", f"{bk_user}@{bk_host}:{bk_port}",
        "0/0",
    ])


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
