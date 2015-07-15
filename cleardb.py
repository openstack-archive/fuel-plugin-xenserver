#!/usr/bin/env python

import os
import yaml

settings = yaml.load(open('/etc/nailgun/settings.yaml'))
os.environ["PGPASSWORD"] = settings['DATABASE']['passwd']
cmd = ('psql -h {host} -p {port} -U {user} -w -d {name} '
	'-c "delete from releases where name like \'%Xen%\';" '
	).format(**settings['DATABASE'])

os.system(cmd)