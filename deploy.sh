source localrc

scp cleardb.py root@$FUELMASTER:$PLUGIN_PATH
ssh root@$FUELMASTER dockerctl copy cleardb.py nailgun:/tmp/cleardb.py
ssh root@$FUELMASTER dockerctl shell nailgun /tmp/cleardb.py

scp newrelease.yaml root@$FUELMASTER:$PLUGIN_PATH
ssh root@$FUELMASTER dockerctl copy newrelease.yaml nailgun:/tmp/newrelease.yaml
ssh root@$FUELMASTER dockerctl shell nailgun manage.py loaddata /tmp/newrelease.yaml

fpb --check ./
fpb --build .

scp xenserver-fuel-plugin-$BUILD_VERSION.noarch.rpm root@$FUELMASTER:$PLUGIN_PATH

ssh root@$FUELMASTER fuel plugins --install $PLUGIN_PATH/xenserver-fuel-plugin-$BUILD_VERSION.noarch.rpm ||
ssh root@$FUELMASTER fuel plugins --update $PLUGIN_PATH/xenserver-fuel-plugin-$BUILD_VERSION.noarch.rpm

ssh root@$FUELMASTER fuel plugins --list
