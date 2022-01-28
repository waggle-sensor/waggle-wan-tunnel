# Waggle WAN Tunnel

This service manages an sshuttle connection through the ssh tunnel to beekeeper.

By default it excludes forwarding the following subnets:

```text
127.0.0.1/24    localhost
10.31.81.0/24   lan
10.42.0.0/16    kubernetes pods
10.43.0.0/16    kubernetes services
172.17.0.1/16   docker
beekeeper/16    services sharing beekeeper cidr
wan0/24         wan0 subnet at start time, if available
wifi0/24        wifi0 subnet at start time, if available
modem0/24       modem0 subnet at start time, if available
```

Additionally, all subnets listed in `/etc/waggle/config.ini` in `wan-tunnel.exclude` will be excluded. For example:

```ini
[wan-tunnel]
exclude = 1.2.3.4/24 10.0.0.1/8 192.168.1.1/24
```
