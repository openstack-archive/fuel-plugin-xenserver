#!/bin/bash

function setup_himn {
	echo 'auto eth2
iface eth2 inet dhcp' \
	> /etc/network/interfaces.d/ifcfg-eth2
}

function install_xen_tools {
	local xen_tools_url
	xen_tools_url="$1"

	local xen_tools_file
	xen_tools_file=$(mktemp)

	wget -qO "$xen_tools_file" "$xen_tools_url"
	dpkg -i "$xen_tools_file"
	rm "$xen_tools_file"
}

function install_xapi_plugin {
	local nova_url
	nova_url="$1"

	local nova_zipball
	nova_zipball=$(mktemp)

	local nova_sources
	nova_sources=$(mktemp -d)

	wget -qO "$nova_zipball" "$nova_url"
	unzip "$nova_zipball" -d "$nova_sources"
	cp $nova_sources/plugins/xenserver/xenapi/etc/xapi.d/plugins/* /etc/xapi.d/plugins/
	rm "$nova_zipball"
	rm -rf "$nova_sources"
}

function install_xenapi_sdk {
	local xenapi_url
	xenapi_url="$1"

	local xenapi_zipball
	xenapi_zipball=$(mktemp)

	local xenapi_sources
	xenapi_sources=$(mktemp -d)

	wget -qO "$xenapi_zipball" "$xenapi_url"
	unzip "$xenapi_zipball" -d "$xenapi_sources"
	tar -xf $xenapi_sources/*.tar
	cp $xenapi_sources/XenAPI-*/XenAPI.py /usr/lib/python2.7/dist­packages/
	rm "$xenapi_zipball"
	rm -rf "$xenapi_sources"
}

function create_nova­compute_conf {
	local username
	username="$1"

	local password
	password="$2"

	echo '[DEFAULT]
compute_driver=xenapi.XenAPIDriver
[xenserver]
connection_url=http://10.219.10.22 
connection_username=$username
connection_password=$password' \
	> /etc/nova/nova­-compute.conf
}

setup_himn
install_xen_tools "http://xen-tools.org/software/xen-tools/xen-tools_4.5-1_all.deb"
install_xapi_plugin "https://codeload.github.com/openstack/nova/zip/2014.2.2"
install_xenapi_sdk "https://pypi.python.org/packages/source/X/XenAPI/XenAPI-1.2.tar.gz"
create_nova­compute_conf "$username_text" "$password_text" 