#!/usr/bin/env python

import logging
import netifaces
import os
import subprocess
import yaml

# Below modules are not installed when running compute pre-deployment
try:
    from glanceclient import Client
    from keystoneauth1 import loading
    from keystoneauth1 import session
except ImportError:
    pass

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
        logging.info(err)

    if proc.returncode is not None and proc.returncode != 0:
        if proc.returncode in kwargs.get('allowed_return_codes', [0]):
            logging.info('Swallowed acceptable return code of %d',
                         proc.returncode)
        else:
            raise ExecutionError(err)

    return out


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


def get_keystone_creds():
    return {
        'username': os.environ['OS_USERNAME'],
        'password': os.environ['OS_PASSWORD'],
        'auth_url': os.environ['OS_AUTH_URL'],
        'tenant_name': os.environ['OS_TENANT_NAME'],
    }


def get_keystone_session():
    loader = loading.get_plugin_loader('password')
    creds = get_keystone_creds()
    auth = loader.load_from_options(**creds)
    sess = session.Session(auth=auth)
    return sess


def list_images(sess):
    logging.info('Listing images:')
    glance = Client('2', session=sess)
    images = glance.images.list()
    for image in images:
        logging.info('+ {name}'.format(**image))


def del_images(sess, image_name):
    glance = Client('2', session=sess)
    images = glance.images.list()
    for image in images:
        if image.name == image_name:
            glance.images.delete(image.id)
            logging.info('Image %s is delete' % image_name)


def add_image(sess, image_name, vm_mode, image_file):
    glance = Client('2', session=sess)
    image = glance.images.create(name=image_name, container_format="ovf",
                                 disk_format="vhd", visibility="public",
                                 vm_mode=vm_mode)
    with open(image_file, 'rb') as f:
        glance.images.upload(image.id, f)
    logging.info('Image %s (mode: %s, file: %s) is added' %
                 (image_name, vm_mode, image_file))
