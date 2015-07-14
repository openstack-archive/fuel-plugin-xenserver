xenserver-fuel-plugin
============

Prerequisites
-------------

	apt-get install createrepo rpm dpkg-dev python-pip -y || yum install createrepo rpm rpm-build dpkg-devel python-pip -y
	pip install fuel-plugin-builder

Environment Setup
-----------------

	git clone https://github.com/citrix-openstack/xenserver-fuel-plugin.git
	cd xenserver-fuel-plugin
	cp localrc.sample localrc
	vi localrc #configure your local environment
	source localrc

Deployment
----------

	fpb --build .
	scp xenserver-fuel-plugin-$BUILD_VERSION.noarch.rpm root@$FUELMASTER:$PLUGIN_PATH
	ssh root@$FUELMASTER fuel plugins --install $PLUGIN_PATH/xenserver-fuel-plugin-$BUILD_VERSION.noarch.rpm
	#or
	ssh root@$FUELMASTER fuel plugins --update $PLUGIN_PATH/xenserver-fuel-plugin-$BUILD_VERSION.noarch.rpm
	ssh root@$FUELMASTER fuel plugins --list

Check out on Fuel Web UI
------------------------

	Open Fuel Web UI, go the Setting Tab of a new/existing Environment.

	You have to enable the plugin(check on the checkbox) before use it.

