#!/usr/bin/env python

import ConfigParser
from logging import basicConfig
from logging import debug
from logging import DEBUG
from logging import info
from logging import warning
import netifaces
import os
import re
from socket import inet_ntoa
from struct import pack
from subprocess import PIPE
from subprocess import Popen
import sys
import yaml


ASTUTE_PATH = '/etc/astute.yaml'
ASTUTE_SECTION = 'fuel-plugin-xenserver'
LOG_ROOT = '/var/log/fuel-plugin-xenserver'
LOG_FILE = 'compute_post_deployment.log'
HIMN_IP = '169.254.0.1'
INT_BRIDGE = 'br-int'
XS_PLUGIN_ISO = 'xenserverplugins-liberty.iso'
DIST_PACKAGES_DIR = '/usr/lib/python2.7/dist-packages/'

if not os.path.exists(LOG_ROOT):
    os.mkdir(LOG_ROOT)

basicConfig(filename=os.path.join(LOG_ROOT, LOG_FILE), level=DEBUG)


def reportError(err):
    warning(err)
    raise Exception(err)


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
        (out, err) = (out.replace('\n', ''), err.replace('\n', ''))

    if out:
        debug(out)

    if proc.returncode is not None and proc.returncode != 0:
        reportError(err)

    return out


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
        reportError('%s not found' % astute_path)

    astute = yaml.load(open(astute_path))
    return astute


def astute_get(dct, keys, default=None, fail_if_missing=True):
    """A safe dictionary getter"""
    for key in keys:
        if key in dct:
            dct = dct[key]
        else:
            if fail_if_missing:
                reportError('Value of "%s" is missing' % key)
            return default
    return dct


def get_options(astute, astute_section):
    """Return username and password filled in plugin."""
    if astute_section not in astute:
        reportError('%s not found' % astute_section)

    options = astute[astute_section]
    info('username: {username}'.format(**options))
    info('password: {password}'.format(**options))
    info('install_xapi: {install_xapi}'.format(**options))
    return options['username'], options['password'], \
        options['install_xapi']


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


def init_eth():
    """Initialize the net interface connected to HIMN

    Returns:
        the IP addresses of local host and XenServer.
    """

    domid = execute('xenstore-read', 'domid')
    himn_mac = execute(
        'xenstore-read',
        '/local/domain/%s/vm-data/himn_mac' % domid)
    info('himn_mac: %s' % himn_mac)

    _mac = lambda eth: \
        netifaces.ifaddresses(eth).get(netifaces.AF_LINK)[0]['addr']
    eths = [eth for eth in netifaces.interfaces() if _mac(eth) == himn_mac]
    if len(eths) != 1:
        reportError('Cannot find eth matches himn_mac')

    eth = eths[0]
    info('himn_eth: %s' % eth)

    ip = netifaces.ifaddresses(eth).get(netifaces.AF_INET)

    if not ip:
        execute('dhclient', eth)
        fname = '/etc/network/interfaces.d/ifcfg-' + eth
        s = ('auto {eth}\n'
             'iface {eth} inet dhcp\n'
             'post-up route del default dev {eth}').format(eth=eth)
        with open(fname, 'w') as f:
            f.write(s)
        info('%s created' % fname)
        execute('ifdown', eth)
        execute('ifup', eth)
        ip = netifaces.ifaddresses(eth).get(netifaces.AF_INET)

    if ip:
        himn_local = ip[0]['addr']
        himn_xs = '.'.join(himn_local.split('.')[:-1] + ['1'])
        if HIMN_IP == himn_xs:
            info('himn_local: %s' % himn_local)
            return eth, himn_local

    reportError('HIMN failed to get IP address from XenServer')


def check_hotfix_exists(himn, username, password, hotfix):
    out = ssh(HIMN_IP, username, password,
              'xe patch-list name-label=%s' % hotfix)
    if not out:
        reportError('Hotfix %s has not been installed' % hotfix)


def install_xenapi_sdk():
    """Install XenAPI Python SDK"""
    execute('cp', 'XenAPI.py', DIST_PACKAGES_DIR)


def create_novacompute_conf(himn, username, password, public_ip):
    """Fill nova-compute.conf with HIMN IP and root password. """
    mgmt_if = netifaces.ifaddresses('br-mgmt')
    if mgmt_if and mgmt_if.get(netifaces.AF_INET) \
            and mgmt_if.get(netifaces.AF_INET)[0]['addr']:
        mgmt_ip = mgmt_if.get(netifaces.AF_INET)[0]['addr']
    else:
        reportError('Cannot get IP Address on Management Network')

    filename = '/etc/nova/nova-compute.conf'
    cf = ConfigParser.ConfigParser()
    try:
        cf.read(filename)
        cf.set('DEFAULT', 'compute_driver', 'xenapi.XenAPIDriver')
        cf.set('DEFAULT', 'force_config_drive', 'always')
        cf.set('DEFAULT', 'novncproxy_base_url',
               'https://%s:6080/vnc_auto.html' % public_ip)
        cf.set('DEFAULT', 'vncserver_proxyclient_address', mgmt_ip)
        if not cf.has_section('xenserver'):
            cf.add_section('xenserver')
        cf.set('xenserver', 'connection_url', 'http://%s' % himn)
        cf.set('xenserver', 'connection_username', username)
        cf.set('xenserver', 'connection_password', password)
        cf.set('xenserver', 'vif_driver',
               'nova.virt.xenapi.vif.XenAPIOpenVswitchDriver')
        cf.set('xenserver', 'ovs_integration_bridge', INT_BRIDGE)
        cf.write(open(filename, 'w'))
    except Exception:
        reportError('Cannot set configurations to %s' % filename)
    info('%s created' % filename)


def route_to_compute(endpoints, himn_xs, himn_local, username, password):
    """Route storage/mgmt requests to compute nodes. """
    out = ssh(himn_xs, username, password, 'route', '-n')
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
                params = ['route', 'add', '-net', net, 'netmask',
                          mask, 'gw', himn_local]
                ssh(himn_xs, username, password, *params)
                sh = 'echo \'%s\' >> /etc/sysconfig/static-routes' \
                    % ' '.join(params)
                ssh(himn_xs, username, password, sh)
        else:
            info('%s network ip is missing' % endpoint_name)


def install_suppack(himn, username, password):
    """Install xapi driver supplemental pack. """
    # TODO(Johnhua): check if installed
    scp(himn, username, password, '/tmp/', XS_PLUGIN_ISO)
    ssh(
        himn, username, password, 'xe-install-supplemental-pack',
        '/tmp/%s' % XS_PLUGIN_ISO, prompt='Y\n')
    ssh(himn, username, password, 'rm', '/tmp/%s' % XS_PLUGIN_ISO)


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
    execute('service', 'iptables-persistent', 'save')


def forward_port(eth_in, eth_out, target_host, target_port):
    """Forward packets from eth_in to eth_out on target_host:target_port. """
    execute('iptables', '-t', 'nat', '-A', 'PREROUTING',
            '-i', eth_in, '-p', 'tcp', '--dport', target_port,
            '-j', 'DNAT', '--to', target_host)
    execute('iptables', '-A', 'FORWARD',
            '-i', eth_out, '-o', eth_in,
            '-m', 'state', '--state', 'RELATED,ESTABLISHED',
            '-j', 'ACCEPT')
    execute('iptables', '-A', 'FORWARD',
            '-i', eth_in, '-o', eth_out,
            '-j', 'ACCEPT')

    execute('iptables', '-t', 'filter', '-S', 'FORWARD')
    execute('iptables', '-t', 'nat', '-S', 'POSTROUTING')
    execute('service', 'iptables-persistent', 'save')


def install_logrotate_script(himn, username, password):
    "Install console logrotate script"
    scp(himn, username, password, '/root/', 'rotate_xen_guest_logs.sh')
    ssh(himn, username, password, 'mkdir -p /var/log/xen/guest')
    ssh(himn, username, password, '''crontab - << CRONTAB
* * * * * /root/rotate_xen_guest_logs.sh
CRONTAB''')


def modify_neutron_rootwrap_conf(himn, username, password):
    """Set xenapi configurations"""
    filename = '/etc/neutron/rootwrap.conf'
    cf = ConfigParser.ConfigParser()
    try:
        cf.read(filename)
        cf.set('xenapi', 'xenapi_connection_url', 'http://%s' % himn)
        cf.set('xenapi', 'xenapi_connection_username', username)
        cf.set('xenapi', 'xenapi_connection_password', password)
        cf.write(open(filename, 'w'))
    except Exception:
        reportError("Fail to modify file %s", filename)
    info('Modify file %s successfully', filename)


def modify_neutron_ovs_agent_conf(int_br, br_mappings):
    filename = '/etc/neutron/plugins/ml2/ml2_conf.ini'
    cf = ConfigParser.ConfigParser()
    try:
        cf.read(filename)
        cf.set('agent', 'root_helper',
               'neutron-rootwrap-xen-dom0 /etc/neutron/rootwrap.conf')
        cf.set('agent', 'root_helper_daemon', '')
        cf.set('agent', 'minimize_polling', False)
        cf.set('ovs', 'integration_bridge', int_br)
        cf.set('ovs', 'bridge_mappings', br_mappings)
        cf.write(open(filename, 'w'))
    except Exception:
        reportError("Fail to modify %s", filename)
    info('Modify %s successfully', filename)


def find_bridge_mappings(astute, himn, username, password):
    # find out bridge which is used for private network
    values = astute['network_scheme']['transformations']
    for item in values:
        if item['action'] == 'add-port' and item['bridge'] == 'br-aux':
            ethX = item['name']
            break
    # find the ethX mac in /sys/class/net/ethX/address
    fo = open('/sys/class/net/%s/address' % ethX, 'r')
    mac = fo.readline()
    fo.close()
    network_uuid = ssh(himn, username, password,
            'xe vif-list params=network-uuid minimal=true MAC=%s' % mac)
    bridge = ssh(himn, username, password,
            'xe network-list params=bridge minimal=true uuid=%s' % network_uuid)

    # find physical network name
    phynet_setting = astute['quantum_settings']['L2']['phys_nets']
    physnet = phynet_setting.keys()[0]
    return physnet + ':' + bridge


def restart_services(service_name):
    execute('stop', service_name)
    execute('start', service_name)


def enable_linux_bridge(himn, username, password):
    # When using OVS under XS6.5, it will prevent use of Linux bridge in
    # Dom0, but neutron-openvswitch-agent in compute node will use Linux
    # bridge, so we remove this restriction here
    # TODO(huanxie): will be executed multitimes, merge to install_suppack()?
    ssh(himn, username, password, 'rm -f /etc/modprobe.d/blacklist-bridge')


def replace_xenapi(himn, username, password):
    """replace folder xenapi to add patches which are not merged to upstream"""
    # TODO(huanxie): need to confirm the overall patchset list
    patchset_dir = sys.path[0]
    patchfile_list = ['%s/patchset/vif-plug.patch' % patchset_dir,
            '%s/patchset/nova-neutron-race-condition.patch' % patchset_dir,
            '%s/patchset/ovs-interim-bridge.patch' % patchset_dir,
            '%s/patchset/neutron-security-group.patch' % patchset_dir]
    for patch_file in patchfile_list:
        execute('patch', '-d', DIST_PACKAGES_DIR, '-p1', '-i', patch_file)


if __name__ == '__main__':
    install_xenapi_sdk()
    astute = get_astute(ASTUTE_PATH)
    if astute:
        username, password, install_xapi = get_options(astute, ASTUTE_SECTION)
        endpoints = get_endpoints(astute)
        himn_eth, himn_local = init_eth()

        public_ip = astute_get(
            astute, ('network_metadata', 'vips', 'public', 'ipaddr'))

        if username and password and endpoints and himn_local:
            check_hotfix_exists(HIMN_IP, username, password, 'XS65ESP1013')
            route_to_compute(
                endpoints, HIMN_IP, himn_local, username, password)
            if install_xapi:
                install_suppack(HIMN_IP, username, password)
            enable_linux_bridge(HIMN_IP, username, password)
            forward_from_himn(himn_eth)

            # port forwarding for novnc
            forward_port('br-mgmt', himn_eth, HIMN_IP, '80')

            create_novacompute_conf(HIMN_IP, username, password, public_ip)
            replace_xenapi(HIMN_IP, username, password)
            restart_services('nova-compute')

            install_logrotate_script(HIMN_IP, username, password)

            # neutron-l2-agent in compute node
            modify_neutron_rootwrap_conf(HIMN_IP, username, password)
            br_mappings = find_bridge_mappings(astute, HIMN_IP,
                                               username, password)
            modify_neutron_ovs_agent_conf(INT_BRIDGE, br_mappings)
            restart_services('neutron-plugin-openvswitch-agent')
