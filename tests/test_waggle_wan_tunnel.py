from waggle_wan_tunnel import scan_interface_subnets
import unittest

class TestProgram(unittest.TestCase):

    def test_scan_ip_addr_subsets(self):
        subsets = scan_interface_subnets("""
3: wan0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc pfifo_fast state UP group default qlen 1000
    link/ether 48:b0:2d:15:bc:68 brd ff:ff:ff:ff:ff:ff
    inet 192.168.88.251/24 brd 192.168.88.255 scope global dynamic noprefixroute wan0
       valid_lft 419sec preferred_lft 419sec
""")
        self.assertEqual(subsets, ["192.168.88.251/24"])

        subsets = scan_interface_subnets("""
3: wwan0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc pfifo_fast state UP group default qlen 1000
    link/ether 48:b0:2d:15:bc:68 brd ff:ff:ff:ff:ff:ff
    inet 192.168.88.251/16 brd 192.168.88.255 scope global dynamic noprefixroute wan0
       valid_lft 419sec preferred_lft 419sec
    inet 192.168.88.252/24 brd 192.168.88.255 scope global dynamic noprefixroute wan0
       valid_lft 419sec preferred_lft 419sec
""")
        self.assertEqual(subsets, ["192.168.88.251/16", "192.168.88.252/24"])


if __name__ == "__main__":
    unittest.main()
