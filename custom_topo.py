#!/usr/bin/env python3
"""
custom_topo.py
Mininet script implementing the requested topology with TCLink parameters.
Run with: sudo python3 custom_topo.py
"""

from mininet.net import Mininet
from mininet.node import Controller, OVSSwitch
from mininet.link import TCLink
from mininet.log import setLogLevel, info

def run():
    setLogLevel('info')
    net = Mininet(controller=Controller, link=TCLink, switch=OVSSwitch)

    info('*** Adding controller\n')
    c0 = net.addController('c0')

    info('*** Adding switches\n')
    s1 = net.addSwitch('s1')
    
    s2 = net.addSwitch('s2')
    s3 = net.addSwitch('s3')
    s4 = net.addSwitch('s4')

    info('*** Adding hosts\n')
    h1 = net.addHost('h1', ip='10.0.0.1/24')
    h2 = net.addHost('h2', ip='10.0.0.2/24')
    h3 = net.addHost('h3', ip='10.0.0.3/24')
    h4 = net.addHost('h4', ip='10.0.0.4/24')
    dns = net.addHost('dns', ip='10.0.0.5/24')

    info('*** Creating links (bw=100Mbps, specified delays)\n')
    # host->switch links (100Mbps, 2ms)
    net.addLink(h1, s1, bw=100, delay='2ms')
    net.addLink(h2, s2, bw=100, delay='2ms')
    net.addLink(h3, s3, bw=100, delay='2ms')
    net.addLink(h4, s4, bw=100, delay='2ms')

    # switch-to-switch links with given delays
    net.addLink(s1, s2, bw=100, delay='5ms')
    net.addLink(s2, s3, bw=100, delay='8ms')
    net.addLink(s3, s4, bw=100, delay='10ms')

    # s2 to dns (1ms)
    net.addLink(s2, dns, bw=100, delay='1ms')

    info('*** Starting network\n')
    net.start()

    info('*** Setting default routes (not strictly required for L2)\n')
    # Not necessary for simple ping in same /24, but left here if you want explicit default route:
    for h in [h1, h2, h3, h4, dns]:
        h.cmd('ip route add default dev {}'.format(h.defaultIntf()))

    info('*** Running tests\n')
    info('*** Ping all hosts\n')
    net.pingAll()
    info('*** Ping specific pairs (h1->h2 ,h1->h3, h1->h4 and h1->dns)\n')
    info(h1.cmd('ping -c 3 10.0.0.2'))
    info(h1.cmd('ping -c 3 10.0.0.3'))
    info(h1.cmd('ping -c 3 10.0.0.4'))
    info(h1.cmd('ping -c 3 10.0.0.5'))


    info('*** Run iperf between h1 and h4 (TCP)\n')
    # Start iperf server on h4
    h4.cmd('iperf -s -D')   # -D run as daemon
    info(h1.cmd('iperf -c 10.0.0.4 -t 5'))

    info('*** You can use CLI now (type exit or ctrl+D to stop)\n')
    from mininet.cli import CLI
    CLI(net)

    info('*** Stopping network\n')
    net.stop()

if __name__ == '__main__':
    run()
