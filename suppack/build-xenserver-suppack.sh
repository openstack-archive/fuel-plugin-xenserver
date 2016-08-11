#!/bin/bash

set -eux

# =============================================
# Usage of this script:
# ./build-xenserver-suppack.sh xs-version xs-build git-branch plugin-version
# or
# ./build-xenserver-suppack.sh
#
# You can provide explict input parameters or you can use the default ones:
#   XenServer version
#   XenServer build
#   OpenStack release branch
#   XenServer OpenStack plugin version


THIS_FILE=$(readlink -f $0)
FUELPLUG_UTILS_ROOT=$(dirname $THIS_FILE)
cd $FUELPLUG_UTILS_ROOT
rm -rf xenserver-suppack
mkdir -p xenserver-suppack && cd xenserver-suppack


# =============================================
# Configurable items

# OpenStack release
OS_RELEASE=${1:-"mitaka"}

# xenserver version info
PLATFORM_VERSION=${2:-"1.9"}
XS_BUILD=${3:-"90233c"}

# nova and neutron xenserver dom0 plugin version
XS_PLUGIN_VERSION=${4:-"2015.1"}

# branch info
GITBRANCH="origin/stable/$OS_RELEASE"

# repository info
NOVA_GITREPO="https://git.openstack.org/openstack/nova"
NEUTRON_GITREPO="https://git.openstack.org/openstack/neutron"
DDK_ROOT_URL="http://copper.eng.hq.xensource.com/builds/ddk-xs6_2.tgz"
RPM_BUILDER_REPO="https://github.com/citrix-openstack/xenserver-nova-suppack-builder"

# Update system and install dependencies
export DEBIAN_FRONTEND=noninteractive

# =============================================
# Install suppack builder
# TODO: check PLATFORM_VERSION
rpm -q supp-pack-build-2.1.0-xs55.noarch
if [ $? -ne 0 ]; then
	rpm -i http://coltrane.uk.xensource.com/usr/groups/release/XenServer-7.x/XS-7.0/RTM-125380/binary-packages/RPMS/domain0/RPMS/noarch/supp-pack-build-2.1.0-xs55.noarch.rpm
fi
rpm -q xcp-python-libs-1.9.0-159.noarch
if [ $? -ne 0 ]; then
	rpm -i http://coltrane.uk.xensource.com/usr/groups/release/XenServer-7.x/XS-7.0/RTM-125380/binary-packages/RPMS/domain0/RPMS/noarch/xcp-python-libs-1.9.0-159.noarch.rpm
fi

# =============================================
# Check out rpm packaging repo
rm -rf xenserver-nova-suppack-builder
git clone $RPM_BUILDER_REPO xenserver-nova-suppack-builder
cd xenserver-nova-suppack-builder
git checkout -b mos_suppack_builder "$GITBRANCH"
cd ..


# =============================================
# Create nova rpm file
rm -rf nova
git clone "$NOVA_GITREPO" nova
cd nova
git checkout -b mos_nova "$GITBRANCH"
# patch xenhost as this file is not merged into this release
cp $FUELPLUG_UTILS_ROOT/../plugin_source/deployment_scripts/patchset/xenhost plugins/xenserver/xenapi/etc/xapi.d/plugins/
cd ..

cp -r xenserver-nova-suppack-builder/plugins/xenserver/xenapi/* nova/plugins/xenserver/xenapi/
cd nova/plugins/xenserver/xenapi/contrib
./build-rpm.sh $XS_PLUGIN_VERSION
cd $FUELPLUG_UTILS_ROOT/
RPMFILE=$(find -name "openstack-xen-plugins-*.noarch.rpm" -print)
cd xenserver-suppack


# =============================================
# Create neutron rpm file
rm -rf neutron
git clone "$NEUTRON_GITREPO" neutron
cd neutron
git checkout -b mos_neutron "$GITBRANCH"
cd ..

cp -r xenserver-nova-suppack-builder/neutron/* \
      neutron/neutron/plugins/ml2/drivers/openvswitch/agent/xenapi/
cd neutron/neutron/plugins/ml2/drivers/openvswitch/agent/xenapi/contrib
./build-rpm.sh $XS_PLUGIN_VERSION
cd $FUELPLUG_UTILS_ROOT/

NEUTRON_RPMFILE=$(find -name "openstack-neutron-xen-plugins-*.noarch.rpm" -print)


# =============================================
# Create Supplemental pack
rm -rf suppack
mkdir -p suppack

tee buildscript.py << EOF
from xcp.supplementalpack import *
from optparse import OptionParser

parser = OptionParser()
parser.add_option('--pdn', dest="product_name")
parser.add_option('--pdv', dest="product_version")
parser.add_option('--bld', dest="build")
parser.add_option('--out', dest="outdir")
(options, args) = parser.parse_args()

xcp = Requires(originator='xcp', name='main', test='ge',
               product='XenServer', version='$PLATFORM_VERSION',
               build='$XS_BUILD')

setup(originator='xcp', name='xenapi-plugins-$OS_RELEASE', product='XenServer',
      version=options.product_version, build=options.build, vendor='Citrix Systems, Inc.',
      description="OpenStack XenServer Plugins", packages=args, requires=[xcp],
      outdir=options.outdir, output=['iso'])
EOF

python buildscript.py \
--pdn=xenserverplugins \
--pdv=$OS_RELEASE \
--bld=0 \
--out=$FUELPLUG_UTILS_ROOT \
$FUELPLUG_UTILS_ROOT/$RPMFILE \
$FUELPLUG_UTILS_ROOT/$NEUTRON_RPMFILE
