#!/bin/bash

OPERA=$1
COUNT=$#

function create_mesh_bridge {
    local dom0_bridge=$1
    local mesh_ip=$2
    local mesh_netmask=$3
    local mesh_broadcast=$4
    local tag=$5

    ip link show br-mesh
    exitcode=$?
    if [ "$exitcode" == "1" ]; then
        brctl addbr br-mesh
        brctl setfd br-mesh 0
        brctl stp br-mesh off
        ip link set br-mesh up
        ip link delete mesh_ovs
        ip link add mesh_ovs type veth peer name mesh_linux
        ip link set mesh_ovs up
        ip link set mesh_ovs promisc on
        ip link set mesh_linux up
        ip link set mesh_linux promisc on
        brctl addif br-mesh mesh_linux
        ovs-vsctl -- --if-exists del-port mesh_ovs -- add-port $dom0_bridge mesh_ovs
        ip addr add $mesh_ip/$mesh_netmask broadcast $mesh_broadcast dev br-mesh
        if [ -n "$tag" ]; then
            ovs-vsctl -- set Port mesh_ovs tag=$tag
        fi
    fi
}

function delete_mesh_bridge {
    ip link show br-mesh
    exitcode=$?
    if [ "$exitcode" == "0" ]; then
        ip link set br-mesh down
        ip link set mesh_ovs down
        ip link delete mesh_ovs
        ovs-vsctl -- --if-exist del-port mesh_ovs
        brctl delbr br-mesh
    fi
}


if [ "$OPERA" == "start" ]; then
    if [ $COUNT -lt 6 ]; then
        echo "The params are not enough, exit"
        exit 0
    fi

    dom0_bridge=$2
    mesh_ip=$3
    mesh_netmask=$4
    mesh_broadcast=$5
    tag=$6
    create_mesh_bridge $dom0_bridge $mesh_ip $mesh_netmask $mesh_broadcast $tag
elif [ "$OPERA" == "stop" ]; then
    delete_mesh_bridge
fi