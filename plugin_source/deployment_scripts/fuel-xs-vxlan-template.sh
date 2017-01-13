#!/bin/bash

dom0_bridge=DOM0_BRIDGE
mesh_ip=MESH_IP
mesh_netmask=MESH_NETMASK
mesh_broadcast=MESH_BROADCAST
create_tag=CREATE_TAG
tag=TAG

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
    if [ "$create_tag" == "1" ]; then
        ovs-vsctl -- set Port mesh_ovs tag=$tag
    fi
fi