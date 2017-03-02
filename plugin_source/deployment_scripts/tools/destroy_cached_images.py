#!/usr/bin/env python
# Licensed under the Apache License, Version 2.0 (the "License").
# You may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""This tool is used to clean up Glance images that are cached in the SR."""


import sys

from oslo_config import cfg

import nova.conf
from nova import config
from nova import utils
from nova.virt.xenapi.client import session
from nova.virt.xenapi import vm_utils

destroy_opts = [
    cfg.BoolOpt('all_cached',
                default=False,
                help='Destroy all cached images instead of just unused cached'
                     ' images.'),
    cfg.BoolOpt('dry_run',
                default=False,
                help='Don\'t actually delete the VDIs.')
]

CONF = nova.conf.CONF
CONF.register_cli_opts(destroy_opts)


def main():
    """By default, this script will only cleanup unused cached images.

    Options:

    --all_cached - Destroy all cached images instead of just unused cached
                   images.
    --dry_run    - Don't actually destroy the VDIs.
    """
    config.parse_args(sys.argv)
    utils.monkey_patch()

    _session = session.XenAPISession(CONF.xenserver.connection_url,
                                     CONF.xenserver.connection_username,
                                     CONF.xenserver.connection_password)

    sr_ref = vm_utils.safe_find_sr(_session)
    destroyed = vm_utils.destroy_cached_images(
        _session, sr_ref, all_cached=CONF.all_cached,
        dry_run=CONF.dry_run)

    if '--verbose' in sys.argv:
        print('\n'.join(destroyed))

    print("Destroyed %d cached VDIs" % len(destroyed))


if __name__ == "__main__":
    main()
