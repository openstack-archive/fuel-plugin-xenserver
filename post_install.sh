name=${1-"fuel-plugin-xenserver*"}
cd /var/www/nailgun/plugins/%{name}

dockerctl copy cleardb.py nailgun:/tmp/cleardb.py
dockerctl shell nailgun /tmp/cleardb.py
dockerctl shell nailgun rm /tmp/cleardb.py

cp openstack.yaml xs_release.yaml
patch -p1 xs_release.yaml < xs_release.patch
dockerctl copy xs_release.yaml nailgun:/tmp/xs_release.yaml

dockerctl shell nailgun manage.py loaddata /tmp/xs_release.yaml
dockerctl shell nailgun rm /tmp/xs_release.yaml
fuel rel --sync-deployment-tasks --dir /etc/puppet/
