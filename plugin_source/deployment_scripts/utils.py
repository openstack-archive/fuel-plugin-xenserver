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


def detailed_execute(*cmd, **kwargs):
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

    prompt = kwargs.get('prompt')
    if prompt:
        (out, err) = proc.communicate(prompt)
    else:
        (out, err) = proc.communicate()

    if out:
        # Truncate "\n" if it is the last char
        out = out.strip()
        logging.debug(out)
    if err:
        logging.info(err)

    if proc.returncode is not None and proc.returncode != 0:
        if proc.returncode in kwargs.get('allowed_return_codes', [0]):
            logging.info('Swallowed acceptable return code of %d',
                         proc.returncode)
        else:
            raise ExecutionError(err)

    return proc.returncode, out, err


def execute(*cmd, **kwargs):
    _, out, _ = detailed_execute(*cmd, **kwargs)
    return out


def patch(directory, patch_file, level):
    cwd = os.getcwd()
    patchset_dir = os.path.join(cwd, "patchset")

    patches_applied = os.path.join(patchset_dir, "patches_applied")

    patched = False
    if os.path.exists(patches_applied):
        with open(patches_applied) as f:
            patches = f.read().split('\n')
        patched = (patch_file) in patches

    if not patched:
        execute('patch', '-d', directory, '-p%s' % level, '-i',
                os.path.join(patchset_dir, patch_file))
        with open(patches_applied, "a") as f:
            f.write(patch_file + "\n")
    else:
        logging.info(patch_file + " is already applied - skipping")


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


def eth_to_mac(eth):
    return netifaces.ifaddresses(eth).get(netifaces.AF_LINK)[0]['addr']


def detect_himn_ip(eths=None):
    if eths is None:
        eths = netifaces.interfaces()
    for eth in eths:
        ip = netifaces.ifaddresses(eth).get(netifaces.AF_INET)
        if ip is None:
            continue
        himn_local = ip[0]['addr']
        himn_xs = '.'.join(himn_local.split('.')[:-1] + ['1'])
        if HIMN_IP == himn_xs:
            return eth, ip
    return None, None


def find_eth_xenstore():
    domid = execute('xenstore-read', 'domid')
    himn_mac = execute(
        'xenstore-read',
        '/local/domain/%s/vm-data/himn_mac' % domid)
    logging.info('himn_mac: %s' % himn_mac)

    eths = [eth for eth in netifaces.interfaces()
            if eth_to_mac(eth) == himn_mac]
    if len(eths) != 1:
        reportError('Cannot find eth matches himn_mac')

    return eths[0]


def detect_eth_dhclient():
    for eth in netifaces.interfaces():
        # Don't try and dhclient for devices an IP address already
        ip = netifaces.ifaddresses(eth).get(netifaces.AF_INET)
        if ip:
            continue

        # DHCP replies from HIMN should be super fast
        execute('timeout', '2s', 'dhclient', eth,
                allowed_return_codes=[0, 124])
        try:
            _, ip = detect_himn_ip([eth])
            if ip is not None:
                return eth
        finally:
            execute('dhclient', '-r', eth)


def init_eth():
    """Initialize the net interface connected to HIMN

    Returns:
        the IP addresses of local host and hypervisor.
    """

    eth, ip = detect_himn_ip()

    if not ip:
        eth = None
        try:
            eth = find_eth_xenstore()
        except Exception:
            logging.debug('Failed to find MAC through xenstore', exc_info=True)

        if eth is None:
            eth = detect_eth_dhclient()

        if eth is None:
            reportError('Failed to detect HIMN ethernet device')

        logging.info('himn_eth: %s' % eth)

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
        himn_local = ip[0]['addr']
        himn_xs = '.'.join(himn_local.split('.')[:-1] + ['1'])
        if HIMN_IP != himn_xs:
            # Not on the HIMN - we failed here.
            logging.info('himn_local: DHCP returned incorrect IP %s' %
                         ip[0]['addr'])
            ip = None

    if not ip:
        reportError('HIMN failed to get IP address from Hypervisor')

    logging.info('himn_local: %s' % ip[0]['addr'])
    return eth, ip[0]['addr']
