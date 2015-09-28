Copyright 2015 Citrix Systems

Fuel Plugin for Xenserver
==============================

The XenServer plugin provides the ability to use Xenserver as the
hypervisor for Mirantis OpenStack.

Compatible with Fuel version 6.1.

Problem description
===================

There is currently no supported way for Citrix Xenserver customers to
use Mirantis OpenStack in their environments.  Further, Fuel does not
provide sufficient flexibility to add a new hypervisor option to the
wizard, meaning that any users of Citrix XenServer who wish to
manually configure Fuel are required to select an incorrect hypervisor
then made post-install changes to switch them over to using XenServer.

Proposed change
===============

Unfortunately the Fuel Plugin architecture is not sufficiently
flexible to allow a plugin to add a new hypervisor option to the
wizard.  Therefore, this plugin will provide a new Release definition
which can be used to automatically install with XenServer.

Alternatives
------------

N/A - the aim is to implement a Fuel plugin.

Data model impact
-----------------

None, although a new Release will be installed into the existing model.

REST API impact
---------------

None.

Upgrade impact
--------------

When upgrading the Fuel Master node to Fuel Version higher than 6.1,
plugin compatibility should be checked, and a new plugin installed if
necessary.

Security impact
---------------

None.

Notifications impact
--------------------

None.

Other end user impact
---------------------

Once the plugin is installed, the user can select the XenServer
Release and then configure the access credentials in the Settings tab
of the Fuel Web UI.

Performance Impact
------------------

None.

Plugin impact
-------------

The plugin will:

* Install a customized Release definition (based on Ubuntu) which will
  only be usable to install an environment with XenServer

* Connect to XenServer over a new network (an internal management
  network)

 * Require the network is already set up on the host (to be
   documented)

 * Set up the network to use DHCP, which will allow access to
   XenServer over a fixed link-local IP 169.254.0.1

* Configure Nova to the XenAPI driver and use this interface to
  connect

* Configure the Compute VM to provide a NATed interface to Dom0 so
  that storage traffic (for example, when downloading the initial
  image) which originates in Dom0 can be routed through the Compute VM
  as a gateway

Other deployer impact
---------------------

The plugin requries the Compute nodes to be created on the XenServer
hosts as XenServer's Nova plugin requires access to the virtual disks
as they are being created.

Developer impact
----------------

None.

Infrastructure impact
---------------------

None.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  John Hua <john.hua@citrix.com> (developer)

Other contributors:
  Bob Ball <bob.ball@citrix.com> (developer, reviewer)

Work Items
----------

* Manual integration of XenServer with Fuel 6.1.

* Implement the XenServer plugin.

* Test XenServer plugin.

* Create the documentation.

Dependencies
============

* Fuel 6.1.

Testing
=======

* Prepare a test plan.

* Test the plugin according to the test plan.

Documentation Impact
====================

* Create the following documentation:

 * User Guide.

 * Test Plan.

 * Test Report.

References
==========

* Citrix XenServer official documentation: http://docs.vmd.citrix.com/XenServer

* What is Xen? by Xen.org: http://xen.org/files/Marketing/WhatisXen.pdf

* Xen Hypervisor project: http://www.xenproject.org/developers/teams/hypervisor.html

* Xapi project: http://www.xenproject.org/developers/teams/xapi.html

* Further XenServer and OpenStack information: http://wiki.openstack.org/XenServer
