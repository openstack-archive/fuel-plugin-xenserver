#!/usr/bin/env python

import ConfigParser
from distutils.version import LooseVersion
import logging
import netifaces
import os
import re
from socket import inet_ntoa
from struct import pack
import sys
import utils
from utils import HIMN_IP


LOG_FILE = os.path.join(utils.LOG_ROOT, 'compute_post_deployment.log')
INT_BRIDGE = 'br-int'
XS_PLUGIN_ISO = 'xenapi-plugins-mitaka.iso'
DIST_PACKAGES_DIR = '/usr/lib/python2.7/dist-packages/'
CONNTRACK_ISO = 'conntrack-tools.iso'
CONNTRACK_CONF_SAMPLE =\
    '/usr/share/doc/conntrack-tools-1.4.2/doc/stats/conntrackd.conf'

if not os.path.exists(utils.LOG_ROOT):
    os.mkdir(utils.LOG_ROOT)

logging.basicConfig(filename=LOG_FILE,
                    level=logging.DEBUG)


def get_endpoints(astute):
    """Return the IP addresses of the storage/mgmt endpoints."""
    endpoints = astute['network_scheme']['endpoints']
    endpoints = dict([(
        k.replace('br-', ''),
        endpoints[k]['IP'][0]
    ) for k in endpoints])

    logging.info('storage network: {storage}'.format(**endpoints))
    logging.info('mgmt network: {mgmt}'.format(**endpoints))
    return endpoints


def install_xenapi_sdk():
    """Install XenAPI Python SDK"""
    utils.execute('cp', 'XenAPI.py', DIST_PACKAGES_DIR)


def create_novacompute_conf(himn, username, password, public_ip, services_ssl):
    """Fill nova-compute.conf with HIMN IP and root password. """
    mgmt_if = netifaces.ifaddresses('br-mgmt')
    if mgmt_if and mgmt_if.get(netifaces.AF_INET) \
            and mgmt_if.get(netifaces.AF_INET)[0]['addr']:
        mgmt_ip = mgmt_if.get(netifaces.AF_INET)[0]['addr']
    else:
        utils.reportError('Cannot get IP Address on Management Network')

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
        cf.set('xenserver', 'cache_images', 'none')
        with open(filename, 'w') as configfile:
            cf.write(configfile)
    except Exception:
        utils.reportError('Cannot set configurations to %s' % filename)
    logging.info('%s created' % filename)


def route_to_compute(endpoints, himn_xs, himn_local, username):
    """Route storage/mgmt requests to compute nodes. """

    def _net(ip):
        return '.'.join(ip.split('.')[:-1] + ['0'])

    def _mask(cidr):
        return inet_ntoa(pack('>I', 0xffffffff ^ (1 << 32 - int(cidr)) - 1))

    def _routed(net, mask, gw):
        return re.search(r'%s\s+%s\s+%s\s+' % (
            net.replace('.', r'\.'),
            gw.replace('.', r'\.'),
            mask
        ), out)

    out = utils.ssh(himn_xs, username, 'route', '-n')

    utils.ssh(himn_xs, username,
              ('printf "#!/bin/bash\nsleep 5\n" >'
               '/etc/udev/scripts/reroute.sh'))
    endpoint_names = ['storage', 'mgmt']
    for endpoint_name in endpoint_names:
        endpoint = endpoints.get(endpoint_name)
        if endpoint:
            ip, cidr = endpoint.split('/')
            net, mask = _net(ip), _mask(cidr)
            if not _routed(net, mask, himn_local):
                params = ['route', 'add', '-net', '"%s"' % net, 'netmask',
                          '"%s"' % mask, 'gw', himn_local]
                utils.ssh(himn_xs, username, *params)
            # Always add the route to the udev, even if it's currently active
            cmd = (
                "printf 'if !(/sbin/route -n | /bin/grep -q -F \"{net}\"); "
                "then\n"
                "/sbin/route add -net \"{net}\" netmask "
                "\"{mask}\" gw {himn_local};\n"
                "fi\n' >> /etc/udev/scripts/reroute.sh"
            )
            cmd = cmd.format(net=net, mask=mask, himn_local=himn_local)
            utils.ssh(himn_xs, username, cmd)
        else:
            logging.info('%s network ip is missing' % endpoint_name)
    utils.ssh(himn_xs, username, 'chmod +x /etc/udev/scripts/reroute.sh')
    utils.ssh(himn_xs, username,
              ('echo \'SUBSYSTEM=="net" ACTION=="add" '
               'KERNEL=="xenapi" RUN+="/etc/udev/scripts/reroute.sh"\' '
               '> /etc/udev/rules.d/90-reroute.rules'))


def install_suppack(himn, username, package):
    """Install xapi driver supplemental pack. """
    tmp = utils.ssh(himn, username, 'mktemp', '-d')
    utils.scp(himn, username, tmp, package)
    utils.ssh(himn, username, 'xe-install-supplemental-pack',
              tmp + '/' + package, prompt='Y\n')
    utils.ssh(himn, username, 'rm', tmp, '-rf')


def forward_from_himn(eth):
    """Forward packets from HIMN to storage/mgmt network. """
    utils.execute('sed', '-i', 's/#net.ipv4.ip_forward/net.ipv4.ip_forward/g',
                  '/etc/sysctl.conf')
    utils.execute('sysctl', '-p', '/etc/sysctl.conf')

    endpoint_names = ['br-storage', 'br-mgmt']
    for endpoint_name in endpoint_names:
        utils.execute('iptables', '-t', 'nat', '-A', 'POSTROUTING',
                      '-o', endpoint_name, '-j', 'MASQUERADE')
        utils.execute('iptables', '-A', 'FORWARD',
                      '-i', endpoint_name, '-o', eth,
                      '-m', 'state', '--state', 'RELATED,ESTABLISHED',
                      '-j', 'ACCEPT')
        utils.execute('iptables', '-A', 'FORWARD',
                      '-i', eth, '-o', endpoint_name,
                      '-j', 'ACCEPT')

    utils.execute('iptables', '-A', 'INPUT', '-i', eth, '-j', 'ACCEPT')
    utils.execute('iptables', '-t', 'filter', '-S', 'FORWARD')
    utils.execute('iptables', '-t', 'nat', '-S', 'POSTROUTING')
    utils.execute('service', 'iptables-persistent', 'save')


def forward_port(eth_in, eth_out, target_host, target_port):
    """Forward packets from eth_in to eth_out on target_host:target_port. """
    utils.execute('iptables', '-t', 'nat', '-A', 'PREROUTING',
                  '-i', eth_in, '-p', 'tcp', '--dport', target_port,
                  '-j', 'DNAT', '--to', target_host)
    utils.execute('iptables', '-A', 'FORWARD',
                  '-i', eth_out, '-o', eth_in,
                  '-m', 'state', '--state', 'RELATED,ESTABLISHED',
                  '-j', 'ACCEPT')
    utils.execute('iptables', '-A', 'FORWARD',
                  '-i', eth_in, '-o', eth_out,
                  '-j', 'ACCEPT')

    utils.execute('iptables', '-t', 'filter', '-S', 'FORWARD')
    utils.execute('iptables', '-t', 'nat', '-S', 'POSTROUTING')
    utils.execute('service', 'iptables-persistent', 'save')


def install_logrotate_script(himn, username):
    "Install console logrotate script"
    utils.scp(himn, username, '/root/', 'rotate_xen_guest_logs.sh')
    utils.ssh(himn, username, 'mkdir -p /var/log/xen/guest')
    utils.ssh(himn, username, '''crontab - << CRONTAB
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
        with open(filename, 'w') as configfile:
            cf.write(configfile)
    except Exception:
        utils.reportError("Fail to modify file %s", filename)
    logging.info('Modify file %s successfully', filename)


def modify_neutron_ovs_agent_conf(int_br, br_mappings):
    filename = '/etc/neutron/plugins/ml2/openvswitch_agent.ini'
    cf = ConfigParser.ConfigParser()
    try:
        cf.read(filename)
        cf.set('agent', 'root_helper',
               'neutron-rootwrap-xen-dom0 /etc/neutron/rootwrap.conf')
        cf.set('agent', 'root_helper_daemon', '')
        cf.set('agent', 'minimize_polling', False)
        cf.set('ovs', 'integration_bridge', int_br)
        cf.set('ovs', 'bridge_mappings', br_mappings)
        with open(filename, 'w') as configfile:
            cf.write(configfile)
    except Exception:
        utils.reportError("Fail to modify %s", filename)
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
        utils.reportError("Cannot find eth used for private network")

    # find the ethX mac in /sys/class/net/ethX/address
    with open('/sys/class/net/%s/address' % ethX, 'r') as fo:
        mac = fo.readline()
    network_uuid = utils.ssh(himn, username,
                             ('xe vif-list params=network-uuid '
                              'minimal=true MAC=%s') % mac)
    bridge = utils.ssh(himn, username,
                       ('xe network-param-get param-name=bridge '
                        'uuid=%s') % network_uuid)

    # find physical network name
    phynet_setting = astute['quantum_settings']['L2']['phys_nets']
    physnet = phynet_setting.keys()[0]
    return physnet + ':' + bridge


def restart_services(service_name):
    utils.execute('stop', service_name)
    utils.execute('start', service_name)


def enable_linux_bridge(himn, username):
    # When using OVS under XS6.5, it will prevent use of Linux bridge in
    # Dom0, but neutron-openvswitch-agent in compute node will use Linux
    # bridge, so we remove this restriction here
    utils.ssh(himn, username, 'rm -f /etc/modprobe.d/blacklist-bridge*')


def patch_ceilometer():
    """Add patches which are not merged to upstream

    Order of patches applied:
        ceilometer-poll-cpu-util.patch
        ceilometer-rates-always-zero.patch
        ceilometer-support-network-bytes.patch
    """
    patchset_dir = sys.path[0]
    patchfile_list = [
        '%s/patchset/ceilometer-poll-cpu-util.patch' % patchset_dir,
        '%s/patchset/ceilometer-rates-always-zero.patch' % patchset_dir,
        '%s/patchset/ceilometer-support-network-bytes.patch' % patchset_dir,
    ]
    for patch_file in patchfile_list:
        utils.patch(DIST_PACKAGES_DIR, patch_file)


def patch_compute_xenapi():
    """Add patches which are not merged to upstream

    Order of patches applied:
        support-disable-image-cache.patch
        speed-up-config-drive.patch
        ovs-interim-bridge.patch
        neutron-security-group.patch
    """
    patchset_dir = sys.path[0]
    patchfile_list = [
        '%s/patchset/support-disable-image-cache.patch' % patchset_dir,
        '%s/patchset/speed-up-config-drive.patch' % patchset_dir,
        '%s/patchset/ovs-interim-bridge.patch' % patchset_dir,
        '%s/patchset/neutron-security-group.patch' % patchset_dir]
    for patch_file in patchfile_list:
        utils.patch(DIST_PACKAGES_DIR, patch_file)


def patch_neutron_ovs_agent():
    """Apply neutron patch

    Add conntrack-tools patch to support conntrack in Dom0
    """
    patchset_dir = sys.path[0]
    patch_file = '%s/patchset/fix-xenapi-returncode.patch' % patchset_dir
    utils.patch('/usr/bin', patch_file)


def reconfig_multipath():
    """Ignore local disks for multipathd

    Change devnode rule from "^hd[a-z]" to "^(hd|xvd)[a-z]"
    """
    utils.execute('sed', '-i', r's/"\^hd\[a-z\]"/"^(hd|xvd)[a-z]"/',
                  '/etc/multipath.conf')
    utils.execute('service', 'multipath-tools', 'restart')


def check_and_setup_ceilometer(himn, username, password):
    """Set xenapi configuration for ceilometer service"""
    filename = '/etc/ceilometer/ceilometer.conf'
    if not os.path.exists(filename):
        utils.reportError("The file: %s doesn't exist" % filename)
        return

    patch_ceilometer()

    cf = ConfigParser.ConfigParser()
    try:
        cf.read(filename)
        cf.set('DEFAULT', 'hypervisor_inspector', 'xenapi')
        cf.set('xenapi', 'connection_url', 'http://%s' % himn)
        cf.set('xenapi', 'connection_username', username)
        cf.set('xenapi', 'connection_password', password)
        with open(filename, 'w') as configfile:
            cf.write(configfile)
        logging.info('Modify file %s successfully', filename)
    except Exception:
        utils.reportError("Fail to modify file %s", filename)
        return
    restart_services('ceilometer-polling')


def enable_conntrack_service(himn, username):
    xcp_ver = utils.ssh(himn, username,
                        ('xe host-param-get uuid=$(xe host-list --minimal) '
                         'param-name=software-version '
                         'param-key=platform_version'))
    if LooseVersion(xcp_ver) < LooseVersion('2.1.0'):
        # Only support conntrack-tools since XS7.0(XCP2.1.0) and above
        logging.info('No need to enable conntrack-tools with XCP %s' % xcp_ver)
        return

    conn_installed = utils.ssh(himn, username,
                               'find', '/usr/sbin', '-name', 'conntrackd')
    if not conn_installed:
        install_suppack(himn, username, CONNTRACK_ISO)
        # use conntrack statistic mode, so change conntrackd.conf
        utils.ssh(himn, username,
                  'mv',
                  '/etc/conntrackd/conntrackd.conf',
                  '/etc/conntrackd/conntrackd.conf.back')
        utils.ssh(himn, username,
                  'cp',
                  CONNTRACK_CONF_SAMPLE,
                  '/etc/conntrackd/conntrackd.conf')

    # Restart conntrackd service
    utils.ssh(himn, username, 'service', 'conntrackd', 'restart')


if __name__ == '__main__':
    install_xenapi_sdk()
    astute = utils.get_astute()
    if astute:
        username, password, install_xapi = utils.get_options(astute)
        endpoints = get_endpoints(astute)
        himn_eth, himn_local = utils.init_eth()

        public_ip = utils.astute_get(
            astute, ('network_metadata', 'vips', 'public', 'ipaddr'))

        services_ssl = utils.astute_get(
            astute, ('public_ssl', 'services'))

        if username and password and endpoints and himn_local:
            route_to_compute(endpoints, HIMN_IP, himn_local, username)
            if install_xapi:
                install_suppack(HIMN_IP, username, XS_PLUGIN_ISO)
            enable_linux_bridge(HIMN_IP, username)
            forward_from_himn(himn_eth)

            # port forwarding for novnc
            forward_port('br-mgmt', himn_eth, HIMN_IP, '80')

            create_novacompute_conf(HIMN_IP, username, password, public_ip,
                                    services_ssl)
            patch_compute_xenapi()
            restart_services('nova-compute')

            install_logrotate_script(HIMN_IP, username)

            # enable conntrackd service in Dom0
            enable_conntrack_service(HIMN_IP, username)

            # neutron-l2-agent in compute node
            modify_neutron_rootwrap_conf(HIMN_IP, username, password)
            br_mappings = find_bridge_mappings(astute, HIMN_IP, username)
            modify_neutron_ovs_agent_conf(INT_BRIDGE, br_mappings)
            patch_neutron_ovs_agent()
            restart_services('neutron-openvswitch-agent')

            reconfig_multipath()

            # Add xenapi specific setup for ceilometer if service is enabled.
            is_ceilometer_enabled = utils.astute_get(astute,
                                                     ('ceilometer', 'enabled'))
            if is_ceilometer_enabled:
                check_and_setup_ceilometer(HIMN_IP, username, password)
            else:
                logging.info('Skip ceilomter setup as this service is '
                             'disabled.')
