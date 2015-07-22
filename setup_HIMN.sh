#!/bin/sh


function add_himn {
	local vm_name
	vm_name="$1"

	local vm_uuid
	vm_uuid=$(xe vm-list name-label="$vm_name")

	local device_number
	device_number=$2

	local net_uuid
	net_uuid=`xe network-list bridge=xenapi minimal=true`

	local eth2_uuid
	eth2_uuid=$(xe vif-create network-uuid=$net_uuid vm-uuid=$vm_uuid device=$device_number)
	xe vif-plug uuid=$eth2_uuid

	#make eth2 visible
	xe network-param-remove param-name=other-config \
		param-key=is_guest_installer_network uuid=$net_uuid
}

VM_NAMES="$@"

for VM_NAME in $VM_NAMES
do
	add_himn "$VM_NAME" 2
done
