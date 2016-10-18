#!/usr/bin/env python

import ConfigParser
from glanceclient import Client
from keystoneauth1 import loading
from keystoneauth1 import session
import logging
import os
import shutil
from time import sleep
import utils
import yaml


LOG_FILE = os.path.join(utils.LOG_ROOT, 'controller_post_deployment.log')

if not os.path.exists(utils.LOG_ROOT):
    os.mkdir(utils.LOG_ROOT)

logging.basicConfig(filename=LOG_FILE,
                    level=logging.DEBUG)


def get_keystone_creds():
    return {
        'username': os.environ['OS_USERNAME'],
        'password': os.environ['OS_PASSWORD'],
        'auth_url': os.environ['OS_AUTH_URL'],
        'tenant_name': os.environ['OS_TENANT_NAME'],
    }


def replace_test_image(image_name, vm_mode, image_file):
    loader = loading.get_plugin_loader('password')
    creds = get_keystone_creds()
    auth = loader.load_from_options(**creds)
    sess = session.Session(auth=auth)
    glance = Client('2', session=sess)
    images = glance.images.list()
    for image in images:
        if image.name == image_name:
            glance.images.delete(image.id)
    image = glance.images.create(name=image_name, container_format="ovf",
                                 disk_format="vhd", visibility="public",
                                 vm_mode=vm_mode)
    with open(image_file, 'rb') as f:
        glance.images.upload(image.id, f)


def wait_ocf_resource_started(timeout, interval):
    """Wait until all ocf resources are started"""
    remain_time = timeout
    while remain_time > 0:
        resources = utils.execute('pcs', 'resource', 'show',
                                  allowed_return_codes=[0, 124])
        if resources:
            all_started = all([("Started" not in line)
                               for line in resources.split()
                               if "ocf::fuel" in line])
            if all_started:
                return
        sleep(interval)
        remain_time = timeout - interval

    utils.reportError("Timeout for waiting resources to start")


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
        except Exception:
            utils.reportError('Cannot set configurations to %s' % filename)
        logging.info('%s created' % filename)


def mod_ceilometer():
    resource_exists = utils.execute(
        'pcs', 'resource', 'show', 'p_ceilometer-agent-central',
        allowed_return_codes=[0, 124])

    """Wait until all ocf resources are started, otherwise there is risk for race
    condition: If run "pcs resource restart" while some resources are still in
    restarting or initiating stage, it may result into failures for both.
    """
    if resource_exists:
        wait_ocf_resource_started(300, 10)

        # Exclude network.services.* to avoid error 404
        pipeline = '/etc/ceilometer/pipeline.yaml'
        if not os.path.exists(pipeline):
            utils.reportError('%s not found' % pipeline)
        with open(pipeline) as f:
            ceilometer = yaml.safe_load(f)
        sources = utils.astute_get(ceilometer, ('sources',))
        if len(sources) != 1:
            utils.reportError('ceilometer has none or more than one sources')
        source = sources[0]
        meters = utils.astute_get(source, ('meters',))
        new_meter = '!network.services.*'
        if new_meter not in meters:
            meters.append(new_meter)
        with open(pipeline, "w") as f:
            ceilometer = yaml.safe_dump(ceilometer, f)

        restart_info = utils.execute(
            'pcs', 'resource', 'restart', 'p_ceilometer-agent-central',
            allowed_return_codes=[0, 124])

        logging.info(restart_info)

if __name__ == '__main__':
    replace_test_image("TestVM", "xen", "cirros-0.3.4-x86_64-disk.vhd.tgz")
    mod_ceilometer()
