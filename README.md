xenserver-fuel-plugin
============

Prerequisites
-------------

	[user@local tmp]# apt-get install createrepo rpm dpkg-dev python-pip sshpass -y || yum install createrepo rpm rpm-build dpkg-devel python-pip sshpass -y

Environment Setup
-----------------

	[user@local tmp]# git clone https://github.com/citrix-openstack/fuel-plugins.git
	[user@local tmp]# sudo pip install fuel-plugins/fuel_plugin_builder/
	[user@local tmp]# git clone https://github.com/citrix-openstack/xenserver-fuel-plugin.git


Deployment
----------

	[user@local tmp]# fpb --check xenserver-fuel-plugin && \
	fpb --build xenserver-fuel-plugin


Installation
------------

	[user@local tmp]# scp xenserver-fuel-plugin*.noarch.rpm root@<Fuel_Master_IP>:/tmp

	[root@fuel tmp]# fuel plugins --install xenserver-fuel-plugin*.noarch.rpm
