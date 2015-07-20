#!/bin/sh


function add_interface {
	local vm_uuid
	vm_uuid="$1"

	local device_number
	device_number=$2

	local himn_uuid
	himn_uuid=`xe network-list bridge=xenapi minimal=true`

	xe vif-create network-uuid=$himn_uuid vm-uuid=$vm_uuid device=$device_number
}

vm_uuids="$@"

for vm_uuid in $vm_uuids
do
	eth2_uuid=$(add_interface "$vm_uuid" 2)
	xe vif-plug uuid=$eth2_uuid
done
