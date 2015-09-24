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

XenServer Fuel Plugin uses a forked Fuel Plugin Builder (FPB) to deploy a new OpenStack release during the installation of the plugin.
This is achieved by adding a post-install script option to the version 2.0 plugin.

	git clone https://git.openstack.org/openstack/fuel-plugin-xenserver
	sudo pip install fuel-plugins/fuel_plugin_builder/



Build and Check
---------------

	git clone https://git.openstack.org/openstack/fuel-plugin-xenserver.git
	fpb --check fuel-plugin-xenserver
	fpb --build fuel-plugin-xenserver
