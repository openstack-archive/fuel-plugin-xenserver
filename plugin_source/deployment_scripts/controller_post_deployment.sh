#!/bin/bash -eu

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
		glance image-delete $image_id 2>&1 &>> $LOG_FILE
	fi

	echo "Create image $image_name" >> $LOG_FILE
	glance image-create \
		--name "$image_name" \
		--container-format ovf \
		--disk-format vhd \
		--property vm_mode="$vm_mode" \
		--visibility public \
		--file "$image_file" \
		2>&1 &>> $LOG_FILE
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

function wait_ocf_resource_started {
    # wait upto $TIMEOUT seconds until all ocf resources are started
    TIMEOUT=300
    INTERVAL=10
    remain_time=$TIMEOUT
    while [ ${remain_time} -gt 0 ]; do
        if pcs resource show | grep ocf::fuel | grep -v Started >> $LOG_FILE; then
            echo "$(date): wait for resources to start." >> $LOG_FILE
            sleep $INTERVAL
            remain_time=$((remain_time - $INTERVAL))
        else
            return 0
        fi
    done
    echo "Error:  $(date): timeout for waiting resources to start." >> $LOG_FILE
    echo "Error: $(date): timeout for waiting resources to start." >&2
    exit 1
}

function mod_ceilometer {
    # modify ceilometer configuration per need.
    if pcs resource show p_ceilometer-agent-central >/dev/null 2>&1; then
        # wait until all ocf resources are started, otherwise there is risk for race
        # condition: If run "pcs resource restart" while some resources are still in
        # restarting or initiating stage, it may result into failures for both.
        wait_ocf_resource_started

        # exclude network.services.* to avoid NotFound: 404 service not found error.
        sed  -i '/- "!storage.api.request"/a\            - "!network.services.*"' \
            /etc/ceilometer/pipeline.yaml>>$LOG_FILE 2>&1
        pcs resource restart  p_ceilometer-agent-central  >>$LOG_FILE 2>&1
    fi
}

source /root/openrc admin

echo "Before image replacement" >> $LOG_FILE
glance image-list 2>&1 >> $LOG_FILE

replace_test_image "TestVM" "xen" cirros-0.3.4-x86_64-disk.vhd.tgz

echo "After image replacement" >> $LOG_FILE
glance image-list 2>&1 >> $LOG_FILE

mod_novnc

mod_ceilometer
