XenServer Fuel Plugin
=====================

Intro
=====

XenServer Fuel Plugin will help to deploy Mirantis OpenStack over XenServer hosts and make sure they work as xenapi rather than qemu.


Usage
=====

Please look at the [install guide](doc/content/installation.rst)
and [user guide](doc/content/user-guide.rst).


How to build plugin
===================

	pip install fuel-plugin-builder
	git clone https://git.openstack.org/openstack/fuel-plugin-xenserver
	fpb --check fuel-plugin-xenserver
	fpb --build fuel-plugin-xenserver
