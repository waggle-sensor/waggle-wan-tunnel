#!/usr/bin/env python3
from configparser import ConfigParser
from pathlib import Path
from socket import gethostbyname
import re
import subprocess
import time


def remove_stale_sshuttle_state():
    print("removing stale sshuttle iptables state", flush=True)

    # scan sshuttle rules and chains in nat table
    output = subprocess.check_output(["iptables-save", "-t", "nat"]).decode()
    chains = re.findall(":(sshuttle-\d+)", output)
    rules = re.findall("-A(.*sshuttle.*)", output)

    for rule in rules:
        print("removing rule", rule, flush=True)
        subprocess.check_call(["iptables", "-t", "nat", "-D"] + rule.split())
    
    for chain in chains:
        print("removing chain", chain, flush=True)
        subprocess.check_call(["iptables", "-t", "nat", "-X", chain])

    print("done", flush=True)


def main():
    remove_stale_sshuttle_state()

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

    sshuttle_cmd = [
        "sshuttle",
        "-e", f"ssh {ssh_options} -o ServerAliveInterval={ssh_keepalive_interval} -o ServerAliveCountMax={ssh_keepalive_count} -i {bk_key}",
        "-x", f"{bk_ip}/16",  # tunnel cidr
        "-x", "10.31.81.0/24",  # lan cidr
        "-x", "10.42.0.0/16",  # k3s pod cidr
        "-x", "10.43.0.0/16",  # k3s svc cidr
        "-r", f"{bk_user}@{bk_host}:{bk_port}",
        "0/0",
    ]
    print("running", " \\\n\t".join(map(repr, sshuttle_cmd)), flush=True)
    subprocess.run(sshuttle_cmd, check=True)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
