#!/usr/bin/env python

import os
import yaml

settings = yaml.load(open('/etc/nailgun/settings.yaml'))
db_settings = settings['DATABASE']
os.environ["PGPASSWORD"] = db_settings['passwd']

def execute_sql(sql):
	paras = dict(db_settings.items() + {'sql':sql}.items())
	print paras
	cmd = ('psql -h {host} -p {port} -U {user} -w -d {name} '
		'-c "{sql}" '
		).format(**paras)
	os.system(cmd)

if __name__ == '__main__':
	execute_sql('delete from releases where name like \'%Xen%\';')

