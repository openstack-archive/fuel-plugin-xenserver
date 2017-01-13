#!/usr/bin/env python

import ConfigParser
from distutils.version import LooseVersion
import ipaddress
import netifaces
import os
import re
import shutil
from socket import inet_ntoa
import stat
from struct import pack
import utils
from utils import HIMN_IP


INT_BRIDGE = 'br-int'
MESH_BRIDGE = 'br-mesh'
XS_PLUGIN_ISO = 'xenapi-plugins-mitaka.iso'
CONNTRACK_CONF_SAMPLE =\
    '/usr/share/doc/conntrack-tools-1.4.2/doc/stats/conntrackd.conf'

utils.setup_logging('compute_post_deployment.log')
LOG = utils.LOG


def get_endpoints(astute):
    """Return the IP addresses of the storage/mgmt endpoints."""
    endpoints = astute['network_scheme']['endpoints']
    endpoints = dict([(
        k.replace('br-', ''),
        endpoints[k]['IP'][0]
    ) for k in endpoints])

    LOG.info('storage network: {storage}'.format(**endpoints))
    LOG.info('mgmt network: {mgmt}'.format(**endpoints))
    return endpoints


def install_xenapi_sdk():
    """Install XenAPI Python SDK"""
    utils.execute('cp', 'XenAPI.py', utils.DIST_PACKAGES_DIR)


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

        if not cf.has_section('vnc'):
            cf.add_section('vnc')
        scheme = "https" if services_ssl else "http"
        cf.set('vnc', 'novncproxy_base_url',
               '%s://%s:6080/vnc_auto.html' % (scheme, public_ip))
        cf.set('vnc', 'vncserver_proxyclient_address', mgmt_ip)

        if not cf.has_section('xenserver'):
            cf.add_section('xenserver')
        cf.set('xenserver', 'connection_url', 'http://%s' % himn)
        cf.set('xenserver', 'connection_username', username)
        cf.set('xenserver', 'connection_password', password)
        cf.set('xenserver', 'vif_driver',
               'nova.virt.xenapi.vif.XenAPIOpenVswitchDriver')
        cf.set('xenserver', 'ovs_integration_bridge', INT_BRIDGE)
        cf.set('xenserver', 'cache_images', 'all')
        with open(filename, 'w') as configfile:
            cf.write(configfile)
    except Exception:
        utils.reportError('Cannot set configurations to %s' % filename)
    LOG.info('%s created' % filename)


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
            LOG.info('%s network ip is missing' % endpoint_name)
    utils.ssh(himn_xs, username, 'chmod +x /etc/udev/scripts/reroute.sh')
    utils.ssh(himn_xs, username,
              ('echo \'SUBSYSTEM=="net" ACTION=="add" '
               'KERNEL=="xenapi" RUN+="/etc/udev/scripts/reroute.sh"\' '
               '> /etc/udev/rules.d/90-reroute.rules'))


def parse_uuid(output):
    uuid = None
    index = output.strip().find('uuid:')
    if index >= 0:
        start = index + len('uuid:')
        uuid = output[start:].strip()
    return uuid


def install_suppack(himn, username, package, xcp_version):
    """Install xapi driver supplemental pack. """
    tmp = utils.ssh(himn, username, 'mktemp', '-d')
    real_pack = "xcp_%s/%s" % (xcp_version, package)
    if not os.path.exists(real_pack):
        utils.reportError('Package folder %s not exist' % real_pack)
    utils.scp(himn, username, tmp, real_pack)
    if LooseVersion(xcp_version) < LooseVersion('2.2.0'):
        utils.ssh(himn, username, 'xe-install-supplemental-pack',
                  tmp + '/' + package, prompt='Y\n')
    else:
        errcode, uuid, errmsg = \
            utils.ssh_detailed(himn, username, 'xe', 'update-upload',
                               'file-name=' + tmp + '/' + package,
                               allowed_return_codes=[0, 1])
        if errcode == 0:
            utils.ssh(himn, username, 'xe', 'update-apply',
                      'uuid=' + uuid.strip())
        else:
            LOG.debug("Install supplemental pack failed, err: %s", errmsg)
            if "The uploaded update already exists" in errmsg:
                uuid = parse_uuid(errmsg)
                if uuid is None:
                    raise utils.ExecutionError(errmsg)
                # Check current update is applied already
                out = utils.ssh(himn, username, 'xe', 'update-list',
                                'uuid=' + uuid, '--minimal')
                # Apply this update if cannot find it with uuid
                if not out:
                    utils.ssh(himn, username, 'xe', 'update-apply',
                              'uuid=' + uuid)
    utils.ssh(himn, username, 'rm', tmp, '-rf')


def forward_from_himn(eth):
    """Forward packets from HIMN to storage/mgmt network. """
    # make change to be persistent
    utils.execute('sed', '-i',
                  's/.*net\.ipv4\.ip_forward.*=.*/net.ipv4.ip_forward=1/g',
                  '/etc/sysctl.conf')
    # make it to take effective now.
    utils.execute('sysctl', 'net.ipv4.ip_forward=1')

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
* * * * * /root/rotate_xen_guest_logs.sh >/dev/null 2>&1
CRONTAB''')


def install_image_cache_cleanup():
    tool_path = '/usr/bin/destroy_cached_images'
    tool_conf = '/etc/nova/nova-compute.conf'
    # install this tool.
    try:
        src_file = 'tools/destroy_cached_images.py'
        target_file = tool_path
        shutil.copy(src_file, target_file)
        os.chown(target_file, 0, 0)
        os.chmod(target_file, stat.S_IRWXU)
    except Exception:
        utils.reportError("Failed to install file %s" % target_file)

    # create a daily clean-up cron job
    cron_entry = '5 3 * * * {} --config-file={} >/dev/null 2>&1'.format(
                 tool_path,
                 tool_conf)
    user = 'root'
    utils.add_cron_job(user, cron_entry)
    LOG.info('Added crontab successfully: %s' % cron_entry)


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
    LOG.info('Modify file %s successfully', filename)


def modify_neutron_ovs_agent_conf(int_br, br_mappings=None, local_ip=None):
    filename = '/etc/neutron/plugins/ml2/openvswitch_agent.ini'
    cf = ConfigParser.ConfigParser()
    try:
        cf.read(filename)
        cf.set('agent', 'root_helper',
               'neutron-rootwrap-xen-dom0 /etc/neutron/rootwrap.conf')
        cf.set('agent', 'root_helper_daemon', '')
        cf.set('agent', 'minimize_polling', False)
        cf.set('ovs', 'integration_bridge', int_br)
        if br_mappings:
            cf.set('ovs', 'bridge_mappings', br_mappings)
        if local_ip:
            cf.set('ovs', 'local_ip', local_ip)
        with open(filename, 'w') as configfile:
            cf.write(configfile)
    except Exception:
        utils.reportError("Fail to modify %s", filename)
    LOG.info('Modify %s successfully', filename)


def get_network_ethX(bridge_name):
    # find out ethX in DomU which connect to private network
    # br-aux is the auxiliary bridge and in normal case there will be a patch
    # between br-prv and br-aux
    values = astute['network_scheme']['transformations']
    for item in values:
        if item['action'] == 'add-port' and item['bridge'] == bridge_name:
            return item['name']
    # If cannot find given bridge, the network topo should be public and
    # private connecting to the same network and the checkbox
    # "Assign public network to all nodes" is checked, we need to use br-ex
    # to find ethX in domU
    for item in values:
        if item['action'] == 'add-port' and item['bridge'] == 'br-ex':
            return item['name']


def find_dom0_bridge(himn, username, bridge_name):
    ethX = get_network_ethX(bridge_name)
    if not ethX:
        utils.reportError("Cannot find eth used for private network")
    ethX = ethX.split('.')[0]

    # find the ethX mac in /sys/class/net/ethX/address
    with open('/sys/class/net/%s/address' % ethX, 'r') as fo:
        mac = fo.readline()
    network_uuid = utils.ssh(himn, username,
                             ('xe vif-list params=network-uuid '
                              'minimal=true MAC=%s') % mac)
    bridge = utils.ssh(himn, username,
                       ('xe network-param-get param-name=bridge '
                        'uuid=%s') % network_uuid)
    return bridge


def find_bridge_mappings(astute, himn, username):
    # find corresponding bridge in Dom0
    bridge = find_dom0_bridge(himn, username, 'br-aux')

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
        ceilometer-add-purge_inspection_cache.patch
    """
    patchfile_list = [
        'ceilometer-poll-cpu-util.patch',
        'ceilometer-rates-always-zero.patch',
        'ceilometer-support-network-bytes.patch',
        'ceilometer-add-purge_inspection_cache.patch',
    ]
    for patch_file in patchfile_list:
        utils.patch(utils.DIST_PACKAGES_DIR, patch_file, 1)


def patch_compute_xenapi():
    """Add patches which are not merged to upstream

    Order of patches applied:
        support-disable-image-cache.patch
        speed-up-config-drive.patch
        ovs-interim-bridge.patch
        neutron-security-group.patch
        live-migration-iscsi.patch
        support-vif-hotplug.patch
        fix-rescue-vm.patch
        live-migration-vifmapping.patch
    """
    patchfile_list = [
        # Change-Id: I5ebff2c1f7534b06233a4d41d7f5f2e5e3b60b5a
        'support-disable-image-cache.patch',
        # Change-Id: I359e17d6d5838f4028df0bd47e4825de420eb383
        'speed-up-config-drive.patch',
        # Change-Id: I0cfc0284e1fcd1a6169d31a7ad410716037e5cc2
        'ovs-interim-bridge.patch',
        # Change-Id: Id9b39aa86558a9f7099caedabd2d517bf8ad3d68
        'neutron-security-group.patch',
        # Change-Id: I88d1d384ab7587c428e517d184258bb517dfb4ab
        'live-migration-iscsi.patch',
        # Change-Id: I22f3fe52d07100592015007653c7f8c47c25d22c
        'support-vif-hotplug.patch',
        # Change-Id: I32c66733330bc9877caea7e2a2290c02b3906708
        'fix-rescue-vm.patch',
        # Change-Id: If0fb5d764011521916fbbe15224f524a220052f3
        'live-migration-vifmapping.patch',
        # TODO(huanxie): below patch isn't merged into upstream yet,
        # it only affects XS7.1 and later
        # Change-Id: I31850b25e2f32eb65a00fbb824b08646c9ed340a
        'assert_can_migrated.patch',
    ]
    for patch_file in patchfile_list:
        utils.patch(utils.DIST_PACKAGES_DIR, patch_file, 1)


def patch_neutron_ovs_agent():
    """Apply neutron patch

    Add conntrack-tools patch to support conntrack in Dom0
    """
    utils.patch('/usr/bin', 'fix-xenapi-returncode.patch', 2)


def reconfig_multipath():
    """Ignore local disks for multipathd

    Change devnode rule from "^hd[a-z]" to "^(hd|xvd)[a-z]"
    """
    multipath_conf = '/etc/multipath.conf'
    if os.path.exists(multipath_conf):
        utils.execute('sed', '-i', r's/"\^hd\[a-z\]"/"^(hd|xvd)[a-z]"/',
                      multipath_conf)
    else:
        with open(multipath_conf, "w") as f:
            f.write('# Generated by %s:\n' % utils.PLUGIN_NAME)
            f.write('blacklist {\ndevnode "^(hd|xvd)[a-z]"\n}')
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
        LOG.info('Modify file %s successfully', filename)
    except Exception:
        utils.reportError("Fail to modify file %s", filename)
        return
    restart_services('ceilometer-polling')


def enable_conntrack_service(himn, username, xcp_version):
    if LooseVersion(xcp_version) < LooseVersion('2.1.0'):
        # Only support conntrack-tools since XS7.0(XCP2.1.0) and above
        LOG.info('No need to enable conntrack-tools with XCP %s' % xcp_version)
        return

    # use conntrack statistic mode, so change conntrackd.conf
    if not os.path.exists('/etc/conntrackd/conntrackd.conf.back'):
        utils.ssh(himn, username,
                  'mv',
                  '/etc/conntrackd/conntrackd.conf',
                  '/etc/conntrackd/conntrackd.conf.back')
        utils.ssh(himn, username,
                  'cp',
                  CONNTRACK_CONF_SAMPLE,
                  '/etc/conntrackd/conntrackd.conf')

    # Rotate log file for conntrack
    utils.scp(himn, username,
              '/etc/logrotate.d', 'etc/logrotate.d/conntrackd')

    # Restart conntrackd service
    utils.ssh(himn, username, 'service', 'conntrackd', 'restart')


def get_xcp_version(himn, username):
    xcp_ver = utils.ssh(himn, username,
                        ('xe host-param-get uuid=$(xe host-list --minimal) '
                         'param-name=software-version '
                         'param-key=platform_version'))
    return xcp_ver


def configure_dom0_iptables(himn, username):
    xs_chain = 'XenServer-Neutron-INPUT'

    # Check XenServer specific chain, create if not exist
    exitcode, _, _ = utils.ssh_detailed(
        himn, username, 'iptables -t filter -L %s' % xs_chain,
        allowed_return_codes=[0, 1])
    if exitcode == 1:
        LOG.info('Create iptables chain %s', xs_chain)
        utils.ssh(himn, username, 'iptables -t filter --new %s' % xs_chain)
        utils.ssh(himn, username,
                  'iptables -t filter -I INPUT -j %s' % xs_chain)

    # Check XenServer rule for ovs native mode, create if not exist
    exitcode, _, _ = utils.ssh_detailed(
        himn, username,
        'iptables -t filter -C %s -p tcp -m tcp --dport 6640 -j ACCEPT'
        % xs_chain,
        allowed_return_codes=[0, 1])
    if exitcode == 1:
        LOG.info('Create iptables rule for neutron ovs native mode')
        utils.ssh(himn, username,
                  'iptables -t filter -I %s -p tcp --dport 6640 -j ACCEPT'
                  % xs_chain)

    # Check XenServer rule for vxlan, create if not exist
    exitcode, _, _ = utils.ssh_detailed(
        himn, username,
        'iptables -t filter -C %s -p udp -m multiport --dports 4789 -j ACCEPT'
        % xs_chain,
        allowed_return_codes=[0, 1])
    if exitcode == 1:
        LOG.info('Create iptables rule for neutron VxLAN')
        utils.ssh(himn, username,
                  'iptables -t filter -I %s -p udp -m multiport --dport 4789'
                  ' -j ACCEPT' % xs_chain)


def create_dom0_mesh_bridge(himn, username, dom0_bridge, mesh_info):
    ovs_port = 'mesh_ovs'
    linux_port = 'mesh_linux'
    exitcode, _, _ = utils.ssh_detailed(himn, username,
                                        'ip', 'link', 'show', MESH_BRIDGE,
                                        allowed_return_codes=[0, 1])
    # Create br-mesh and veth pair if not exist in Dom0
    if exitcode == 1:
        # create linux bridge br-mesh in dom0
        utils.ssh(himn, username, 'brctl', 'addbr', MESH_BRIDGE)
        utils.ssh(himn, username, 'brctl', 'setfd', MESH_BRIDGE, '0')
        utils.ssh(himn, username, 'brctl', 'stp', MESH_BRIDGE, 'off')

        # add veth pair to ovs bridge
        utils.ssh(himn, username,
                  'ip', 'link', 'add', ovs_port, 'type', 'veth',
                  'peer', 'name', linux_port)
        utils.ssh(himn, username, 'ip', 'link', 'set', ovs_port, 'up')
        utils.ssh(himn, username,
                  'ip', 'link', 'set', ovs_port, 'promisc', 'on')
        utils.ssh(himn, username, 'ip', 'link', 'set', linux_port, 'up')
        utils.ssh(himn, username,
                  'ip', 'link', 'set', linux_port, 'promisc', 'on')
        utils.ssh(himn, username, 'brctl', 'addif', MESH_BRIDGE, linux_port)

    # move br-mesh from compute node to dom0 and persist the configurations
    disable_local_mesh_bridge(MESH_BRIDGE)
    enable_dom0_mesh_bridge(himn, username, MESH_BRIDGE, mesh_info)

    # Create port in ovs
    utils.ssh(himn, username, 'ovs-vsctl', '--', '--if-exists', 'del-port',
              ovs_port, '--', 'add-port', dom0_bridge, ovs_port)
    if mesh_info['tag']:
        utils.ssh(himn, username, 'ovs-vsctl', '--', 'set', 'Port', ovs_port,
                  'tag=' + mesh_info['tag'])


def disable_local_mesh_bridge(bridge):
    utils.execute('ifconfig', bridge, '0.0.0.0')
    filename = '/etc/network/interfaces.d/ifcfg-%s' % bridge
    if os.path.isfile(filename):
        utils.execute('rm', '-f', filename)


def enable_dom0_mesh_bridge(himn, username, bridge, mesh_info):
    utils.ssh(himn, username, 'ip', 'addr', 'replace',
              mesh_info['ipaddr'] + '/' + mesh_info['netmask'], 'dev', bridge)
    filename = '/etc/sysconfig/network-scripts/ifcfg-%s' % bridge
    utils.ssh(himn, username,
              'cat > %(filename)s << IFACE_CONF_EOF\n'
              'DEVICE=%(bridge)s\n'
              'ONBOOT=yes\n'
              'NAME=%(bridge)s\n'
              'BOOTPROTO=static\n'
              'IPADDR=%(ip)s\n'
              'NETMASK=%(netmask)s\n'
              'NETWORK=%(network)s\n'
              'BROADCAST=%(broadcast)s\n'
              'IFACE_CONF_EOF\n' %
              {'filename': filename,
               'bridge': bridge,
               'ip': mesh_info['ipaddr'],
               'netmask': mesh_info['netmask'],
               'network': mesh_info['network'],
               'broadcast': mesh_info['broadcast']})


def get_mesh_info(astute, bridge):
    mesh_nets = astute['network_scheme']['endpoints'][bridge]['IP'][0]
    mesh_ip = mesh_nets.split('/')[0]
    ipv4_net = ipaddress.ip_network(unicode(mesh_nets), strict=False)
    mesh_broadcast = str(ipv4_net.broadcast_address)
    network_netmask = str(ipv4_net.with_netmask).split('/')
    mesh_netmask = network_netmask[1]
    mesh_network = network_netmask[0]
    mesh_eth = get_network_ethX(bridge)
    mesh_tag = None
    index = mesh_eth.index('.')
    if index > 0:
        mesh_tag = mesh_eth[index+1:]
    mesh_info = {'ipaddr': mesh_ip, 'network': mesh_network,
                 'netmask': mesh_netmask, 'broadcast': mesh_broadcast,
                 'tag': mesh_tag}
    return mesh_info


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
            xcp_version = get_xcp_version(HIMN_IP, username)
            if install_xapi:
                install_suppack(HIMN_IP, username, XS_PLUGIN_ISO, xcp_version)
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
            enable_conntrack_service(HIMN_IP, username, xcp_version)

            # configure iptables in Dom0 to support ovs native mode and VxLAN
            configure_dom0_iptables(HIMN_IP, username)

            # neutron-l2-agent in compute node
            modify_neutron_rootwrap_conf(HIMN_IP, username, password)
            l2_net_type = astute['quantum_settings']['predefined_networks'][
                'admin_internal_net']['L2']['network_type']
            br_mappings = None
            if l2_net_type == 'vlan':
                br_mappings = find_bridge_mappings(astute, HIMN_IP, username)
            ip = None
            if l2_net_type == 'tun':
                dom0_priv_bridge = find_dom0_bridge(HIMN_IP, username,
                                                    MESH_BRIDGE)
                mesh_info = get_mesh_info(astute, MESH_BRIDGE)
                create_dom0_mesh_bridge(HIMN_IP, username, dom0_priv_bridge,
                                        mesh_info)
            modify_neutron_ovs_agent_conf(INT_BRIDGE, br_mappings=br_mappings,
                                          local_ip=mesh_info['ipaddr'])
            patch_neutron_ovs_agent()
            restart_services('neutron-openvswitch-agent')

            reconfig_multipath()

            # Add xenapi specific setup for ceilometer if service is enabled.
            is_ceilometer_enabled = utils.astute_get(astute,
                                                     ('ceilometer', 'enabled'))
            if is_ceilometer_enabled:
                check_and_setup_ceilometer(HIMN_IP, username, password)
            else:
                LOG.info('Skip ceilomter setup as this service is '
                         'disabled.')

            install_image_cache_cleanup()
