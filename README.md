XenServer Fuel Plugin
=====================

Intro
=====

XenServer Fuel Plugin will help to deploy Mirantis OpenStack over XenServer hosts and make sure they work as xenapi rather than qemu.


Usage
=====

Please run `make latexpdf` and look at the User Guide `fuel-plugin-xenserver.pdf` generated under `doc/build/latex/fuel-plugin-xenserver`.


How to build plugin
===================

	pip install git+https://github.com/openstack/fuel-plugins
	pip show fuel-plugin-builder | grep ^Version # make sure here >= 4.0.1

	git clone https://git.openstack.org/openstack/fuel-plugin-xenserver
	fpb --check fuel-plugin-xenserver
	fpb --build fuel-plugin-xenserver
