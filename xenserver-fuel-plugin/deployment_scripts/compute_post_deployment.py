#!/usr/bin/env python

import os
import logging
from logging import debug, info, warning
import yaml
from subprocess import call
from shutil import rmtree
from tempfile import mkstemp, mkdtemp

LOG_FILE = '/var/log/compute_post_deployment.log'
logging.basicConfig(filename=LOG_FILE,level=logging.DEBUG)

def init_eth(dev_no):
	fname = '/etc/network/interfaces.d/ifcfg-eth%d' % (dev_no)
	s = \
"""auto eth2
iface eth2 inet dhcp
"""
	with open(fname, 'w') as f:
		f.write(s)
	info('%s created' % fname)

def install_xen_tools():
	#TODO
	'''
	local xen_tools_url
	xen_tools_url="$1"

	local xen_tools_file
	xen_tools_file=$(mktemp)

	wget -qO "$xen_tools_file" "$xen_tools_url"
	dpkg -i "$xen_tools_file"
	rm "$xen_tools_file"
	'''

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

def create_novacompute_conf(fuel_plugin_name='xenserver-fuel-plugin'):
	astute_path = '/etc/astute.yaml'
	if not os.path.exists(astute_path):
		warning('%s not found' % astute_path)
		return

	astute = yaml.load(open(astute_path))
	if not fuel_plugin_name in astute:
		warning('%s not found in %s' % (fuel_plugin_name, astute_path))
		return

	env = astute[fuel_plugin_name]
	info('username: {username_text}'.format(**env))
	info('password: {password_text}'.format(**env))

	template = \
"""[DEFAULT]
compute_driver=xenapi.XenAPIDriver
[xenserver]
connection_url=http://10.219.10.22
connection_username={username_text}
connection_password={password_text}
"""
	s = template.format(**env)
	with open('/etc/nova/nova-compute.conf','w') as f:
		f.write(s)

if __name__ == '__main__':
	init_eth(2)
	#install_xen_tools "http://xen-tools.org/software/xen-tools/xen-tools_4.5-1_all.deb"
	install_xenapi_sdk('https://pypi.python.org/packages/source/X/XenAPI/XenAPI-1.2.tar.gz')
	create_novacompute_conf('xenserver-fuel-plugin')