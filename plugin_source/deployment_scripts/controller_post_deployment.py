#!/usr/bin/env python

import ConfigParser
from glanceclient import Client
import keystoneauth1
import logging
import os
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


def get_keystone_session():
    loader = keystoneauth1.loading.get_plugin_loader('password')
    creds = get_keystone_creds()
    auth = loader.load_from_options(**creds)
    return keystoneauth1.session.Session(auth=auth)


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


def wait_ocf_resource_started(timeout, interval):
    """Wait until all ocf resources are started"""
    remain_time = timeout
    while remain_time > 0:
        resources = utils.execute('pcs', 'resource', 'show',
                                  allowed_return_codes=[0, 124])
        if resources:
            exists_not_started = any([("Started" not in line)
                                      for line in resources.split()
                                      if "ocf::fuel" in line])
            # All started
            if not exists_not_started:
                return
        sleep(interval)
        remain_time = timeout - interval

    utils.reportError("Timeout for waiting resources to start")


def mod_novnc():
    astute = utils.get_astute()
    if astute:
        public_ip = utils.astute_get(
            astute, ('network_metadata', 'vips', 'public', 'ipaddr'))
        filename = '/etc/nova/nova-compute.conf'
        cf = ConfigParser.ConfigParser()
        try:
            cf.set('DEFAULT', 'novncproxy_base_url',
                   'http://%s:6080/vnc_auto.html' % public_ip)
            cf.set('DEFAULT', 'novncproxy_host', "0.0.0.0")
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
    session = get_keystone_session()
    list_images(session)
    del_images(session, "TestVM")
    add_image(session, "TestVM", "xen", "cirros-0.3.4-x86_64-disk.vhd.tgz")
    list_images(session)
    mod_ceilometer()
