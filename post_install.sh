name=${1-"fuel-plugin-xenserver*"}
cd /var/www/nailgun/plugins/%{name}

dockerctl copy cleardb.py nailgun:/tmp/cleardb.py
dockerctl shell nailgun /tmp/cleardb.py
dockerctl shell nailgun rm /tmp/cleardb.py
dockerctl copy xs_release.yaml nailgun:/tmp/xs_release.yaml
dockerctl shell nailgun manage.py loaddata /tmp/xs_release.yaml
dockerctl shell nailgun rm /tmp/xs_release.yaml
fuel rel --sync-deployment-tasks --dir /etc/puppet/
