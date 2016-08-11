# build-xenserver-suppack.sh

This script is used to build iso for XenServer Dom0 xapi plugin.

It will build both Nova and Neutron Dom0 plugin RPM packages firstly,
and then make them in one ISO.


## usage:

#####./build-xenserver-suppack.sh OS_RELEASE PLATFORM_VERSION XS_BUILD XS_PLUGIN_VERSION

* OS_RELEASE: OpenStack branch that's used for building this plugin

* PLATFORM_VERSION: Xen cloud platform version which can be used for this plugin

* XS_BUILD: XenServer build number

* XS_PLUGIN_VERSION: OpenStack XenServer Dom0 plguin version


*NOTE: If no input parameters given, default values are used*

*OS_RELEASE: mitaka

*PLATFORM_VERSION: 1.9

*XS_BUILD: 90233c

*XS_PLUGIN_VERSION: 2015.1
