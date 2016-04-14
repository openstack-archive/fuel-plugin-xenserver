XenServer Fuel Plugin
=====================

XenServer Fuel Plugin will help to deploy Mirantis OpenStack using the XenServer hypervisor to host virtual machines, making all the necessary changes to the Mirantis OpenStack to use the xenapi Nova compute driver.


Developer’s Specification
=========================

See developers specification in the source code repository at https://git.openstack.org/openstack/fuel-plugin-xenserver

Limitations
-----------

This version of XenServer Fuel Plugin has not been certified to work with the Ceilometer, MongoDB or Murano additional services.  Future versions of the plugin will relax these restrictions.


Test strategy
=============

Acceptance criteria
-------------------

All tests that do not depend on additional services must pass.

Test environment, infrastructure and tools
------------------------------------------

All tests need to be run under a cluster of at least 4 XenServer machines with 3 physical NICs. As HA and multihost are enabled, a topology of 3 Controller Nodes + 3 Compute Nodes + 1 Storage Node will be recommended to be created as VMs on XenServer machines. Easy setup and management of those XenServers and VM Nodes can be achieved using XenCenter and a plugin, described below, to add an internal management network to VMs.

To simplify setup, the fuel master is also installed on the XenServer hosts (so XenServer hosts can fully control the network setup), but this is not required.

While many networking setups are expected to work, the following setup is used by this test plan:

* eth0 / “Access network”: Used to access the XenServer hosts and the Fuel Master’s web interface
* eth1 / “Control network”: OpenStack control plane (management and storage), the PXE network and the public network; all separated by VLAN tags.  The public network is also on this network, and if a VLAN is required this is applied by the switch for untagged traffic.
* eth2 / “VLAN network”: This version of the plugin only supports VLAN segmentation for Neutron networking.  This device carries all of the VLANs to be used by Neutron for VM traffic.

   .. image:: _static/topology00.png
      :width: 80%

Product compatibility matrix
----------------------------

The plugin is compatible with MOS 8.0 and XenServer 6.5 SP1, with all hotfixes applied (Especially hotfix XS65ESP1013).


Prerequirements
===============

Prepare XenServers
------------------

#. Install and start XenCenter on your Windows PC
#. Add new servers with a common root password in XenCenter
#. Plug three physical NIC to each of all XenServer machines, make sure the cabling of all NIC 0 are attached to the ‘access’ network, all NIC 1 to the ‘public’ network  and NIC 2 are attached to the isolated, ‘VLAN network’.  It is recommended to rename these networks using XenCenter to make the network topology clear.
#. Add a further network, with a vlan tag that will be used for PXE.

Prepare Fuel Master
-------------------

#. Upload Fuel ISO to a NFS/Samba server and make it accessible to your XenServer hosts.
#. Select a XenServer and click “New Storage” button, in the popup window check on CIFS/NFS ISO library and input NFS/Samba server path.
#. Create a new VM in XenCenter using the “Other Install Media” template (to ensure a HVM domain is created) with and PXE network as eth0 and ‘access’ network as eth1. In the Console Tab, insert Fuel ISO and install.
#. In fuel menu, enable eth1 with DHCP so the fuel master can be accessed over the ‘access’ network.
#. Select Fuel Master in XenCenter and switch to Console tab, login with prompted user and password
#. Visit http://ip_of_fuel_master:8000 in browser.


Type of testing
===============

Install XenServer Fuel Plugin
-----------------------------

.. list-table::
   :header-rows: 0

   * - Test Case ID
     - ``insall_xfp``
   * - Description
     - ``Verify that XenServer Fuel Plugin can be installed into Fuel Master,``
       ``and the new OpenStack release is registered.``
   * - Steps
     -
       ``[root@fuel-master ~]# fuel plugins``
       ``id | name                  | version | package_version``
       ``---|-----------------------|---------|----------------``
       ``9  | fuel-plugin-xenserver | 3.0.0   | 3.0.0``
   * - Expected Result
     -
       ``fuel plugins``
       ``id | name                  | version | package_version``
       ``---|-----------------------|---------|----------------``
       ``2  | fuel-plugin-xenserver | 3.0.0   | 3.0.0``
       ``fuel rel``
       ``id | name                                     | state``
       ``| operating_system | version``
       ``---|------------------------------------------|-------------``
       ``|------------------|------------``
       ``2  | Liberty on Ubuntu 14.04                  | available``
       ``| Ubuntu           | liberty-8.0``
       ``3  | Liberty+Citrix XenServer on Ubuntu 14.04 | available``
       ``| Ubuntu           | liberty-8.0``
       ``1  | Liberty on CentOS 6.5                    | unavailable``
       ``| CentOS           | liberty-8.0``

Prepare Nodes
-------------

.. list-table::
   :header-rows: 0

   * - Test Case ID
     - prepare_nodes
   * - Description
     - Verify all controller/compute/storage nodes are ready for PXE install.
   * - Steps
       Create 3 new VMs in XenCenter in different XenServers and name them Controller1, Controller2, Controller3
       Create 3 new VMs in XenCenter in different XenServers and name them Compute1, Compute2, Compute3
       Create 1 new VM in XenCenter and name it Storage1
       Add ‘PXE’ network as eth0, Public/Management/Storage network as eth1 and ‘VLAN network’ as eth2 to each of new VMs created above.
   * - Expected Result
     - All nodes are shown in XenCenter with ‘PXE network’ as eth0 and ‘VLAN network’ as eth1.