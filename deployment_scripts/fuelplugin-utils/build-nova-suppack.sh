set -eux

cd ../..

PWD=`pwd`

mkdir -p nova-suppack && cd nova-suppack

GITREPO=${1:-"https://git.openstack.org/openstack/nova"}
DDK_ROOT_URL=${2:-"http://copper.eng.hq.xensource.com/builds/ddk-xs6_2.tgz"}
GITBRANCH=${3:-"stable/kilo"}


# Update system and install dependencies
export DEBIAN_FRONTEND=noninteractive

#sudo apt-get update
#sudo apt-get -qy upgrade
#sudo apt-get install -qy git rpm

# Check out rpm packaging
[ -e xenserver-nova-suppack-builder ] || git clone https://github.com/citrix-openstack/xenserver-nova-suppack-builder

# Create rpm file

## Check out Nova
if ! [ -e nova ]; then
    git clone "$GITREPO" nova
    cd nova
    git fetch origin "$GITBRANCH"
    git checkout FETCH_HEAD
    cd ..
fi

cd nova
NOVA_VER=$(
{
    grep -e "^PLUGIN_VERSION" plugins/xenserver/xenapi/etc/xapi.d/plugins/nova_plugin_version;
    echo "print PLUGIN_VERSION"
} | python
)
cd ..

cp -r xenserver-nova-suppack-builder/plugins/* nova/plugins/

cd nova/plugins/xenserver/xenapi/contrib
#./inject-key.sh ~/domzero_public_key
./build-rpm.sh
cd ~/workspace

RPMFILE=$(find -name "openstack-xen-plugins*.noarch.rpm" -print -quit)

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

xs = Requires(originator='xs', name='main', test='ge',
               product='XenServer', version='5.6.100',
               build='39265p')

setup(originator='xs', name='novaplugins', product='XenServer',
      version=options.product_version, build=options.build, vendor='Citrix Systems, Inc.',
      description="OpenStack Nova Plugins", packages=args, requires=[xs],
      outdir=options.outdir, output=['iso'])
EOF

sudo chroot $DDKROOT python buildscript.py \
--pdn=nova-plugins \
--pdv="$NOVA_VER" \
--bld=0 \
--out=/mnt/host/suppack \
/mnt/host/$RPMFILE

# Cleanup
sudo umount $DDKROOT/mnt/host
sudo rm -rf "$DDKROOT"

