xenserver-fuel-plugin
============

Prerequisites
-------------

	apt-get install createrepo rpm dpkg-dev python-pip sshpass -y || yum install createrepo rpm rpm-build dpkg-devel python-pip sshpass -y
	pip install fuel-plugin-builder

Environment Setup
-----------------

	git clone https://github.com/citrix-openstack/xenserver-fuel-plugin.git
	cd xenserver-fuel-plugin
	cp localrc.sample localrc && vi localrc #configure your local environment

Deployment
----------

	./deploy.sh release
	./deploy.sh plugin
	./deploy.sh #both
