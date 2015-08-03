source localrc

echo "Setting up HIMN"

for HOST_NODE in ${COMPUTE_NODES//,/ }
do
	IFS=/ read -a _HOST_NODE <<< $HOST_NODE
	HOST=${_HOST_NODE[0]}
	NODE=${_HOST_NODE[1]}
	sshpass -p $XEN_PASSWORD ssh $XEN_ROOT@$HOST \
'set +x
vm_name="'$NODE'"
vm_uuid=$(xe vm-list name-label="$vm_name" --minimal)
if [ -n "$vm_uuid" ]; then
	device_number=2
	net_uuid=$(xe network-list bridge=xenapi minimal=true)
	vif_uuid=$(xe vif-list network-uuid="$net_uuid" vm-uuid="$vm_uuid" --minimal)
	if [ -z "$vif_uuid" ]; then
		
		eth2_uuid=$(xe vif-create network-uuid="$net_uuid" vm-uuid="$vm_uuid" device="$device_number")
		echo "$vm_name : HIMN created"
	fi
else
	echo "$vm_name does not exist"
fi
set +x'
done
