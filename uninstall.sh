name=${1-"xenserver-fuel-plugin*"}
cd /var/www/nailgun/plugins/%{name}

dockerctl copy cleardb.py nailgun:/tmp/cleardb.py
dockerctl shell nailgun /tmp/cleardb.py
dockerctl shell nailgun rm /tmp/cleardb.py
fuel rel --sync-deployment-tasks --dir /etc/puppet/
