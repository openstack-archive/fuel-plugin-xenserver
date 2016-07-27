# build-xenserver-suppack.sh

This script is used to build iso for XenServer Dom0 xapi plugin.

It will build both Nova and Neutron Dom0 plugin RPM packages firstly,
and then make them in one ISO.


## usage:

#####./build-xenserver-suppack.sh $xcp-version $xs-build $os-git-branch $os-plugin-version

* xcp-version: Xen cloud platform version which can be used for this plugin

* xs-build: XenServer build number

* os-git-branch: OpenStack branch that's used for building this plugin

* os-plugin-version: OpenStack XenServer Dom0 plguin version



*NOTE: If no input parameters given, default values are used*

*xcp-version: 1.9.0

*xs-build: 90233c*

*os-git-branch: stable/liberty*

*os-plugin-version: 2015.1*


