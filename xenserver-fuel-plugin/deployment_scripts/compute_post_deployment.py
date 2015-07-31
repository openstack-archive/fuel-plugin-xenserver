#!/usr/bin/env python

import os
import logging
from logging import debug, info, warning
import yaml
from subprocess import call
from shutil import rmtree
from tempfile import mkstemp, mkdtemp
import netifaces

LOG_FILE = '/tmp/compute_post_deployment.log'
ASTUTE_PATH = '/etc/astute.yaml'
ACCESS_SECTION = 'xenserver-fuel-plugin'
XENAPI_URL = 'https://pypi.python.org/packages/source/X/XenAPI/XenAPI-1.2.tar.gz'

logging.basicConfig(filename=LOG_FILE,level=logging.DEBUG)

def get_access(astute_path, access_section):
	if not os.path.exists(astute_path):
		warning('%s not found' % astute_path)
		return None

	astute = yaml.load(open(astute_path))
	if not access_section in astute:
		warning('%s not found' % access_section)
		return None

	access = astute[access_section]
	info('username: {username}'.format(**access))
	info('password: {password}'.format(**access))
	return access

def init_eth(dev_no):
	eth = 'eth%s' % dev_no

	if not eth in netifaces.interfaces():
		warning('%s not found' % eth)
		return

	info('%s found' % eth)
	call('dhclient', eth)
	call('ifconfig', eth)
	fname = '/etc/network/interfaces.d/ifcfg-' + eth
	s = \
"""auto {eth}
iface {eth} inet dhcp
""".format(eth = eth)
	with open(fname, 'w') as f:
		f.write(s)
	info('%s created' % fname)
	call('ifdown', eth)
	call('ifup', eth)
	addr = netifaces.ifaddresses(eth).get(2)
	if addr is not None:
		ip = addr[0]['addr']
		info('%s : %s' % (eth, ip))
		return ip
	else:
		warning('%s not found' % access_section)

	return

def set_routing():
	eth_nova = astute['network_scheme']['roles']['novanetwork/fixed']
	storage_ip = astute['network_scheme']['endpoints']['br-storage']['IP']
	mgmt_ip = astute['network_scheme']['endpoints']['br-mgmt']['IP']

	nova_ip = netifaces.ifaddresses(eth_nova).get(2)

	call('route', 'add', storage_ip, 'gw', nova_ip)
	call('route', 'add', mgmt_ip, 'gw', nova_ip)

def install_xenapi_sdk(xenapi_url):
	xenapi_zipball = mkstemp()[1]
	xenapi_sources = mkdtemp()

	call(['wget', '-qO', xenapi_zipball, xenapi_url])
	info('%s downloaded' % (xenapi_url))

	call(['tar', '-zxf', xenapi_zipball, '-C', xenapi_sources])
	subdirs = os.listdir(xenapi_sources)
	if (len(subdirs) != 1) or (not subdirs[0].startswith('XenAPI')):
		warning('fail to extract %s' % xenapi_url)
		return
	info('%s extracted' % (subdirs[0]))

	src = os.path.join(xenapi_sources, subdirs[0], 'XenAPI.py')
	dest = '/usr/lib/python2.7/dist-packages'
	call(['cp', src, dest])
	info('XenAPI.py deployed')

	os.remove(xenapi_zipball)
	rmtree(xenapi_sources)

def create_novacompute_conf(access, ip):
	template = \
"""[DEFAULT]
compute_driver=xenapi.XenAPIDriver
[xenserver]
connection_url=http://%s
connection_username="%s"
connection_password="%s"
"""
	s = template.format(ip, access['username'],access['password'])
	with open('/etc/nova/nova-compute.conf','w') as f:
		f.write(s)
	info('nova-compute.conf created')

if __name__ == '__main__':
	install_xenapi_sdk(XENAPI_URL)
	access = get_access(ASTUTE_PATH, ACCESS_SECTION)
	ip = init_eth(2)
	if access is not None and ip is not None :
		create_novacompute_conf(access, ip)
