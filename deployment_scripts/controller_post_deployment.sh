#!/bin/bash

LOG_ROOT="/var/log/fuel-plugin-xenserver/"
mkdir -p $LOG_ROOT
LOG_FILE=$LOG_ROOT"controller_post_deployment.log"

function delete_image {
	local image_name
	image_name="$1"
	image_id=$(glance image-list | grep "$image_name" | awk -F "|" '{print $2}' | grep -v '^$')
	glance image-delete $image_id &>> $LOG_FILE
}


function create_image {
	local image_name
	image_name="$1"

	local vm_mode
	vm_mode="$2"

	local image_file
	image_file="$3"

	if ! glance image-list | grep -q "$image_name"; then
		glance image-create \
			--name "$image_name" \
			--container-format ovf \
			--disk-format vhd \
			--property vm_mode="$vm_mode" \
			--visibility public \
			--file "$image_file" \
			&>> $LOG_FILE
	fi
}

function mod_novnc {
	local public_ip
	public_ip=$(python - <<EOF
import sys
import yaml
astute=yaml.load(open('/etc/astute.yaml'))
print astute['network_metadata']['vips']['public']['ipaddr']
EOF
)
	cat > /etc/nova/nova-compute.conf <<EOF
[DEFAULT]
novncproxy_host=0.0.0.0
novncproxy_base_url=http://$public_ip:6080/vnc_auto.html
EOF
	service nova-novncproxy restart
	service nova-consoleauth restart
}

source /root/openrc admin

echo "Before image replacement"
glance image-list >> $LOG_FILE

delete_image "TestVM"
create_image "TestVM" "xen" cirros-0.3.4-x86_64-disk.vhd.tgz

echo "After image replacement"
glance image-list >> $LOG_FILE

mod_novnc
