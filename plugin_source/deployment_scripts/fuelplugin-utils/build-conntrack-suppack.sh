#!/bin/bash

set -eux

PLATFORM_VERSION=${1:-"1.9"}
XS_BUILD=${2:-"90233c"}

DDK_ROOT_URL="http://copper.eng.hq.xensource.com/builds/ddk-xs6_2.tgz"

THIS_FILE=$(readlink -f $0)
FUELPLUG_UTILS_ROOT=$(dirname $THIS_FILE)
DEPLOYMENT_SCRIPT_ROOT=$(dirname $FUELPLUG_UTILS_ROOT)

cd $DEPLOYMENT_SCRIPT_ROOT/conntrack-rpms
rm -rf $DEPLOYMENT_SCRIPT_ROOT/conntrack-rpms/suppack
mkdir $DEPLOYMENT_SCRIPT_ROOT/conntrack-rpms/suppack
RPM_CONNTRACKTOOLS=$(find -name "conntrack-tools-*.rpm" -print)
RPM_CTHELPER=$(find -name "libnetfilter_cthelper-*.rpm" -print)
RPM_CTTIMEOUT=$(find -name "libnetfilter_cttimeout-*.rpm" -print)
RPM_QUEUE=$(find -name "libnetfilter_queue-*.rpm" -print)

DDKROOT=$(mktemp -d)
wget -qO - "$DDK_ROOT_URL" | sudo tar -xzf - -C "$DDKROOT"

sudo cp $FUELPLUG_UTILS_ROOT/buildscript.py $DDKROOT/
sudo mkdir $DDKROOT/mnt/host
sudo mkdir $DDKROOT/mnt/host/suppack 
sudo mount --bind $DEPLOYMENT_SCRIPT_ROOT/conntrack-rpms $DDKROOT/mnt/host

sudo chroot $DDKROOT python buildscript.py \
--pdn=conntrack-tools \
--pdv=$PLATFORM_VERSION \
--desc="Dom0 conntrack-tools" \
--bld=$XS_BUILD \
--out=/mnt/host/suppack \
/mnt/host/$RPM_QUEUE \
/mnt/host/$RPM_CTTIMEOUT \
/mnt/host/$RPM_CTHELPER \
/mnt/host/$RPM_CONNTRACKTOOLS

# Cleanup
sudo umount $DDKROOT/mnt/host
sudo rm -rf "$DDKROOT"
