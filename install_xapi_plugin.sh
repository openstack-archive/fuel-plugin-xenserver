#!/bin/bash

set -x

function install_xapi_plugin {
    local nova_url
    nova_url="$1"

    local nova_zipball
    nova_zipball=$(mktemp)

    local nova_sources
    nova_sources=$(mktemp -d)

    wget -qO "$nova_zipball" "$nova_url"
    unzip -q "$nova_zipball" -d "$nova_sources"
    cp $nova_sources/*/plugins/xenserver/xenapi/etc/xapi.d/plugins/* /etc/xapi.d/plugins/
    rm "$nova_zipball"
    rm -rf "$nova_sources"
}

install_xapi_plugin "https://codeload.github.com/openstack/nova/zip/2014.2.2"