#!/bin/bash

LOG_ROOT="/var/log/@PLUGIN_NAME@/"
mkdir -p $LOG_ROOT
LOG_FILE=$LOG_ROOT"controller_post_deployment.log"

function replace_test_image {
	local image_name
	image_name="$1"

	local vm_mode
	vm_mode="$2"

	local image_file
	image_file="$3"

	image_id=$(glance image-list | grep "$image_name" | awk -F "|" '{print $2}' | grep -v '^$')

	if [[ -n "$image_id" ]]; then
		echo "Delete image $image_name" >> $LOG_FILE
		glance image-delete $image_id &>> $LOG_FILE
	fi

	echo "Create image $image_name" >> $LOG_FILE
	glance image-create \
		--name "$image_name" \
		--container-format ovf \
		--disk-format vhd \
		--property vm_mode="$vm_mode" \
		--visibility public \
		--file "$image_file" \
		&>> $LOG_FILE
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

function mod_ceilometer {
    # modify ceilometer configuration per need.
    if pcs resource show p_ceilometer-agent-central >/dev/null 2>&1; then
        # exclude network.services.* to avoid NotFound: 404 service not found error.
        sed  -i '/- "!storage.api.request"/a\            - "!network.services.*"' \
            /etc/ceilometer/pipeline.yaml>>$LOG_FILE 2>&1
        pcs resource restart  p_ceilometer-agent-central  >>$LOG_FILE 2>&1
    fi
}

source /root/openrc admin

echo "Before image replacement" >> $LOG_FILE
glance image-list >> $LOG_FILE

replace_test_image "TestVM" "xen" cirros-0.3.4-x86_64-disk.vhd.tgz

echo "After image replacement" >> $LOG_FILE
glance image-list >> $LOG_FILE

mod_novnc

mod_ceilometer
