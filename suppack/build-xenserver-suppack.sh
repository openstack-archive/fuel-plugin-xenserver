#!/bin/bash

set -eux

# =============================================
# Usage of this script:
# ./build-xenserver-suppack.sh os-release hypervisor-name xs-plugin-version key
# Or
# ./build-xenserver-suppack.sh
#
# You can provide explict input parameters or you can use the default ones:
#   OpenStack release
#   Hypervisor name
#   XenServer OpenStack plugin version
#   Key for building supplemental packages
#   Keyfile for building supplemental packages
#
# Prerequisite:
#   For Dundee:
#     No
#   For Ely:
#     1. Secret key is imported to the VM which is use for building suppack
#     2. Public keyfile is downloaded to this folder in the building VM
#     3. Below packages should be installed in advance:
#          expect-5.45-14.el7_1.x86_64
#          libarchive-3.1.2-7.el7.x86_64
#          rpm-sign-4.11.3-17.el7.x86_64


THIS_FILE=$(readlink -f $0)
FUELPLUG_UTILS_ROOT=$(dirname $THIS_FILE)
BUILDROOT=${FUELPLUG_UTILS_ROOT}/build
SUPPACK_CREEDENCE=${FUELPLUG_UTILS_ROOT}/xcp_1.9.0
SUPPACK_DUNDEE=${FUELPLUG_UTILS_ROOT}/xcp_2.1.0
SUPPACK_ELY=${FUELPLUG_UTILS_ROOT}/xcp_2.2.0
rm -rf $BUILDROOT $SUPPACK_CREEDENCE $SUPPACK_DUNDEE $SUPPACK_ELY
mkdir -p $SUPPACK_CREEDENCE
mkdir -p $SUPPACK_DUNDEE
mkdir -p $SUPPACK_ELY
mkdir -p $BUILDROOT && cd $BUILDROOT


# =============================================
# Configurable items

# OpenStack release
OS_RELEASE=${1:-"mitaka"}

HYPERVISOR_NAME=${2:-"XenServer"}

# nova and neutron xenserver dom0 plugin version
XS_PLUGIN_VERSION=${3:-"13.0.0"}

# key of the public/secret OpenStack GPG key
SUPPACK_KEY=${4:-"Citrix OpenStack (XenServer Updates) <openstack@citrix.com>"}

# keyfile
SUPPACK_KEYFILE=${5:-"RPM-GPG-KEY-XS-OPENSTACK"}

# branch info
GITBRANCH="origin/stable/$OS_RELEASE"

# repository info
NOVA_GITREPO="https://git.openstack.org/openstack/nova"
NEUTRON_GITREPO="https://git.openstack.org/openstack/neutron"
RPM_BUILDER_REPO="https://github.com/citrix-openstack/xenserver-nova-suppack-builder"

# Update system and install dependencies
export DEBIAN_FRONTEND=noninteractive

# =============================================
# Install suppack builder for Dundee (XCP 2.1.0)
RPM_ROOT=http://coltrane.uk.xensource.com/usr/groups/release/XenServer-7.x/XS-7.0/RTM-125380/binary-packages/RPMS/domain0/RPMS/noarch
wget $RPM_ROOT/supp-pack-build-2.1.0-xs55.noarch.rpm -O supp-pack-build.rpm
wget $RPM_ROOT/xcp-python-libs-1.9.0-159.noarch.rpm -O xcp-python-libs.rpm

# Don't install the RPM as we may not have root.
rpm2cpio supp-pack-build.rpm | cpio -idm
rpm2cpio xcp-python-libs.rpm | cpio -idm

# ==============================================
# Install suppack builder for Ely (XCP 2.2.0)
RPM_ROOT=http://coltrane.uk.xensource.com/release/XenServer-7.x/XS-7.1/RC/137005.signed/binary-packages/RPMS/domain0/RPMS/noarch/
wget $RPM_ROOT/python-libarchive-c-2.5-1.el7.centos.noarch.rpm -O python-libarchive.rpm
wget $RPM_ROOT/update-package-1.1.2-1.noarch.rpm -O update-package.rpm

rpm2cpio python-libarchive.rpm | cpio -idm
rpm2cpio update-package.rpm | cpio -idm

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
git clone $RPM_BUILDER_REPO xenserver-nova-suppack-builder
pushd xenserver-nova-suppack-builder
git checkout -b mos_suppack_builder "$GITBRANCH"
popd


# =============================================
# Create nova rpm file
rm -rf nova
git clone "$NOVA_GITREPO" nova
pushd nova
git checkout -b mos_nova "$GITBRANCH"
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
git clone "$NEUTRON_GITREPO" neutron
pushd neutron
git checkout -b mos_neutron "$GITBRANCH"
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
# Create Supplemental pack for Creedence and Dundee

tee buildscript.py << EOF
import sys
sys.path.append('$BUILDROOT/usr/lib/python2.7/site-packages')
from xcp.supplementalpack import *
from optparse import OptionParser

parser = OptionParser()
parser.add_option('--pdn', dest="product_name")
parser.add_option('--pdv', dest="product_version")
parser.add_option('--hvn', dest="hypervisor_name")
parser.add_option('--desc', dest="description")
parser.add_option('--bld', dest="build")
parser.add_option('--out', dest="outdir")
(options, args) = parser.parse_args()

xcp = Requires(originator='xcp', name='main', test='ge',
               product=options.hypervisor_name, version=options.product_version,
               build=options.build)


setup(originator='xcp', name=options.product_name, product=options.hypervisor_name,
      version=options.product_version, build=options.build, vendor='',
      description=options.description, packages=args, requires=[xcp],
      outdir=options.outdir, output=['iso'])
EOF

python buildscript.py \
--pdn=xenapi-plugins-$OS_RELEASE \
--pdv="1.9.0" \
--hvn="$HYPERVISOR_NAME" \
--desc="OpenStack Plugins" \
--bld=0 \
--out=$SUPPACK_CREEDENCE \
$RPMFILE \
$NEUTRON_RPMFILE

python buildscript.py \
--pdn=xenapi-plugins-$OS_RELEASE \
--pdv="2.1.0" \
--hvn="$HYPERVISOR_NAME" \
--desc="OpenStack Plugins" \
--bld=0 \
--out=$SUPPACK_DUNDEE \
$RPMFILE \
$NEUTRON_RPMFILE \
$EXTRA_RPMS


# =============================================
# Create Supplemental pack for Ely

# KEY for building supplemental pack
SUPPACK_KEY="Citrix OpenStack (XenServer Updates) <openstack@citrix.com>"
CONNTRACK_UUID=`uuidgen`
XENAPI_PLUGIN_UUID=`uuidgen`

tee buildscript_ely.py << EOF
import sys
sys.path.append('$BUILDROOT/usr/lib/python2.7/site-packages')
from pkg_resources import load_entry_point

if __name__ == '__main__':
    sys.exit(
        load_entry_point('update-package', 'console_scripts', 'build-update')()
    )
EOF

python buildscript_ely.py \
--uuid $XENAPI_PLUGIN_UUID \
-l "openstack-xenapi-plugins" \
-v 1.0 \
-d "OpenStack plugins supplemental pack" \
-o $SUPPACK_ELY/xenapi-plugins-$OS_RELEASE.iso \
-k "$SUPPACK_KEY" \
--keyfile "$FUELPLUG_UTILS_ROOT/$SUPPACK_KEYFILE" --no-passphrase \
$RPMFILE $NEUTRON_RPMFILE $EXTRA_RPMS
