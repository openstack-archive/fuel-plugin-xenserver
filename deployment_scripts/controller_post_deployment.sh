#!/bin/bash

LOG_FILE="/tmp/controller_post_deployment.log"

function clear_images {
	for ID in $(glance image-list | awk 'NR>2{print $2}' | grep -v '^$');
	do
		glance image-delete $ID &>> $LOG_FILE
	done
}

function create_image {
	local image_name
	image_name="$1"

	local vm_mode
	vm_mode="$2"

	local image_url
	image_url="$3"

	if ! glance image-list --name "$image_name" --property vm_mode="$vm_mode" | grep -q "$image_name"; then
		local image_file
		image_file=$(mktemp)

		wget -q -O "$image_file" "$image_url"
		glance image-create \
			--name "$image_name" \
			--container-format ovf \
			--disk-format vhd \
			--property vm_mode="$vm_mode" \
			--is-public True \
			--file "$image_file" \
			&>> $LOG_FILE

		rm "$image_file"
	fi
}

source /root/openrc admin

create_image "TestVM" "xen" "http://ca.downloads.xensource.com/OpenStack/cirros-0.3.4-x86_64-disk.vhd.tgz"
create_image "F17-x86_64-cfntools" "hvm" "http://ca.downloads.xensource.com/OpenStack/F21-x86_64-cfntools.tgz"
glance image-list >> $LOG_FILE