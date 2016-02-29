name=${1-"fuel-plugin-xenserver*"}
cd /var/www/nailgun/plugins/%{name}

dockerctl copy cleardb.py nailgun:/tmp/cleardb.py
dockerctl shell nailgun /tmp/cleardb.py
dockerctl shell nailgun rm /tmp/cleardb.py
cat base_release.yaml xs_release.yaml > new_release.yaml
dockerctl copy new_release.yaml nailgun:/tmp/new_release.yaml
dockerctl shell nailgun manage.py loaddata /tmp/new_release.yaml
dockerctl shell nailgun rm /tmp/new_release.yaml
rm new_release.yaml
fuel rel --sync-deployment-tasks --dir /etc/puppet/
