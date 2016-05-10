#!/usr/bin/env python

import ConfigParser
import logging
import netifaces
import os
import re
from socket import inet_ntoa
from struct import pack
import subprocess
import sys
import yaml


XS_RSA = '/root/.ssh/xs_rsa'
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

logging.basicConfig(filename=os.path.join(LOG_ROOT, LOG_FILE),
                    level=logging.DEBUG)


def reportError(err):
    logging.error(err)
    raise Exception(err)


def execute(*cmd, **kwargs):
    cmd = map(str, cmd)
    _env = kwargs.get('env')
    env_prefix = ''
    if _env:
        logging.info('env: %r' % _env)
        env_prefix = ''.join(['%s=%s ' % (k, _env[k]) for k in _env])

        env = dict(os.environ)
        env.update(_env)
    else:
        env = None
    logging.info(env_prefix + ' '.join(cmd))
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                 stderr=subprocess.PIPE, env=env)

    if 'prompt' in kwargs:
        prompt = kwargs.get('prompt')
        proc.stdout.flush()
        (out, err) = proc.communicate(prompt)
    else:
        out = proc.stdout.readlines()
        err = proc.stderr.readlines()
        (out, err) = map(' '.join, [out, err])

    # Both if/else need to deal with "\n" scenario
    (out, err) = (out.replace('\n', ''), err.replace('\n', ''))

    if out:
        logging.debug(out)
    if err:
        logging.error(out)

    if proc.returncode is not None and proc.returncode != 0:
        raise Exception(err)

    return out


def ssh(host, username, *cmd, **kwargs):
    cmd = map(str, cmd)

    return execute('ssh', '-i', XS_RSA,
                   '-o', 'StrictHostKeyChecking=no',
                   '%s@%s' % (username, host), *cmd,
                   prompt=kwargs.get('prompt'))


def scp(host, username, target_path, filename):
    return execute('scp', '-i', XS_RSA,
                   '-o', 'StrictHostKeyChecking=no', filename,
                   '%s@%s:%s' % (username, host, target_path))


def ssh_copy_id(host, username, password, ssh_priv_key):
    out = execute("apt-cache", "search", "sshpass")
    if out:
        execute("apt-get", "-y", "install", "sshpass")
    else:
        execute("dpkg", "-i", "sshpass_1.05-1_amd64.deb")

    if ssh_priv_key:
        with open(XS_RSA, 'w') as f:
            f.write(ssh_priv_key)
        ssh_pub_key = execute('ssh-keygen', '-y', '-f', XS_RSA)
        with open(XS_RSA + ".pub", 'w') as f:
            f.write(ssh_pub_key)
    else:
        if os.path.exists(XS_RSA):
            os.remove(XS_RSA)
        if os.path.exists(XS_RSA + ".pub"):
            os.remove(XS_RSA + ".pub")
        execute('ssh-keygen', '-f', XS_RSA, '-t', 'rsa', '-N', '')

    execute("sshpass", "-p", password, "ssh-copy-id",
            "-o", "StrictHostKeyChecking=no",
            "-i", XS_RSA, "%s@%s" % (username, host),
            env={"HOME": "/root"})


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
    logging.info('username: {username}'.format(**options))
    logging.info('password: {password}'.format(**options))
    logging.info('install_xapi: {install_xapi}'.format(**options))
    logging.info('ssh_priv_key: {ssh_priv_key}'.format(**options))
    return options['username'], options['password'], \
        options['install_xapi'], options['ssh_priv_key']


def get_endpoints(astute):
    """Return the IP addresses of the endpoints connected to
    storage/mgmt network.
    """
    endpoints = astute['network_scheme']['endpoints']
    endpoints = dict([(
        k.replace('br-', ''),
        endpoints[k]['IP'][0]
    ) for k in endpoints])

    logging.info('storage network: {storage}'.format(**endpoints))
    logging.info('mgmt network: {mgmt}'.format(**endpoints))
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
    logging.info('himn_mac: %s' % himn_mac)

    _mac = lambda eth: \
        netifaces.ifaddresses(eth).get(netifaces.AF_LINK)[0]['addr']
    eths = [eth for eth in netifaces.interfaces() if _mac(eth) == himn_mac]
    if len(eths) != 1:
        reportError('Cannot find eth matches himn_mac')

    eth = eths[0]
    logging.info('himn_eth: %s' % eth)

    ip = netifaces.ifaddresses(eth).get(netifaces.AF_INET)

    if not ip:
        execute('dhclient', eth)
        fname = '/etc/network/interfaces.d/ifcfg-' + eth
        s = ('auto {eth}\n'
             'iface {eth} inet dhcp\n'
             'post-up route del default dev {eth}').format(eth=eth)
        with open(fname, 'w') as f:
            f.write(s)
        logging.info('%s created' % fname)
        execute('ifdown', eth)
        execute('ifup', eth)
        ip = netifaces.ifaddresses(eth).get(netifaces.AF_INET)

    if ip:
        himn_local = ip[0]['addr']
        himn_xs = '.'.join(himn_local.split('.')[:-1] + ['1'])
        if HIMN_IP == himn_xs:
            logging.info('himn_local: %s' % himn_local)
            return eth, himn_local

    reportError('HIMN failed to get IP address from XenServer')


def check_host_compatibility(himn, username):
    hotfix = 'XS65ESP1013'
    installed = ssh(himn, username,
                    'xe patch-list name-label=%s --minimal' % hotfix)
    ver = ssh(himn, username,
              ('xe host-param-get uuid=$(xe host-list --minimal) '
               'param-name=software-version param-key=product_version_text'))

    if not installed and ver == "6.5":
        reportError(('Hotfix %s has not been installed '
                     'and product version is %s') % (hotfix, ver))


def install_xenapi_sdk():
    """Install XenAPI Python SDK"""
    execute('cp', 'XenAPI.py', DIST_PACKAGES_DIR)


def create_novacompute_conf(himn, username, password, public_ip, services_ssl):
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
        cf.set('DEFAULT', 'force_config_drive', 'True')
        scheme = "https" if services_ssl else "http"
        cf.set('DEFAULT', 'novncproxy_base_url',
               '%s://%s:6080/vnc_auto.html' % (scheme, public_ip))
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
    logging.info('%s created' % filename)


def route_to_compute(endpoints, himn_xs, himn_local, username):
    """Route storage/mgmt requests to compute nodes. """
    out = ssh(himn_xs, username, 'route', '-n')
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
                ssh(himn_xs, username, *params)
                sh = 'echo \'%s\' >> /etc/sysconfig/static-routes' \
                    % ' '.join(params)
                ssh(himn_xs, username, sh)
        else:
            logging.info('%s network ip is missing' % endpoint_name)


def install_suppack(himn, username):
    """Install xapi driver supplemental pack. """
    # TODO(Johnhua): check if installed
    scp(himn, username, '/tmp/', XS_PLUGIN_ISO)
    ssh(
        himn, username, 'xe-install-supplemental-pack',
        '/tmp/%s' % XS_PLUGIN_ISO, prompt='Y\n')
    ssh(himn, username, 'rm', '/tmp/%s' % XS_PLUGIN_ISO)


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

    execute('iptables', '-A', 'INPUT', '-i', eth, '-j', 'ACCEPT')
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


def install_logrotate_script(himn, username):
    "Install console logrotate script"
    scp(himn, username, '/root/', 'rotate_xen_guest_logs.sh')
    ssh(himn, username, 'mkdir -p /var/log/xen/guest')
    ssh(himn, username, '''crontab - << CRONTAB
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
    logging.info('Modify file %s successfully', filename)


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
    logging.info('Modify %s successfully', filename)


def get_private_network_ethX():
    # find out ethX in DomU which connect to private network
    # br-aux is the auxiliary bridge and in normal case there will be a patch
    # between br-prv and br-aux
    values = astute['network_scheme']['transformations']
    for item in values:
        if item['action'] == 'add-port' and item['bridge'] == 'br-aux':
            return item['name']
    # If cannot find br-aux, the network topo should be public and private
    # connect to the same network and "Assign public network to all nodes"
    # is checked, we need to use br-ex to find ethX in domU
    for item in values:
        if item['action'] == 'add-port' and item['bridge'] == 'br-ex':
            return item['name']

def find_bridge_mappings(astute, himn, username):
    ethX = get_private_network_ethX()
    if not ethX:
        reportError("Cannot find eth used for private network")

    # find the ethX mac in /sys/class/net/ethX/address
    fo = open('/sys/class/net/%s/address' % ethX, 'r')
    mac = fo.readline()
    fo.close()
    network_uuid = ssh(himn, username,
            'xe vif-list params=network-uuid minimal=true MAC=%s' % mac)
    bridge = ssh(himn, username,
            'xe network-param-get param-name=bridge uuid=%s' % network_uuid)

    # find physical network name
    phynet_setting = astute['quantum_settings']['L2']['phys_nets']
    physnet = phynet_setting.keys()[0]
    return physnet + ':' + bridge


def restart_services(service_name):
    execute('stop', service_name)
    execute('start', service_name)


def enable_linux_bridge(himn, username):
    # When using OVS under XS6.5, it will prevent use of Linux bridge in
    # Dom0, but neutron-openvswitch-agent in compute node will use Linux
    # bridge, so we remove this restriction here
    ssh(himn, username, 'rm -f /etc/modprobe.d/blacklist-bridge*')


def patch_compute_xenapi():
    """replace folder xenapi to add patches which are not merged to upstream"""
    # TODO(huanxie): need to confirm the overall patchset list
    patchset_dir = sys.path[0]
    patchfile_list = ['%s/patchset/vif-plug.patch' % patchset_dir,
            '%s/patchset/nova-neutron-race-condition.patch' % patchset_dir,
            '%s/patchset/ovs-interim-bridge.patch' % patchset_dir,
            '%s/patchset/neutron-security-group.patch' % patchset_dir,
            '%s/patchset/speed-up-writing-config-drive.patch' % patchset_dir]
    for patch_file in patchfile_list:
        execute('patch', '-d', DIST_PACKAGES_DIR, '-p1', '-i', patch_file)


def patch_neutron_ovs_agent():
    patchset_dir = sys.path[0]
    patch_file = '%s/patchset/neutron-rootwrap-xen-dom0.patch' % patchset_dir
    execute('patch', '-d', '/usr/', '-p1', '-i', patch_file)


def apply_sm_patch(himn, username):
    ver = ssh(himn, username,
              ('xe host-param-get uuid=$(xe host-list --minimal) '
               'param-name=software-version param-key=product_version_text'))
    if ver == "6.5":
        ssh(himn, username,
            "sed -i s/\\'phy\\'/\\'aio\\'/g /opt/xensource/sm/ISCSISR.py")


if __name__ == '__main__':
    logging.debug(os.environ)
    install_xenapi_sdk()
    astute = get_astute(ASTUTE_PATH)
    if astute:
        username, password, install_xapi, ssh_priv_key \
            = get_options(astute, ASTUTE_SECTION)
        endpoints = get_endpoints(astute)
        himn_eth, himn_local = init_eth()

        public_ip = astute_get(
            astute, ('network_metadata', 'vips', 'public', 'ipaddr'))

        services_ssl = astute_get(
            astute, ('public_ssl', 'services'))

        if username and password and endpoints and himn_local:
            ssh_copy_id(HIMN_IP, username, password, ssh_priv_key)
            check_host_compatibility(HIMN_IP, username)
            route_to_compute(endpoints, HIMN_IP, himn_local, username)
            if install_xapi:
                install_suppack(HIMN_IP, username)
            enable_linux_bridge(HIMN_IP, username)
            forward_from_himn(himn_eth)

            # port forwarding for novnc
            forward_port('br-mgmt', himn_eth, HIMN_IP, '80')

            # apply sm patch
            apply_sm_patch(HIMN_IP, username)

            create_novacompute_conf(HIMN_IP, username, password, public_ip, services_ssl)
            patch_compute_xenapi()
            restart_services('nova-compute')

            install_logrotate_script(HIMN_IP, username)

            # neutron-l2-agent in compute node
            modify_neutron_rootwrap_conf(HIMN_IP, username, password)
            br_mappings = find_bridge_mappings(astute, HIMN_IP, username)
            modify_neutron_ovs_agent_conf(INT_BRIDGE, br_mappings)
            patch_neutron_ovs_agent()
            restart_services('neutron-plugin-openvswitch-agent')
