source localrc

ALL_NODES="$CONTROLLER_NODES,$COMPUTE_NODES,$STORAGE_NODES"

echo "Creating VMs"

for HOST_NODE in ${ALL_NODES//,/ }
do
	IFS=/ read -a _HOST_NODE <<< $HOST_NODE
	HOST=${_HOST_NODE[0]}
	NODE=${_HOST_NODE[1]}
	
	sshpass -p $XEN_PASSWORD ssh $XEN_ROOT@$HOST \
'set +x
guest_name="'$NODE'"
eth0="'$NODE_ETH0'"
eth1="'$NODE_ETH1'"
memory="'$NODE_MEMORY'"
disksize="'$NODE_DISKSIZE'"
tname="Other install media"	

vm_uuid=$(xe vm-install template="$tname" new-name-label="$guest_name")

localsr=$(xe pool-list params=default-SR minimal=true)
extra_vdi=$(xe vdi-create \
	name-label=xvdb \
	virtual-size="${disksize}GiB" \
	sr-uuid=$localsr type=user)
vbd_uuid=$(xe vbd-create vm-uuid=$vm_uuid vdi-uuid=$extra_vdi device=0)
xe vm-cd-add vm=$vm_uuid device=1 cd-name="xs-tools.iso"

xe vm-memory-limits-set \
    static-min=${memory}MiB \
    static-max=${memory}MiB \
    dynamic-min=${memory}MiB \
    dynamic-max=${memory}MiB \
    uuid=$vm_uuid

eth0_uuid=$(xe vif-create network-uuid=$(xe network-list name-label="$eth0" --minimal) vm-uuid=$vm_uuid device=0)
eth1_uuid=$(xe vif-create network-uuid=$(xe network-list name-label="$eth1" --minimal) vm-uuid=$vm_uuid device=1)

eth0_mac=$(xe vif-param-get uuid=$eth0_uuid param-name=MAC)

xe vm-param-set uuid=$vm_uuid HVM-boot-params:order=ndc

echo "Creating "'$NODE'" ($eth0_mac) on "'$HOST'""
'
done

./setup_HIMN.sh

echo "Booting VMs"
for HOST_NODE in ${ALL_NODES//,/ }
do
	IFS=/ read -a _HOST_NODE <<< $HOST_NODE
	HOST=${_HOST_NODE[0]}
	NODE=${_HOST_NODE[1]}
	sshpass -p $XEN_PASSWORD ssh $XEN_ROOT@$HOST \
'
guest_name="'$NODE'"
vm_uuid=$(xe vm-list name-label="$guest_name" --minimal)
xe vm-start vm=$vm_uuid
echo "'$NODE' booted"
'
done

if false; then
	sleep 60

	echo "Creating Cluster"
	sshpass -p $FUELMASTER_PASSWORD ssh $FUELMASTER_ROOT@$FUELMASTER \
'
guest_name="'$NODE'"

rel_id=$(fuel release | grep "XenServer" | cut -d " " -f1)
fuel env create --name "'$ENV_NAME'" --rel $rel 
env_id=$(fuel env | grep "'$ENV_NAME'" | cut -d " " -f1)
nodes=($(fuel node | grep True | cut -d " " -f1))
fuel --env $env_id node set --node ${nodes[0]} --role controller
fuel --env $env_id node set --node ${nodes[1]},${nodes[2]},${nodes[3]} --role compute
fuel --env $env_id node set --node ${nodes[4]} --role compute,cinder
'
fi