Test Plan for XenServer Fuel Plugin
===================================

XenServer Fuel Plugin
=====================

XenServer Fuel Plugin will help to deploy Mirantis OpenStack using the
XenServer hypervisor to host virtual machines, making all the necessary
changes to the Mirantis OpenStack to use the xenapi Nova compute driver.


Developer’s Specification
=========================

See developers specification in the source code repository at
https://git.openstack.org/openstack/fuel-plugin-xenserver

Limitations
-----------

This version of XenServer Fuel Plugin has not been certified to work with the
Ceilometer, MongoDB or Murano additional services.  Future versions of the
plugin will relax these restrictions.


Test strategy
=============

Acceptance criteria
-------------------

All tests that do not depend on additional services must pass.

Test environment, infrastructure and tools
------------------------------------------

All tests need to be run under a cluster of at least 4 XenServer machines
with 3 physical NICs. As HA and multihost are enabled, a topology of 3
Controller Nodes + 3 Compute Nodes + 1 Storage Node will be recommended to be
created as VMs on XenServer machines. Easy setup and management of those
XenServers and VM Nodes can be achieved using XenCenter and a plugin,
described below, to add an internal management network to VMs.

To simplify setup, the fuel master is also installed on the XenServer hosts
(so XenServer hosts can fully control the network setup), but this is not
required.

While many networking setups are expected to work, the following setup is
used by this test plan:

* eth0 / “Access network”: Used to access the XenServer hosts and the Fuel
Master’s web interface
* eth1 / “Control network”: OpenStack control plane (management and storage),
the PXE network and the public network; all separated by VLAN tags.  The
public network is also on this network, and if a VLAN is required this is
applied by the switch for untagged traffic.
* eth2 / “VLAN network”: This version of the plugin only supports VLAN
segmentation for Neutron networking.  This device carries all of the VLANs to
be used by Neutron for VM traffic.

   .. image:: _static/topology00.png
      :width: 80%

For the hardware configuration see Mirantis OpenStack Planning Guide at
https://docs.mirantis.com/openstack/fuel/fuel-9.0/mos-planning-guide.html

Product compatibility matrix
----------------------------

The plugin is compatible with MOS 9.0 and XenServer versions 6.5 SP1
(with hotfix XS65ESP013) and 7.0, with all hotfixes applied.


Prerequirements
===============

Prepare XenServers
------------------

#. Install and start XenCenter on your Windows PC
#. Add new servers with a common root password in XenCenter
#. Plug three physical NIC to each of all XenServer machines, make sure the
   cabling of all NIC 0 are attached to the ‘access’ network, all NIC 1 to the
   ‘public’ network  and NIC 2 are attached to the isolated, ‘VLAN network’.
   It is recommended to rename these networks using XenCenter to make the
   network topology clear.
#. Add a further network, with a vlan tag that will be used for PXE.

Prepare Fuel Master
-------------------

#. Upload Fuel ISO to a NFS/Samba server and make it accessible to your
   XenServer hosts.
#. Select a XenServer and click “New Storage” button, in the popup window
   check on CIFS/NFS ISO library and input NFS/Samba server path.
#. Create a new VM in XenCenter using the “Other Install Media” template (to
   ensure a HVM domain is created) with and PXE network as eth0 and ‘access’
   network as eth1. In the Console Tab, insert Fuel ISO and install.
#. In fuel menu, enable eth1 with DHCP so the fuel master can be accessed
   over the ‘access’ network.
#. Select Fuel Master in XenCenter and switch to Console tab, login with
   prompted user and password
#. Visit http://ip_of_fuel_master:8000 in browser.


Type of testing
===============

Install XenServer Fuel Plugin
-----------------------------

.. tabularcolumns:: |p{3cm}|p{13cm}|

.. list-table::
   :header-rows: 0

   * - Test Case ID
     - insall_xfp
   * - Description
     - Verify that XenServer Fuel Plugin can be installed into Fuel Master,
       and the new OpenStack release is registered.
   * - Steps
     -
       | ``fuel plugins --install /tmp/fuel-plugin-xenserver-4.0-4.0.0-1.noarch.rpm``
       | ``fuel plugins``
       | ``id | name                  | version | package_version``
       | ``1  | fuel-plugin-xenserver | 4.0.0   | 4.0.0``
   * - Expected Result
     -
       | ``fuel plugins``
       | ``id | name                  | version | package_version``
       | ``1  | fuel-plugin-xenserver | 4.0.0   | 4.0.0``

Prepare Nodes
-------------

.. tabularcolumns:: |p{3cm}|p{13cm}|

.. list-table::
   :header-rows: 0

   * - Test Case ID
     - prepare_nodes
   * - Description
     - Verify all controller/compute/storage nodes are ready for PXE install.
   * - Steps
     -
       #. Create 3 new VMs in XenCenter in different XenServers and name them
          Controller1, Controller2, Controller3
       #. Create 3 new VMs in XenCenter in different XenServers and name them
          Compute1, Compute2, Compute3
       #. Create 1 new VM in XenCenter and name it Storage1
       #. Add ‘PXE’ network as eth0, Public/Management/Storage network as
          eth1 and ‘VLAN network’ as eth2 to each of new VMs created above.

   * - Expected Result
     - All nodes are shown in XenCenter with ‘PXE network’ as eth0 and ‘VLAN
       network’ as eth1.

Install XenCenter HIMN plugin
-----------------------------

.. tabularcolumns:: |p{3cm}|p{13cm}|

.. list-table::
   :header-rows: 0

   * - Test Case ID
     - install_xcp
   * - Description
     - Verify XenCenter HIMN plugin is installed to Windows.
   * - Steps
     -
       #. Download SetupHIMN from http://ca.downloads.xensource.com/OpenStack/Plugins/
       #. Install MSI to your XenCenter
       #. Restart XenCenter
   * - Expected Result
     - Right click on any selected VMs, there will be a menu item “Manage
       internal management network”.

Add Host Internal Management Network to Compute Nodes
-----------------------------------------------------

.. tabularcolumns:: |p{3cm}|p{13cm}|

.. list-table::
   :header-rows: 0

   * - Test Case ID
     - add_himn
   * - Description
     - Verify (or add) Host Internal Management Network is added to all
       Compute Nodes.
   * - Steps
     -
       #. Select Compute1, Compute2, Compute3 in XenCenter
       #. Right click on above nodes and select “Manage internal management
          network” menu.
       #. In the popup window, after status detection, make sure all selected
          Compute nodes are checked on. Click on “Manage internal management
          network” button.
       #. After processing, the status column should be shown as management
          network is added with new generated MAC address
       #. Close the management network window
   * - Expected Result
     - The wizard will report success, however the networks may not be
       visible in XenCenter.

Create an OpenStack environment with XenServer Fuel Plugin
----------------------------------------------------------

.. tabularcolumns:: |p{3cm}|p{13cm}|

.. list-table::
   :header-rows: 0

   * - Test Case ID
     - create_env
   * - Description
     - Verify that an OpenStack environment created with XenServer Fuel
       Plugin can have XenServer options and options of
       hypervisor/network/storage/additional services are disabled.
   * - Steps
     -
       #. Create new OpenStack environment Fuel Web UI and select
          "Mitaka on Ubuntu 14.04” in the OpenStack release
          dropdown list
       #. Check off QEMU and check on XenServer, Network is default to “Neutron
          with VLAN segmentation” and Storage is default to Cinder. Other
          options are disabled.
       #. In Nodes Tab, add all 3 Controller Nodes, 3 Compute Nodes and 1
          Storage Node.
       #. Select all Compute Nodes and click “Configure Interfaces”, drag
          Storage/Management network from default eth0 to eth1, Private
          network to eth2.  Leave PXE on eth0.  No networks should be
          assigned to the final interface.
       #. Select all Controller and Storage Nodes and click “Configure
          Interfaces”, drag Storage/Management network from default eth0 to
          eth1, Private network to eth2.  Leave PXE on eth0.
       #. In Networks Tab, set the vlan tags according to your network
          interfaces previous set and make sure network range will not be
          conflicting with other systems in the same lab. Then click “Verify
          Networks” button.
       #. In the Settings Tab under the side tab “Compute”, input the
          credential applied to all your XenServer hosts.
       #. Click “Deploy Changes” button
   * - Expected Result
     - Deploy of nodes all succeed

Verify hypervisor type
----------------------

.. tabularcolumns:: |p{3cm}|p{13cm}|

.. list-table::
   :header-rows: 0

   * - Test Case ID
     - verify_hypervisor
   * - Description
     - Verify that all hypervisors are identified by OpenStack as ‘xen’.
   * - Steps
     -
       #. Login to Horizon with admin user when OpenStack deployment is
          finished.
       #. Enter into Admin->Hypervisors
   * - Expected Result
     - The Type column should show xen for all hypervisors.

Create guest instances
----------------------

.. tabularcolumns:: |p{3cm}|p{13cm}|

.. list-table::
   :header-rows: 0

   * - Test Case ID
     - create_instances
   * - Description
     - Verify that new environment can create guest instances.
   * - Steps
     -
       #. Create an instance with image of TestVM and flavor of m1.tiny in
          either of Horizon or Controller Node.
       #. Find the instance in XenCenter and switch to Console Tab.
       #. Login with the username and password that prompted in the terminal
          screen.
       #. Ping out to 8.8.8.8
   * - Expected Result
     - Guest instances can ping out.

Verify Fuel Health Checks
-------------------------

.. tabularcolumns:: |p{3cm}|p{13cm}|

.. list-table::
   :header-rows: 0

   * - Test Case ID
     - verify_health_checks
   * - Description
     - Ensure that all applicable health checks pass
   * - Steps
     -
       #. Within the Fuel Master, select the appropriate environment
       #. Run all health checks and wait for completion
   * - Expected Result
     - "Update stack actions: inplace, replace and update whole template"
       is failed because vif hot plug/unplug is not supported by the
       XenServer driver in Mitaka.

Mandatory Tests
===============

Install plugin and deploy environment
-------------------------------------

Covered above.

Modifying env with enabled plugin (removing/adding compute nodes)
-----------------------------------------------------------------

.. tabularcolumns:: |p{3cm}|p{13cm}|

.. list-table::
   :header-rows: 0

   * - Test Case ID
     - modify_env_compute_nodes
   * - Description
     - Adding/removing compute nodes to an existing environment
   * - Steps
     -
       #. Create one more compute following the procedure in step
          prepare_nodes
       #. Add compute node to an existing environment
       #. Redeploy cluster
       #. Run Health Check
       #. Remove a compute node
       #. Redeploy cluster
       #. Run Health Check
   * - Expected Result
     - "Update stack actions: inplace, replace and update whole template"
       is failed because vif hot plug/unplug is not supported by the
       XenServer driver in Mitaka.

Modifying env with enabled plugin (removing/adding controller nodes)
--------------------------------------------------------------------

.. tabularcolumns:: |p{3cm}|p{13cm}|

.. list-table::
   :header-rows: 0

   * - Test Case ID
     - modify_env_controller_nodes
   * - Description
     - Adding/removing controller nodes to an existing environment
   * - Steps
     -
       #. Create one more controller following the procedure in step
          prepare_nodes
       #. Add controller node to an existing environment
       #. Redeploy cluster
       #. Run Health Check
       #. Remove a compute node (not the primary controller node)
       #. Redeploy cluster
       #. Run Health Check
   * - Expected Result
     - "Update stack actions: inplace, replace and update whole template"
       is failed because vif hot plug/unplug is not supported by the
       XenServer driver in Mitaka.

Create mirror and update (setup) of core repos
---------------------------------------------------

.. tabularcolumns:: |p{3cm}|p{13cm}|

.. list-table::
   :header-rows: 0

   * - Test Case ID
     - create_mirror_update_core_repos
   * - Description
     - Fuel create mirror and update (setup) of core repos
   * - Steps
     -
       #. Launch the following command on the Fuel Master node: ``fuel-mirror create -G mos -P ubuntu``
       #. Launch the following command on the Fuel Master node: ``fuel-mirror apply -G mos -P ubuntu -e ENV_ID``, ENV_ID is the id of the deployed cluster
       #. Check if MOS repositories have been changed to local
       #. Run Health Check
   * - Expected Result
     -
       #. Health Checks are passed.
       #. MOS repositories have been changed to local
       #. XenServer Fuel plugin doesn't launch any services, so the check of process PID and status can be skipped

Uninstall of plugin with deployed environment
---------------------------------------------

.. tabularcolumns:: |p{3cm}|p{13cm}|

.. list-table::
   :header-rows: 0

   * - Test Case ID
     - uninstall_plugin_with_deployed_env
   * - Description
     - Verify XenServer Fuel Plugin cannot be uninstalled before all
       dependant environments are removed.
   * - Steps
     - ``fuel plugins --remove fuel-plugin-xenserver==4.0.0``
   * - Expected Result
     - 400 Client Error: Bad Request (Can't delete plugin which is enabled
       for some environment.)

Uninstall of plugin
-------------------

.. tabularcolumns:: |p{3cm}|p{13cm}|

.. list-table::
   :header-rows: 0

   * - Test Case ID
     - uninstall_plugin
   * - Description
     - Verify XenServer Fuel Plugin can be uninstalled as well as XenServer
       OpenStack release after all dependant environments are removed.
   * - Steps
     - | ``fuel plugins --remove fuel-plugin-xenserver==4.0.0``
       | ``fuel plugins``
   * - Expected Result
     - Plugin is removed.

Appendix
========

* XenServer Fuel Plugin Repository: https://git.openstack.org/cgit/openstack/fuel-plugin-xenserver
* XenCenter HIMN Plugin GitHub: https://github.com/citrix-openstack/xencenter-himn-plugin
* Plugin download server: http://ca.downloads.xensource.com/OpenStack/Plugins/

Revision history
================

.. list-table::
   :header-rows: 1

   * - Version
     - Revision Date
     - Editor
     - Comment
   * - 1.0
     - 18.09.2015
     - John Hua (john.hua@citrix.com)
     - First draft.
   * - 2.0
     - 18.11.2015
     - John Hua (john.hua@citrix.com)
     - Revised for Fuel 7.0
   * - 3.0
     - 22.03.2016
     - John Hua (john.hua@citrix.com)
     - Revised for Fuel 8.0
   * - 3.1
     - 22.03.2016
     - John Hua (john.hua@citrix.com)
     - Revised for plugin 4.0.0
   * - 4.0
     - 12.08.2016
     - John Hua (john.hua@citrix.com)
     - Revised for Fuel 9.0
