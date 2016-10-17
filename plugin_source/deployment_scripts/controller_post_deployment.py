#!/usr/bin/env python

import ConfigParser
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
    session = utils.get_keystone_session()
    utils.list_images(session)
    utils.del_images(session, "TestVM")
    utils.add_images(
        session, "TestVM", "xen", "cirros-0.3.4-x86_64-disk.vhd.tgz")
    utils.list_images(session)
    mod_ceilometer()
