name=${1-"xenserver-fuel-plugin*"}

dockerctl copy cleardb.py nailgun:/tmp/cleardb.py
dockerctl shell nailgun /tmp/cleardb.py
dockerctl shell nailgun rm /tmp/cleardb.py
dockerctl copy newrelease.yaml nailgun:/tmp/newrelease.yaml
dockerctl shell nailgun manage.py loaddata /tmp/newrelease.yaml
dockerctl shell nailgun rm /tmp/newrelease.yaml
fuel rel --sync-deployment-tasks --dir /etc/puppet/