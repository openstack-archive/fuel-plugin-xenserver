source localrc

ACTION=${1:-"all"}
TMP="/tmp"

[ -e "$VIRENV_PATH/bin/activate" ] ||	virtualenv "$VIRENV_PATH"

source $VIRENV_PATH/bin/activate

function deploy_release {
	scp cleardb.py root@$FUELMASTER:$TMP
	ssh root@$FUELMASTER dockerctl copy "$TMP/cleardb.py" nailgun:/tmp/cleardb.py
	ssh root@$FUELMASTER dockerctl shell nailgun /tmp/cleardb.py
	ssh root@$FUELMASTER rm "$TMP/cleardb.py"

	cat base_release.yaml > newrelease.yaml
	echo '- pk: 9' >> newrelease.yaml
	echo '  extend: *base_release' >> newrelease.yaml
	cat xs_release.yaml >> newrelease.yaml
	scp newrelease.yaml root@$FUELMASTER:$TMP
	ssh root@$FUELMASTER dockerctl copy "$TMP/newrelease.yaml" nailgun:/tmp/newrelease.yaml
	ssh root@$FUELMASTER dockerctl shell nailgun manage.py loaddata /tmp/newrelease.yaml
	ssh root@$FUELMASTER fuel rel --sync-deployment-tasks --dir /etc/puppet/
	rm newrelease.yaml
	ssh root@$FUELMASTER rm "$TMP/newrelease.yaml"
}

function deploy_plugin {
	fpb --check xenserver-fuel-plugin
	fpb --build xenserver-fuel-plugin

	scp xenserver-fuel-plugin/xenserver-fuel-plugin-0.0-$VERSION-1.noarch.rpm root@$FUELMASTER:$TMP

	#ssh root@$FUELMASTER fuel plugins --remove xenserver-fuel-plugin==$VERSION
	if ssh root@$FUELMASTER fuel plugins --list | grep xenserver-fuel-plugin; then
		ssh root@$FUELMASTER fuel plugins --update "$TMP/xenserver-fuel-plugin-0.0-$VERSION-1.noarch.rpm"
	else
		ssh root@$FUELMASTER fuel plugins --install "$TMP/xenserver-fuel-plugin-0.0-$VERSION-1.noarch.rpm"
	fi

	ssh root@$FUELMASTER rm "$TMP/xenserver-fuel-plugin-0.0-$VERSION-1.noarch.rpm"
}
case $ACTION in
	"release") deploy_release ;;
	"plugin") deploy_plugin ;;
	"all") 
		deploy_release
		deploy_plugin
		;;
esac