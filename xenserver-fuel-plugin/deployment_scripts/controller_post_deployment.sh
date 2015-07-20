#!/bin/bash

function clear_images {
	for ID in $(glance image-list | awk 'NR>2{print $2}' | grep -v '^$'); 
	do
		glance image-delete $ID
	done
}

function create_image {
	local image_name
	image_name="$1"

	local vm_mode
	vm_mode="$2"

	local image_url
	image_url="$3"

	local image_file
	image_file=$(mktemp)

	wget -qO "$image_file" "$image_URL"
	glance image-create \
		--name "$image_name" \
		--container-format ovf \
		--disk-format vhd \
		--property vm_mode="$vm_mode" \
		--is-public True \
		--file "$image_file"

	rm "$image_file"
}

source /root/openrc

clear_images
create_image "TestVM" "xen" "http://ca.downloads.xensource.com/OpenStack/cirros-0.3.3-x86_64-disk.vhd"
create_image "F17-x86_64-cfntools" "hvm" "http://ca.downloads.xensource.com/OpenStack/F21-x86_64-cfntools.tgz"
