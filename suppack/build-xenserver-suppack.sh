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
BUILDROOT=${FUELPLUG_UTILS_ROOT}/build
rm -rf $BUILDROOT
mkdir -p $BUILDROOT && cd $BUILDROOT


# =============================================
# Configurable items

# OpenStack release
OS_RELEASE=${1:-"mitaka"}

HOST_PRODUCT=${2:-"XenServer"}
PLATFORM_VERSION=${3:-"1.9"}
XS_BUILD=${4:-"90233c"}

# nova and neutron xenserver dom0 plugin version
XS_PLUGIN_VERSION=${5:-"2015.1"}

# branch info
GITBRANCH="stable/$OS_RELEASE"

# repository info
NOVA_GITREPO="https://git.openstack.org/openstack/nova"
NEUTRON_GITREPO="https://git.openstack.org/openstack/neutron"
RPM_BUILDER_REPO="https://github.com/citrix-openstack/xenserver-nova-suppack-builder"

# Update system and install dependencies
export DEBIAN_FRONTEND=noninteractive

# =============================================
# Install suppack builder
RPM_ROOT=http://coltrane.uk.xensource.com/usr/groups/release/XenServer-7.x/XS-7.0/RTM-125380/binary-packages/RPMS/domain0/RPMS/noarch
wget $RPM_ROOT/supp-pack-build-2.1.0-xs55.noarch.rpm -O supp-pack-build.rpm
wget $RPM_ROOT/xcp-python-libs-1.9.0-159.noarch.rpm -O xcp-python-libs.rpm

# Don't install the RPM as we may not have root.
rpm2cpio supp-pack-build.rpm | cpio -idm
rpm2cpio xcp-python-libs.rpm | cpio -idm
# Work around dodgy requirements for xcp.supplementalpack.setup function
# Note that either root or a virtual env is needed here. venvs are better :)
cp -f usr/bin/* .

# If we are in a venv, we can potentially work with genisoimage and not mkisofs
venv_prefix=$(python -c 'import sys; print sys.prefix if hasattr(sys, "real_prefix") else ""')
set +e
mkisofs=`which mkisofs`
set -e
if [ -n "$venv_prefix" -a -z "$mkisofs" ]; then
    # Some systems (e.g. debian) only have genisofsimage.
    set +e
    genisoimage=`which genisoimage`
    set -e
    [ -n "$genisoimage" ] && ln -s $genisoimage $venv_prefix/bin/mkisofs
fi

# Now we must have mkisofs as the supp pack builder just invokes it
which mkisofs || (echo "mkisofs not installed" && exit 1)

# =============================================
# Check out rpm packaging repo
rm -rf xenserver-nova-suppack-builder
git clone -b $GITBRANCH --single-branch --depth 1 $RPM_BUILDER_REPO xenserver-nova-suppack-builder


# =============================================
# Create nova rpm file
rm -rf nova
git clone -b $GITBRANCH --single-branch --depth 1 "$NOVA_GITREPO" nova
pushd nova
# patch xenhost as this file is not merged into this release
cp $FUELPLUG_UTILS_ROOT/../plugin_source/deployment_scripts/patchset/xenhost plugins/xenserver/xenapi/etc/xapi.d/plugins/
# patch bandwidth as this file is not merged into this release
cp $FUELPLUG_UTILS_ROOT/../plugin_source/deployment_scripts/patchset/bandwidth plugins/xenserver/xenapi/etc/xapi.d/plugins/
popd

cp -r xenserver-nova-suppack-builder/plugins/xenserver/xenapi/* nova/plugins/xenserver/xenapi/
pushd nova/plugins/xenserver/xenapi/contrib
./build-rpm.sh $XS_PLUGIN_VERSION
popd

RPMFILE=$(find $FUELPLUG_UTILS_ROOT -name "openstack-xen-plugins-*.noarch.rpm" -print)


# =============================================
# Create neutron rpm file
rm -rf neutron
git clone -b $GITBRANCH --single-branch --depth 1 "$NEUTRON_GITREPO" neutron
pushd neutron
cp $FUELPLUG_UTILS_ROOT/../plugin_source/deployment_scripts/patchset/netwrap neutron/plugins/ml2/drivers/openvswitch/agent/xenapi/etc/xapi.d/plugins/
popd

cp -r xenserver-nova-suppack-builder/neutron/* \
      neutron/neutron/plugins/ml2/drivers/openvswitch/agent/xenapi/
pushd neutron/neutron/plugins/ml2/drivers/openvswitch/agent/xenapi/contrib
./build-rpm.sh $XS_PLUGIN_VERSION
popd

NEUTRON_RPMFILE=$(find $FUELPLUG_UTILS_ROOT -name "openstack-neutron-xen-plugins-*.noarch.rpm" -print)

# =============================================
# Find conntrack-tools related RPMs
EXTRA_RPMS=""
EXTRA_RPMS="$EXTRA_RPMS $(find $FUELPLUG_UTILS_ROOT -name "conntrack-tools-*.rpm" -print)"
EXTRA_RPMS="$EXTRA_RPMS $(find $FUELPLUG_UTILS_ROOT -name "libnetfilter_cthelper-*.rpm" -print)"
EXTRA_RPMS="$EXTRA_RPMS $(find $FUELPLUG_UTILS_ROOT -name "libnetfilter_cttimeout-*.rpm" -print)"
EXTRA_RPMS="$EXTRA_RPMS $(find $FUELPLUG_UTILS_ROOT -name "libnetfilter_queue-*.rpm" -print)"


# =============================================
# Create Supplemental pack
#rm -rf suppack
#mkdir -p suppack

tee buildscript.py << EOF
import sys
sys.path.append('$BUILDROOT/usr/lib/python2.7/site-packages')
from xcp.supplementalpack import *
from optparse import OptionParser

parser = OptionParser()
parser.add_option('--pdn', dest="product_name")
parser.add_option('--pdv', dest="product_version")
parser.add_option('--desc', dest="description")
parser.add_option('--bld', dest="build")
parser.add_option('--out', dest="outdir")
(options, args) = parser.parse_args()

xcp = Requires(originator='xcp', name='main', test='ge',
               product='$HOST_PRODUCT', version=options.product_version,
               build=options.build)


setup(originator='xcp', name=options.product_name, product='$HOST_PRODUCT',
      version=options.product_version, build=options.build, vendor='',
      description=options.description, packages=args, requires=[xcp],
      outdir=options.outdir, output=['iso'])
EOF

python buildscript.py \
--pdn=xenapi-plugins-$OS_RELEASE \
--pdv=$PLATFORM_VERSION \
--desc="OpenStack XenServer Plugins" \
--bld=0 \
--out=$FUELPLUG_UTILS_ROOT \
$RPMFILE \
$NEUTRON_RPMFILE

python buildscript.py \
--pdn=conntrack-tools \
--pdv=$PLATFORM_VERSION \
--desc="XenServer Dom0 conntrack-tools" \
--bld=0 \
--out=$FUELPLUG_UTILS_ROOT \
$EXTRA_RPMS
