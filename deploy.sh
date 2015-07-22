source localrc

scp cleardb.py root@$FUELMASTER:$PLUGIN_PATH
ssh root@$FUELMASTER dockerctl copy cleardb.py nailgun:/tmp/cleardb.py
ssh root@$FUELMASTER dockerctl shell nailgun /tmp/cleardb.py

cat base_release.yaml > newrelease.yaml
echo '- pk: 9' >> newrelease.yaml
echo '  extend: *base_release' >> newrelease.yaml
cat xs_release.yaml >> newrelease.yaml
scp newrelease.yaml root@$FUELMASTER:$PLUGIN_PATH
ssh root@$FUELMASTER dockerctl copy newrelease.yaml nailgun:/tmp/newrelease.yaml
ssh root@$FUELMASTER dockerctl shell nailgun manage.py loaddata /tmp/newrelease.yaml
ssh root@$FUELMASTER fuel rel --sync-deployment-tasks --dir /etc/puppet/
rm newrelease.yaml

fpb --check xenserver-fuel-plugin
fpb --build xenserver-fuel-plugin

scp xenserver-fuel-plugin/xenserver-fuel-plugin-$BUILD_VERSION.noarch.rpm root@$FUELMASTER:$PLUGIN_PATH

ssh root@$FUELMASTER fuel plugins --install $PLUGIN_PATH/xenserver-fuel-plugin-$BUILD_VERSION.noarch.rpm ||
ssh root@$FUELMASTER fuel plugins --update $PLUGIN_PATH/xenserver-fuel-plugin-$BUILD_VERSION.noarch.rpm

ssh root@$FUELMASTER fuel plugins --list
