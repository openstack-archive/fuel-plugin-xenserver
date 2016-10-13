#!/usr/bin/env python

from glanceclient import Client
from keystoneauth1 import loading
from keystoneauth1 import session
import logging
import os
import sys
import utils
import yaml

LOG_FILE = os.path.join(utils.LOG_ROOT, 'compute_post_deployment.log')


def get_keystone_creds():
    return {
        'username': os.environ['OS_USERNAME'],
        'password': os.environ['OS_PASSWORD'],
        'auth_url': os.environ['OS_AUTH_URL'],
        'project_id': os.environ['OS_TENANT_NAME'],
    }


def replace_test_image(image_name, vm_mode, image_file):
    loader = loading.get_plugin_loader('password')
    creds = utils.get_keystone_creds()
    auth = loader.load_from_options(**creds)
    session = session.Session(auth=auth)

    glance = Client('2', session=session)
    images = glance.images.list()
    for image in images:
        if image.name == image_name:
            glance.images.delete(image.id)
    image = glance.images.create(name=image_name, container_format="ovf",
                                 disk_format="vhd", visibility="public",
                                 file=image_file, vm_mode=vm_mode)


def mod_ceilometer():
    resource_exists = utils.execute(
        'pcs', 'resource', 'show', 'p_ceilometer-agent-central',
        allowed_return_codes=[0, 124])

    if resource_exists:
        # Exclude network.services.* to avoid error 404
        pipeline = '/etc/ceilometer/pipeline.yaml'
        if not os.path.exists(pipeline):
            reportError('%s not found' % pipeline)
        with open(pipeline) as f:
            ceilometer = yaml.safe_load(f)
        sources = utils.astute_get(ceilometer, ('sources',))
        if len(sources) != 1:
            reportError('ceilometer has none or more than one sources')
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
