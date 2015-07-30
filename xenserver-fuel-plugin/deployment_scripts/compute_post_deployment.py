#!/usr/bin/env python

import os
import logging
from logging import debug, info, warning
import yaml
from subprocess import call
from shutil import rmtree
from tempfile import mkstemp, mkdtemp

LOG_FILE = '/tmp/compute_post_deployment.log'
ASTUTE_PATH = '/etc/astute.yaml'
ACCESS_SECTION = 'xenserver_access'
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
	info('username: {user}'.format(**access))
	info('password: {password}'.format(**access))
	return access

def install_xentools():
	os.system('mount /dev/cdrom /mnt && /mnt/Linux/install.sh')

def init_eth(dev_no):
	fname = '/etc/network/interfaces.d/ifcfg-eth%d' % (dev_no)
	s = \
"""auto eth2
iface eth2 inet dhcp
"""
	with open(fname, 'w') as f:
		f.write(s)
	info('%s created' % fname)

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

def create_novacompute_conf(access):
	template = \
"""[DEFAULT]
compute_driver=xenapi.XenAPIDriver
[xenserver]
connection_url=http://169.254.0.1
connection_username={user}
connection_password={password}
"""
	s = template.format(**access)
	with open('/etc/nova/nova-compute.conf','w') as f:
		f.write(s)
	info('nova-compute.conf created')

if __name__ == '__main__':
	init_eth(2)
	install_xenapi_sdk(XENAPI_URL)
	access = get_access(ASTUTE_PATH, ACCESS_SECTION)
	if access is not None:
		create_novacompute_conf(access)