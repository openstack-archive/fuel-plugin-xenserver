#!/usr/bin/env python

import logging
import netifaces
import os
import subprocess
import yaml

XS_RSA = '/root/.ssh/xs_rsa'
ASTUTE_PATH = '/etc/astute.yaml'
ASTUTE_SECTION = '@PLUGIN_NAME@'
LOG_ROOT = '/var/log/@PLUGIN_NAME@'
HIMN_IP = '169.254.0.1'


class ExecutionError(Exception):
    pass


class FatalException(Exception):
    pass


def reportError(err):
    logging.error(err)
    raise FatalException(err)


def ssh(host, username, *cmd, **kwargs):
    cmd = map(str, cmd)

    return execute('ssh', '-i', XS_RSA,
                   '-o', 'StrictHostKeyChecking=no',
                   '%s@%s' % (username, host), *cmd,
                   prompt=kwargs.get('prompt'))


def scp(host, username, target_path, filename):
    return execute('scp', '-i', XS_RSA,
                   '-o', 'StrictHostKeyChecking=no', filename,
                   '%s@%s:%s' % (username, host, target_path))


def execute(*cmd, **kwargs):
    cmd = map(str, cmd)
    _env = kwargs.get('env')
    env_prefix = ''
    if _env:
        env_prefix = ''.join(['%s=%s ' % (k, _env[k]) for k in _env])

        env = dict(os.environ)
        env.update(_env)
    else:
        env = None
    logging.info(env_prefix + ' '.join(cmd))
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE,  # nosec
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, env=env)

    if 'prompt' in kwargs:
        prompt = kwargs.get('prompt')
        proc.stdout.flush()
        (out, err) = proc.communicate(prompt)
    else:
        out = proc.stdout.readlines()
        err = proc.stderr.readlines()
        (out, err) = map(' '.join, [out, err])

    # Both if/else need to deal with "\n" scenario
    (out, err) = (out.replace('\n', ''), err.replace('\n', ''))

    if out:
        logging.debug(out)
    if err:
        logging.error(err)

    if proc.returncode is not None and proc.returncode != 0:
        raise ExecutionError(err)

    return out


def get_astute(astute_path=ASTUTE_PATH):
    """Return the root object read from astute.yaml"""
    if not os.path.exists(astute_path):
        reportError('%s not found' % astute_path)
    with open(astute_path) as f:
        astute = yaml.safe_load(f)
    return astute


def astute_get(dct, keys, default=None, fail_if_missing=True):
    """A safe dictionary getter"""
    for key in keys:
        if key in dct:
            dct = dct[key]
        else:
            if fail_if_missing:
                reportError('Value of "%s" is missing' % key)
            return default
    return dct


def get_options(astute, astute_section=ASTUTE_SECTION):
    """Return username and password filled in plugin."""
    if astute_section not in astute:
        reportError('%s not found' % astute_section)

    options = astute[astute_section]
    logging.info('username: {username}'.format(**options))
    logging.info('password: {password}'.format(**options))
    logging.info('install_xapi: {install_xapi}'.format(**options))
    return options['username'], options['password'], \
        options['install_xapi']


def init_eth():
    """Initialize the net interface connected to HIMN

    Returns:
        the IP addresses of local host and hypervisor.
    """

    def _mac(eth):
        netifaces.ifaddresses(eth).get(netifaces.AF_LINK)[0]['addr']

    domid = execute('xenstore-read', 'domid')
    himn_mac = execute(
        'xenstore-read',
        '/local/domain/%s/vm-data/himn_mac' % domid)
    logging.info('himn_mac: %s' % himn_mac)

    eths = [eth for eth in netifaces.interfaces() if _mac(eth) == himn_mac]
    if len(eths) != 1:
        reportError('Cannot find eth matches himn_mac')

    eth = eths[0]

    logging.info('himn_eth: %s' % eth)

    ip = netifaces.ifaddresses(eth).get(netifaces.AF_INET)

    if not ip:
        execute('dhclient', eth)
        fname = '/etc/network/interfaces.d/ifcfg-' + eth
        s = ('auto {eth}\n'
             'iface {eth} inet dhcp\n'
             'post-up route del default dev {eth}').format(eth=eth)
        with open(fname, 'w') as f:
            f.write(s)
        logging.info('%s created' % fname)
        execute('ifdown', eth)
        execute('ifup', eth)
        ip = netifaces.ifaddresses(eth).get(netifaces.AF_INET)

    if ip:
        himn_local = ip[0]['addr']
        himn_xs = '.'.join(himn_local.split('.')[:-1] + ['1'])
        if HIMN_IP == himn_xs:
            logging.info('himn_local: %s' % himn_local)
            return eth, himn_local

    reportError('HIMN failed to get IP address from Hypervisor')
