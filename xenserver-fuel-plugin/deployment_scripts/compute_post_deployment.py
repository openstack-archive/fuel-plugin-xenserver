#!/usr/bin/env python

import os
import logging
from logging import debug, info, warning
import yaml
from subprocess import call, Popen
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
	call(['dhclient', eth])
	call(['ifconfig', eth])
	fname = '/etc/network/interfaces.d/ifcfg-' + eth
	s = \
"""auto {eth}
iface {eth} inet dhcp
""".format(eth = eth)
	with open(fname, 'w') as f:
		f.write(s)
	info('%s created' % fname)
	call(['ifdown', eth])
	call(['ifup', eth])
	addr = netifaces.ifaddresses(eth).get(2)
	if addr is not None:
		ip = addr[0]['addr']
		info('%s : %s' % (eth, ip))
		return ip
	else:
		warning('%s not found' % access_section)

	return

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
	xs_ip = '.'.join(ip.split('.')[:-1] + ['1'])
	s = template % (xs_ip, access['username'], access['password'])
	with open('/etc/nova/nova-compute.conf','w') as f:
		f.write(s)
	info('nova-compute.conf created')

def restart_nova_services():
	call(['stop', 'nova-compute'])
	call(['start', 'nova-compute'])
	info('nova-compute restarted')
	call(['stop', 'nova-network'])
	call(['start', 'nova-network'])
	info('nova-network restarted')


def _ssh(himn_ip, access, cmd):
	ssh = Popen(['sshpass', '-p', access['password'], 'ssh', 
		'%s@%s' + (access['username'], himn_ip), cmd],
		stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	s = ssh.stdout.readlines()
	return s

def route_himn(astute_path, dev_no, access):
	if not os.path.exists(astute_path):
		warning('%s not found' % astute_path)
		return None

	eth = 'eth%s' % dev_no
	if not eth in netifaces.interfaces():
		warning('%s not found' % eth)
		return

	astute = yaml.load(open(astute_path))

	storage_ip = astute['network_scheme']['endpoints']['br-storage']['IP'][0]
	mgmt_ip = astute['network_scheme']['endpoints']['br-mgmt']['IP'][0]
	himn_ip = netifaces.ifaddresses(eth).get(2) 

	info('storage network ip : %s' % storage_ip)
	info('management network ip : %s' % mgmt_ip)
	info('HIMN ip : %s' % himn_ip)

	if storage_ip and mgmt_ip and himn_ip:
		info(_ssh('route add "%s" gw "%s"' % (storage_ip, himn_ip)))
		info(_ssh('route add "%s" gw "%s"' % (mgmt_ip, himn_ip)))
	else:
		warning('storage_ip, mgmt_ip or himn_ip is missing')

def install_suppack(himn_ip, access):
	#TODO: scp root@HIMN novaplugins.iso 
	info(_ssh('xe-install-supplemental-pack novaplugins.iso'))

def filter_himn(himn_ip):
	#TODO
	return

if __name__ == '__main__':
	install_xenapi_sdk(XENAPI_URL)
	access = get_access(ASTUTE_PATH, ACCESS_SECTION)
	himn_ip = init_eth(2)
	if access and himn_ip:
		#route_himn(ASTUTE_PATH, himn_ip, access)
		#install_suppack(himn_ip, access)
		#filter_himn(himn_ip)
		create_novacompute_conf(access, himn_ip)
		restart_nova_services()
