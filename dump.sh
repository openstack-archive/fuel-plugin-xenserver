source localrc

ALL_MODELS="action_log capacity_log attributes cluster cluster_changes release "
ALL_MODELS+="node node_roles role node_attributes node_bond_interface node_group "
ALL_MODELS+="network_group networking_config nova_network_config notification task "
ALL_MODELS+="master_node_settings"
MODELS="$@"
MODELS=${MODELS:-$ALL_MODELS}


mkdir -p models
for model in $MODELS
do	
	(set -x ; ssh root@$FUELMASTER dockerctl shell nailgun manage.py dumpdata $model \
	 > models/$model.json)
done
