#!/usr/bin/env python

import ConfigParser
import os
import shutil
import utils


utils.setup_logging('controller_post_deployment.log')
LOG = utils.LOG


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
            memcached_servers = cf.get('keystone_authtoken',
                                       'memcached_servers')
            cf.set('cache', 'memcached_servers', memcached_servers)
            cf.set('DEFAULT', 'memcached_servers', memcached_servers)
            with open(filename, 'w') as configfile:
                cf.write(configfile)
            LOG.info('%s created' % filename)
            utils.execute('service', 'nova-novncproxy', 'restart')
            utils.execute('service', 'nova-consoleauth', 'restart')
        except Exception:
            utils.reportError('Cannot set configurations to %s' % filename)


def patch_nova_conductor():
    """Add patches which are not merged to upstream

    Order of patches applied:
        live-migration-vifmapping-controller.patch
    """
    patchfile_list = [
        # Change-Id: If0fb5d764011521916fbbe15224f524a220052f3
        'live-migration-vifmapping-controller.patch',
    ]
    for patch_file in patchfile_list:
        utils.patch(utils.DIST_PACKAGES_DIR, patch_file, 1)

    # Restart related service
    utils.execute('service', 'nova-conductor', 'restart')


if __name__ == '__main__':
    patch_nova_conductor()
    mod_novnc()
