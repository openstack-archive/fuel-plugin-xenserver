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
DEPLOYMENT_SCRIPT_ROOT=$(dirname $FUELPLUG_UTILS_ROOT)
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
cd $FUELPLUG_UTILS_ROOT/xenserver-suppack/
RPMFILE=$(find -name "openstack-xen-plugins-*.noarch.rpm" -print)


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
cd $FUELPLUG_UTILS_ROOT/xenserver-suppack/
NEUTRON_RPMFILE=$(find -name "openstack-neutron-xen-plugins-*.noarch.rpm" -print)


# =============================================
# Create Supplemental pack
rm -rf suppack
mkdir suppack

DDKROOT=$(mktemp -d)

wget -qO - "$DDK_ROOT_URL" | sudo tar -xzf - -C "$DDKROOT"

sudo mkdir $DDKROOT/mnt/host
sudo mount --bind $(pwd) $DDKROOT/mnt/host

sudo tee $DDKROOT/buildscript.py << EOF
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

sudo chroot $DDKROOT python buildscript.py \
--pdn=xenserverplugins \
--pdv=$OS_RELEASE \
--bld=0 \
--out=/mnt/host/suppack \
/mnt/host/$RPMFILE \
/mnt/host/$NEUTRON_RPMFILE

# Cleanup
sudo umount $DDKROOT/mnt/host
sudo rm -rf "$DDKROOT"
