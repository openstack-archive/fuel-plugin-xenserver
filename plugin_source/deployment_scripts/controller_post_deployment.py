#!/usr/bin/env python

import ConfigParser
import logging
import os
import shutil
import utils


LOG_FILE = os.path.join(utils.LOG_ROOT, 'controller_post_deployment.log')

if not os.path.exists(utils.LOG_ROOT):
    os.mkdir(utils.LOG_ROOT)

logging.basicConfig(filename=LOG_FILE, level=logging.WARNING)
LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)


def mod_novnc():
    astute = utils.get_astute()
    if astute:
        filename = '/etc/nova/nova.conf'
        orig_filename = filename + ".orig"
        if not os.path.exists(orig_filename):
            shutil.copyfile(filename, orig_filename)
        cf = ConfigParser.ConfigParser()
        try:
            cf.read(orig_filename)
            if not cf.has_section('cache'):
                cf.add_section('cache')
            cf.set('cache', 'enable', 'True')
            memcached_servers = cf.get('keystone', 'memcached_servers')
            cf.set('cache', 'memcached_servers', memcached_servers)
            cf.set('DEFAULT', 'memcached_servers', memcached_servers)
            with open(filename, 'w') as configfile:
                cf.write(configfile)
            logging.info('%s created' % filename)
            utils.execute('service', 'nova-novncproxy', 'restart')
            utils.execute('service', 'nova-consoleauth', 'restart')
        except Exception:
            utils.reportError('Cannot set configurations to %s' % filename)


if __name__ == '__main__':
    mod_novnc()
