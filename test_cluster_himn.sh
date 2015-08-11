source localrc


for HOST_NODE in ${COMPUTE_NODES//,/ }
do
	IFS=/ read -a _HOST_NODE <<< $HOST_NODE
	HOST=${_HOST_NODE[0]}
	NODE=${_HOST_NODE[1]}
	
	eth2=$(sshpass -p $XEN_PASSWORD ssh $XEN_ROOT@$HOST \
'xe vm-list name-label="'$NODE'" params=networks --minimal | grep -o -P "(?<=0\/ip\:\s)(\d+\.\d+\.\d+\.\d+)"')
	echo $HOST $NODE $eth2

	sshpass -p $XEN_PASSWORD ssh $XEN_ROOT@$HOST \
'
set +x
route -n | grep -F 169.254.0
'

	sshpass -p $FUELMASTER_PASSWORD ssh $FUELMASTER_ROOT@$FUELMASTER \
'
set +x
ssh '$eth2' iptables -S | grep eth2
'
done
