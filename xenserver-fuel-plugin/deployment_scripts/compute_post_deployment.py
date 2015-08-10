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
XENAPI_URL = \
    'https://pypi.python.org/packages/source/X/XenAPI/XenAPI-1.2.tar.gz'

basicConfig(filename=LOG_FILE, level=DEBUG)


def execute(*cmd):
    cmd = map(str, cmd)
    proc = Popen(cmd, stdout=PIPE, stderr=PIPE)

    out = proc.stdout.readlines()
    err = proc.stderr.readlines()

    (out, err, cmd) = map(' '.join, [out, err, cmd])

    info(cmd)
    if out:
        debug(out)
    if err:
        warning(err)

    return (out, err, cmd)


def ssh(host, username, password, *cmd):
    cmd = map(str, cmd)

    return execute(*(['sshpass', '-p', password, 'ssh',
                      '%s@%s' % (username, host)] + cmd))


def scp(host, username, password, target_path, filename):
    return execute('sshpass', '-p', '"%s"' % password, 'scp', filename,
                   '%s@%s:%s' % (username, host, target_path))


def get_astute(astute_path):
    if not os.path.exists(astute_path):
        warning('%s not found' % astute_path)
        return None

    astute = yaml.load(open(astute_path))
    return astute


def get_access(astute, access_section):
    if not access_section in astute:
        warning('%s not found' % access_section)
        return None, None

    access = astute[access_section]
    info('username: {username}'.format(**access))
    info('password: {password}'.format(**access))
    return access['username'], access['password']


def get_endpoints(astute):
    endpoints = astute['network_scheme']['endpoints']
    endpoints = dict([(
        k.replace('br-', ''),
        endpoints[k]['IP'][0]
    ) for k in endpoints])

    info('storage network: {storage}'.format(**endpoints))
    info('mgmt network: {mgmt}'.format(**endpoints))
    return endpoints


def init_eth(eth):
    if not eth in netifaces.interfaces():
        warning('%s not found' % eth)
        return None

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
        local_ip = addr[0]['addr']
        xs_ip = '.'.join(local_ip.split('.')[:-1] + ['1'])
        info('HIMN on %s : %s' % (eth, xs_ip))
        return xs_ip
    else:
        warning('HIMN failed to get IP address from XenServer')
        return None


def install_xenapi_sdk(xenapi_url):
    xenapi_zipball = mkstemp()[1]
    xenapi_sources = mkdtemp()

    execute('wget', '-qO', xenapi_zipball, xenapi_url)

    execute('tar', '-zxf', xenapi_zipball, '-C', xenapi_sources)
    subdirs = os.listdir(xenapi_sources)
    if (len(subdirs) != 1) or (not subdirs[0].startswith('XenAPI')):
        warning('fail to extract %s' % xenapi_url)
        return

    src = os.path.join(xenapi_sources, subdirs[0], 'XenAPI.py')
    dest = '/usr/lib/python2.7/dist-packages'
    execute('cp', src, dest)

    os.remove(xenapi_zipball)
    rmtree(xenapi_sources)


def create_novacompute_conf(himn, username, password):
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
    execute('stop', 'nova-compute')
    execute('start', 'nova-compute')
    execute('stop', 'nova-network')
    execute('start', 'nova-network')


def route_to_himn(endpoints, himn, username, password):
    (out, err, cmd) = ssh(himn, username, password, 'route -n')
    _netmask = lambda cidr: inet_ntoa(pack(
        '>I', 0xffffffff ^ (1 << 32 - int(cidr)) - 1))
    _routed = lambda ip, mask, gw: re.search(r'%s\s+%s\s+%s\s+' % (
        ip.replace('.', r'\.'),
        gw.replace('.', r'\.'),
        mask
    ), out)
    _route = lambda ip, mask, gw: ssh(
        himn, username, password, 'route', 'add', '-net', ip, 'netmask',
        mask, 'gw', gw)

    nets = ['storage', 'mgmt']
    for net in nets:
        endpoint = endpoints.get(net)
        if endpoint:
            ip, cidr = endpoint.split('/')
            netmask = _netmask(cidr)
            if not _routed(ip, netmask, himn):
                _route(ip, netmask, himn)
        else:
            info('%s network ip is missing' % net)


def install_suppack(himn, username, password):
    # TODO: check exists
    scp(himn, username, password, '/tmp/', 'novaplugins.iso')
    ssh(himn, username, password,
        'xe-install-supplemental-pack', '/tmp/novaplugins.iso')
    ssh(himn, username, password, 'rm', '/tmp/novaplugins.iso')


def forward_from_himn(eth):
    (out, err, cmd) = execute('iptables', '-S')
    if eth in out:
        execute('iptables', '-A', 'FORWARD', '-i', eth, '-j', 'ACCEPT')
        execute('sed', '-i', 's/#net.ipv4.ip_forward/net.ipv4.ip_forward/g',
                '/etc/sysctl.conf')
        execute('sysctl', '-p', '/etc/sysctl.conf')
        execute('iptables', '-t', 'nat', '-A', 'POSTROUTING', '-o', eth,
                '-j', 'MASQUERADE')


if __name__ == '__main__':
    eth = 'eth2'
    install_xenapi_sdk(XENAPI_URL)
    astute = get_astute(ASTUTE_PATH)
    if astute:
        username, password = get_access(astute, ACCESS_SECTION)
        endpoints = get_endpoints(astute)
        himn = init_eth(eth)
        if username and password and endpoints and himn:
            route_to_himn(endpoints, himn, username, password)
            install_suppack(himn, username, password)
            forward_from_himn(eth)
            create_novacompute_conf(himn, username, password)
            restart_nova_services()
