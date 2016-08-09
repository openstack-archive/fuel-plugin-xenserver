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

xcp = Requires(originator='xcp',
               name='main',
               test='ge',
               product='XenServer',
               version=options.product_version,
               build=options.build)


setup(originator='xcp',
      name=options.product_name,
      product='XenServer',
      version=options.product_version,
      build=options.build,
      vendor='Citrix Systems, Inc.',
      description=options.description,
      packages=args,
      requires=[xcp],
      outdir=options.outdir,
      output=['iso'])
