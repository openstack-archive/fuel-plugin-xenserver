source localrc

ACTION=${1:-"all"}

[ -e "$VIRENV_PATH/bin/activate" ] ||	virtualenv "$VIRENV_PATH"

source $VIRENV_PATH/bin/activate

function deploy_release {
	sshpass -p $XEN_PASSWORD scp cleardb.py root@$FUELMASTER:/tmp
	sshpass -p $XEN_PASSWORD ssh $XEN_ROOT@$FUELMASTER \
'
dockerctl copy "/tmp/cleardb.py" nailgun:/tmp/cleardb.py
dockerctl shell nailgun /tmp/cleardb.py
rm "/tmp/cleardb.py"
'
	cat base_release.yaml > newrelease.yaml
	echo '- pk: 9' >> newrelease.yaml
	echo '  extend: *base_release' >> newrelease.yaml
	cat xs_release.yaml >> newrelease.yaml
	sshpass -p $XEN_PASSWORD scp newrelease.yaml root@$FUELMASTER:/tmp
	sshpass -p $XEN_PASSWORD ssh $XEN_ROOT@$FUELMASTER \
'
dockerctl copy "/tmp/newrelease.yaml" nailgun:/tmp/newrelease.yaml
dockerctl shell nailgun manage.py loaddata /tmp/newrelease.yaml
fuel rel --sync-deployment-tasks --dir /etc/puppet/
rm "/tmp/newrelease.yaml"
'
	rm newrelease.yaml
}

function deploy_plugin {
	if ! [ -e xenserver-fuel-plugin/deployment_scripts/novaplugins.iso ]; then
		if [ -e ../nova-suppack/suppack/novaplugins.iso ]; then
			cp ../nova-suppack/suppack/novaplugins.iso \
				xenserver-fuel-plugin/deployment_scripts/
		else
			sudo ./build-nova-suppack.sh
		fi
	fi

	fpb --check xenserver-fuel-plugin
	fpb --build xenserver-fuel-plugin

	sshpass -p $XEN_PASSWORD scp xenserver-fuel-plugin/xenserver-fuel-plugin-0.0-$VERSION-1.noarch.rpm root@$FUELMASTER:/tmp

	#sshpass -p $XEN_PASSWORD ssh $XEN_ROOT@$FUELMASTER fuel plugins --remove xenserver-fuel-plugin==$VERSION
	if sshpass -p $XEN_PASSWORD ssh $XEN_ROOT@$FUELMASTER fuel plugins --list | grep xenserver-fuel-plugin; then
		#sshpass -p $XEN_PASSWORD ssh $XEN_ROOT@$FUELMASTER fuel plugins --update "/tmp/xenserver-fuel-plugin-0.0-$VERSION-1.noarch.rpm"
		sshpass -p $XEN_PASSWORD ssh $XEN_ROOT@$FUELMASTER fuel plugins --remove "xenserver-fuel-plugin==$VERSION"
		sshpass -p $XEN_PASSWORD ssh $XEN_ROOT@$FUELMASTER fuel plugins --install "/tmp/xenserver-fuel-plugin-0.0-$VERSION-1.noarch.rpm"
	else
		sshpass -p $XEN_PASSWORD ssh $XEN_ROOT@$FUELMASTER fuel plugins --install "/tmp/xenserver-fuel-plugin-0.0-$VERSION-1.noarch.rpm"
	fi

	sshpass -p $XEN_PASSWORD ssh $XEN_ROOT@$FUELMASTER rm "/tmp/xenserver-fuel-plugin-0.0-$VERSION-1.noarch.rpm"
}
case $ACTION in
	"release") deploy_release ;;
	"plugin") deploy_plugin ;;
	"all") 
		deploy_release
		deploy_plugin
		;;
esac