#!/usr/bin/env python

import os
from logging import debug, info, warning, DEBUG, basicConfig
from subprocess import Popen, PIPE
import yaml
from shutil import rmtree
from tempfile import mkstemp, mkdtemp
from socket import inet_ntoa
from struct import pack
import netifaces
import re

LOG_FILE = '/tmp/compute_post_deployment.log'
ASTUTE_PATH = '/etc/astute.yaml'
ACCESS_SECTION = 'xenserver-fuel-plugin'

basicConfig(filename=LOG_FILE, level=DEBUG)


def execute(*cmd, **kwargs):
    cmd = map(str, cmd)
    info(' '.join(cmd))
    proc = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)

    if 'prompt' in kwargs:
        prompt = kwargs.get('prompt')
        proc.stdout.flush()
        (out, err) = proc.communicate(prompt)
    else:
        out = proc.stdout.readlines()
        err = proc.stderr.readlines()
        (out, err) = map(' '.join, [out, err])

    if out:
        debug(out)
    if err:
        warning(err)

    return (out, err)


def ssh(host, username, password, *cmd, **kwargs):
    cmd = map(str, cmd)

    return execute('sshpass', '-p', password, 'ssh',
                   '-o', 'StrictHostKeyChecking=no',
                   '%s@%s' % (username, host), *cmd,
                   prompt=kwargs.get('prompt'))


def scp(host, username, password, target_path, filename):
    return execute('sshpass', '-p', password, 'scp',
                   '-o', 'StrictHostKeyChecking=no', filename,
                   '%s@%s:%s' % (username, host, target_path))


def get_astute(astute_path):
    """Return the root object read from astute.yaml"""
    if not os.path.exists(astute_path):
        warning('%s not found' % astute_path)
        return None

    astute = yaml.load(open(astute_path))
    return astute


def get_access(astute, access_section):
    """Return username and password filled in plugin."""
    if not access_section in astute:
        warning('%s not found' % access_section)
        return None, None

    access = astute[access_section]
    info('username: {username}'.format(**access))
    info('password: {password}'.format(**access))
    return access['username'], access['password']


def get_endpoints(astute):
    """Return the IP addresses of the endpoints connected to
    storage/mgmt network.
    """
    endpoints = astute['network_scheme']['endpoints']
    endpoints = dict([(
        k.replace('br-', ''),
        endpoints[k]['IP'][0]
    ) for k in endpoints])

    info('storage network: {storage}'.format(**endpoints))
    info('mgmt network: {mgmt}'.format(**endpoints))
    return endpoints


def init_eth(eth):
    """Initialize the net interface connected to HIMN 

    Returns:
        the IP addresses of local host and XenServer.
    """
    if not eth in netifaces.interfaces():
        warning('%s not found' % eth)
        return None, None

    execute('dhclient', eth)
    execute('ifconfig', eth)

    fname = '/etc/network/interfaces.d/ifcfg-' + eth
    s = 'auto {eth}\niface {eth} inet dhcp'.format(eth=eth)
    with open(fname, 'w') as f:
        f.write(s)
    info('%s created' % fname)
    execute('ifdown', eth)
    execute('ifup', eth)

    addr = netifaces.ifaddresses(eth).get(2)
    if addr:
        addr_local = addr[0]['addr']
        addr_remote = '.'.join(addr_local.split('.')[:-1] + ['1'])
        info('HIMN on %s : %s' % (eth, addr_remote))
        return addr_local, addr_remote
    else:
        warning('HIMN failed to get IP address from XenServer')
        return None, None


def install_xenapi_sdk(xenapi_url):
    """Install XenAPI Python SDK"""
    execute('cp', 'XenAPI.py', '/usr/lib/python2.7/dist-packages/')


def create_novacompute_conf(himn, username, password):
    """Fill nova-compute.conf with HIMN IP and root password. """
    template = '\n'.join([
        '[DEFAULT]',
        'compute_driver=xenapi.XenAPIDriver',
        '[xenserver]',
        'connection_url=http://%s',
        'connection_username="%s"',
        'connection_password="%s"'
    ])

    s = template % (himn, username, password)
    fname = '/etc/nova/nova-compute.conf'
    with open(fname, 'w') as f:
        f.write(s)
    info('%s created' % fname)


def restart_nova_services():
    """Restart nova services"""
    execute('stop', 'nova-compute')
    execute('start', 'nova-compute')
    execute('stop', 'nova-network')
    execute('start', 'nova-network')


def route_to_compute(endpoints, himn_xs, himn_local, username, password):
    """Route storage/mgmt requests to compute nodes. """
    (out, err) = ssh(himn_xs, username, password, 'route', '-n')
    _net = lambda ip: '.'.join(ip.split('.')[:-1] + ['0'])
    _mask = lambda cidr: inet_ntoa(pack(
        '>I', 0xffffffff ^ (1 << 32 - int(cidr)) - 1))
    _routed = lambda net, mask, gw: re.search(r'%s\s+%s\s+%s\s+' % (
        net.replace('.', r'\.'),
        gw.replace('.', r'\.'),
        mask
    ), out)

    endpoint_names = ['storage', 'mgmt']
    for endpoint_name in endpoint_names:
        endpoint = endpoints.get(endpoint_name)
        if endpoint:
            ip, cidr = endpoint.split('/')
            net, mask = _net(ip), _mask(cidr)
            if not _routed(net, mask, himn_local):
                ssh(himn_xs, username, password,
                    'route', 'add',
                    '-net', net, 'netmask', mask, 'gw', himn_local)
        else:
            info('%s network ip is missing' % endpoint_name)


def install_suppack(himn, username, password):
    """Install xapi driver supplemental pack. """
    # TODO: check if installed
    scp(himn, username, password, '/tmp/', 'novaplugins.iso')
    (out, err) = ssh(
        himn, username, password, 'xe-install-supplemental-pack',
        '/tmp/novaplugins.iso', prompt='Y\n')
    ssh(himn, username, password, 'rm', '/tmp/novaplugins.iso')


def forward_from_himn(eth):
    """Forward packets from HIMN to storage/mgmt network. """
    execute('sed', '-i', 's/#net.ipv4.ip_forward/net.ipv4.ip_forward/g',
            '/etc/sysctl.conf')
    execute('sysctl', '-p', '/etc/sysctl.conf')

    endpoint_names = ['br-storage', 'br-mgmt']
    for endpoint_name in endpoint_names:
        execute('iptables', '-t', 'nat', '-A', 'POSTROUTING',
                '-o', endpoint_name, '-j', 'MASQUERADE')
        execute('iptables', '-A', 'FORWARD',
                '-i', endpoint_name, '-o', eth,
                '-m', 'state', '--state', 'RELATED,ESTABLISHED',
                '-j', 'ACCEPT')
        execute('iptables', '-A', 'FORWARD',
                '-i', eth, '-o', endpoint_name,
                '-j', 'ACCEPT')

    execute('iptables', '-t', 'filter', '-S', 'FORWARD')
    execute('iptables', '-t', 'nat', '-S', 'POSTROUTING')


if __name__ == '__main__':
    eth = 'eth2'
    install_xenapi_sdk(XENAPI_URL)
    astute = get_astute(ASTUTE_PATH)
    if astute:
        username, password = get_access(astute, ACCESS_SECTION)
        endpoints = get_endpoints(astute)
        himn_local, himn_xs = init_eth(eth)
        if username and password and endpoints and himn_local and himn_xs:
            route_to_compute(
                endpoints, himn_xs, himn_local, username, password)
            install_suppack(himn_xs, username, password)
            forward_from_himn(eth)
            create_novacompute_conf(himn_xs, username, password)
            restart_nova_services()
