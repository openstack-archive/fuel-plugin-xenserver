#!/usr/bin/env python

from distutils.version import LooseVersion
import json
import os
import stat
import utils
from utils import HIMN_IP

XS_RSA = '/root/.ssh/xs_rsa'
VERSION_HOTFIXES = '@VERSION_HOTFIXES@'
MIN_XCP_VERSION = '2.1.0'

utils.setup_logging('compute_pre_test.log')
LOG = utils.LOG


def ssh_copy_id(host, username, password):
    ssh_askpass = "askpass.sh"

    s = ('#!/bin/sh\n'
         'echo "{password}"').format(password=password)
    with open(ssh_askpass, 'w') as f:
        f.write(s)
    os.chmod(ssh_askpass, stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    if os.path.exists(XS_RSA):
        os.remove(XS_RSA)
    if os.path.exists(XS_RSA + ".pub"):
        os.remove(XS_RSA + ".pub")
    utils.execute('ssh-keygen', '-f', XS_RSA, '-t', 'rsa', '-N', '')

    env = {
        "HOME": "/root",
        "SSH_ASKPASS": os.path.abspath(ssh_askpass),
        "DISPLAY": ":.",
    }
    utils.execute("setsid", "ssh-copy-id", "-o", "StrictHostKeyChecking=no",
                  "-i", XS_RSA, "%s@%s" % (username, host), env=env)


def check_host_compatibility(himn, username):
    xcp_version = utils.get_xcp_version(himn, username)
    if LooseVersion(xcp_version) < LooseVersion(MIN_XCP_VERSION):
        utils.reportError('Host version %s should equal or greater than %s' %
                          (xcp_version, MIN_XCP_VERSION))
        return

    version_hotfixes = json.loads(VERSION_HOTFIXES)

    ver = utils.ssh(himn, username,
                    ('xe host-param-get uuid=$(xe host-list --minimal) '
                     'param-name=software-version param-key=product_version'))
    hotfixes = version_hotfixes.get(ver)
    if not hotfixes:
        return

    for hotfix in hotfixes:
        if not hotfix:
            continue

        installed = utils.ssh(himn, username,
                              'xe patch-list name-label=%s --minimal' % hotfix)

        if not installed:
            utils.reportError('Hotfix %s has not been installed ' % ver)


def check_local_sr(himn, username):
    sr_type = utils.ssh(himn, username,
                        ('xe sr-param-get param-name=type '
                         'uuid=`xe pool-list params=default-SR --minimal`'))

    if sr_type != "ext" and sr_type != "nfs":
        utils.reportError(('Default SR type should be EXT or NFS.  If using '
                           'local storage, Please make sure thin provisioning '
                           'is enabled on your host during installation.'))


if __name__ == '__main__':
    astute = utils.get_astute()
    if astute:
        username, password, install_xapi = utils.get_options(astute)
        himn_eth, himn_local = utils.init_eth()

        if username and password and himn_local:
            ssh_copy_id(HIMN_IP, username, password)
            check_host_compatibility(HIMN_IP, username)
            check_local_sr(HIMN_IP, username)
