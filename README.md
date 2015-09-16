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


Install prerequisites
---------------------

	apt-get install createrepo rpm dpkg-dev python-pip sshpass -y \
	|| yum install createrepo rpm rpm-build dpkg-devel python-pip sshpass -y


Clone Citrix FPB
------------------

XenServer Fuel Plugin uses a forked Fuel Plugin Builder (FPB) to deploy a new OpenStack release as well as the fuel plugin part itself.

	git clone https://github.com/citrix-openstack/fuel-plugins.git
	sudo pip install fuel-plugins/fuel_plugin_builder/



Build and Check
---------------

	git clone https://github.com/citrix-openstack/xenserver-fuel-plugin.git
	fpb --check xenserver-fuel-plugin
	fpb --build xenserver-fuel-plugin
