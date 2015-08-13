xenserver-fuel-plugin
============

Prerequisites
-------------

	[user@local ~]# apt-get install createrepo rpm dpkg-dev python-pip sshpass -y \
	|| yum install createrepo rpm rpm-build dpkg-devel python-pip sshpass -y

Environment Setup
-----------------

	[user@local ~]# git clone https://github.com/citrix-openstack/fuel-plugins.git
	[user@local ~]# sudo pip install fuel-plugins/fuel_plugin_builder/
	[user@local ~]# git clone https://github.com/citrix-openstack/xenserver-fuel-plugin.git


Build
-----

	[user@local ~]# fpb --check xenserver-fuel-plugin
	[user@local ~]# fpb --build xenserver-fuel-plugin


Installation
------------

	[user@local ~]# scp xenserver-fuel-plugin/xenserver-fuel-plugin*.noarch.rpm root@Fuel_Master_IP:/tmp
	
	[root@fuel tmp]# fuel plugins --install xenserver-fuel-plugin*.noarch.rpm
