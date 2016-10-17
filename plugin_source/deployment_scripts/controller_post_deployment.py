#!/usr/bin/env python

import ConfigParser
from glanceclient import Client
from keystoneauth1 import loading
from keystoneauth1 import session
import os
from time import sleep
import utils
import yaml


LOG = utils.setup_logging('controller_post_deployment.log')


def get_keystone_creds():
    return {
        'username': os.environ.get('OS_USERNAME'),
        'password': os.environ.get('OS_PASSWORD'),
        'auth_url': os.environ.get('OS_AUTH_URL'),
        'tenant_name': os.environ.get('OS_TENANT_NAME'),
    }


def get_keystone_session():
    loader = loading.get_plugin_loader('password')
    creds = get_keystone_creds()
    auth = loader.load_from_options(**creds)
    return session.Session(auth=auth)


def list_images(sess):
    LOG.info('Listing images:')
    glance = Client('2', session=sess)
    images = glance.images.list()
    for image in images:
        LOG.info(('+ {name} container_format:{container_format} '
                  'disk_format:{disk_format} visibility:{visibility} '
                  'file:{file}').format(**image))


def del_images(sess, image_name):
    glance = Client('2', session=sess)
    images = glance.images.list()
    for image in images:
        if image.name == image_name:
            glance.images.delete(image.id)
            LOG.info('Image %s has been deleted' % image_name)


def add_image(sess, image_name, vm_mode, image_file):
    glance = Client('2', session=sess)
    image = glance.images.create(name=image_name, container_format="ovf",
                                 disk_format="vhd", visibility="public",
                                 vm_mode=vm_mode)
    with open(image_file, 'rb') as f:
        glance.images.upload(image.id, f)
    LOG.info('Image %s (mode: %s, file: %s) has been added' %
             (image_name, vm_mode, image_file))


def wait_ocf_resource_started(timeout, interval):
    """Wait until all ocf resources are started"""
    LOG.info("Waiting for all ocf resources to start")
    remain_time = timeout
    while remain_time > 0:
        resources = utils.execute('pcs', 'resource', 'show')
        if resources:
            exists_not_started = any([("Started" not in line)
                                      for line in resources.split('\n')
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
            cf.read(filename)
            cf.set('DEFAULT', 'novncproxy_base_url',
                   'http//%s:6080/vnc_auto.html' % public_ip)
            cf.set('DEFAULT', 'novncproxy_host', '0.0.0.0')
            with open(filename, 'w') as configfile:
                cf.write(configfile)
            LOG.info('%s created' % filename)
            utils.execute('service', 'nova-novncproxy', 'restart')
            utils.execute('service', 'nova-consoleauth', 'restart')
        except Exception:
            utils.reportError('Cannot set configurations to %s' % filename)


def mod_ceilometer():
    rc, out, err = utils.detailed_execute(
        'pcs', 'resource', 'show', 'p_ceilometer-agent-central',
        allowed_return_codes=[0, 1])

    """Wait until all ocf resources are started, otherwise there is risk for race
    condition: If run "pcs resource restart" while some resources are still in
    restarting or initiating stage, it may result into failures for both.
    """
    if rc == 0:
        wait_ocf_resource_started(300, 10)
        LOG.info("Patching ceilometer pipeline.yaml to exclude \
            network.servers.*")
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
            'pcs', 'resource', 'restart', 'p_ceilometer-agent-central')

        LOG.info(restart_info)


if __name__ == '__main__':
    sess = get_keystone_session()
    list_images(sess)
    del_images(sess, "TestVM")
    add_image(sess, "TestVM", "xen", "cirros-0.3.4-x86_64-disk.vhd.tgz")
    list_images(sess)
    mod_ceilometer()
    mod_novnc()
