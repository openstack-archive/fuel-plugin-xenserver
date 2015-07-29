#!/bin/bash

set -x

guest_name="$1"
fuel_network="$2"
trunk_network="$3"
memory="$4"
disksize="$5"
tname="Other install media"	

vm_uuid=$(xe vm-install template="$tname" new-name-label="$guest_name")

localsr=$(xe pool-list params=default-SR minimal=true)
extra_vdi=$(xe vdi-create \
	name-label=xvdb \
	virtual-size="${disksize}GiB" \
	sr-uuid=$localsr type=user)
xe vbd-create vm-uuid=$vm_uuid vdi-uuid=$extra_vdi device=0
xe vm-cd-add vm=$vm_uuid device=1 cd-name="xs-tools.iso"

xe vm-memory-limits-set \
    static-min=${memory}MiB \
    static-max=${memory}MiB \
    dynamic-min=${memory}MiB \
    dynamic-max=${memory}MiB \
    uuid=$vm_uuid

xe vif-create network-uuid=$(xe network-list name-label="$fuel_network" --minimal) \
	vm-uuid=$vm_uuid device=0
xe vif-create network-uuid=$(xe network-list name-label="$trunk_network" --minimal) \
	vm-uuid=$vm_uuid device=1

xe vm-param-set uuid=$vm_uuid HVM-boot-params:order=nd

xe vm-start vm=$vm_uuid
