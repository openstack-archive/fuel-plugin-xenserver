Xenserver Fuel Plugin User Guide
================================

Once the Fuel XenServer plugin has been installed (following
`Installation Guide`_), you can create *OpenStack* environments that
use XenServer as the underlying hypervisor

Prepare infrastructure
----------------------

1. Everyone will have different infrastructure requirements. The additional requirements placed by XenServer are:

   - Compute nodes must be run as a Virtual Machine, with one VM per XenServer hypervisor

   - Ensure that the connectivity through to this virtual machine is the same as all other service nodes, as with standard Mirantis OpenStack setups

   - An internal network is added by the instructions below, to provide communication between the host and the compute VM.

   - Other service nodes (e.g. storage node) can also be created as virtual machines, but this is not required

2. Download and install XenServer 6.5 with SP1, Hotfix XS65ESP1013 and HIMN tool, a XenServer plugin, as install guide mentioned. Use it for future VM creation and network configuration.

3. While many networking setups are expected to work, the following setup is known to work:

  - Physical machines with three ethernet devices:

    - eth0 / “Access network”: Used to access the XenServer hosts and the Fuel Master’s web interface
    - eth1 / “Control network”: OpenStack control plane (management and storage), the PXE network and the public network; all separated by VLAN tags.  The public network is also on this network, and if a VLAN is required this is applied by the switch for untagged traffic.
    - eth2 / “VLAN network”: This version of the plugin only supports VLAN segmentation for Neutron networking.  This device carries all of the VLANs to be used by Neutron for VM traffic.

  - One virtual network

    - VLAN 'pxe' on eth1 / “PXE network”: Used for node bootstrapping.

4. To simplify the setup, the fuel master can also be installed on the XenServer hosts (so XenServer hosts can fully control the network setup), but this is not required.
One example deployment is shown below.

   .. image:: _static/topology00.png
      :width: 100%


Select Environment
------------------

#. Create a new environment with the Fuel UI wizard. Select "Liberty on Ubuntu 14.04" from OpenStack Release dropdown list, check off QEMU-KVM and check on XenServer. At the moment you will see most of options are disabled in the wizard.

   .. image:: _static/fmwizard00.png
      :width: 100%

#. Create new VMs in XenCenter for the compute nodes

#. Select all Compute virtual Machines, Right click on one of the
   Virtual Machines and select "Manage internal management network"

#. Use the dialog to add the Host Internal Management
   Network to the compute virtual machines

    .. image:: _static/HIMN_dialog.jpg
      :width: 100%

#. Add new VMs to the new environment according to `Fuel User Guide <http://docs.openstack.org/developer/fuel-docs/userdocs/fuel-user-guide/configure-environment/add-nodes.html>`_ and configure them properly. A typical topology of 3 controller nodes + 3 compute nodes + 1 storage node is recommended.

#. Go to Settings tab and "Compute" section. You need to input the common access credentials to all XenServers that previously are used to create new VMs.

   .. image:: _static/fmsetting00.png
      :width: 100%

#. If the XenServer host already has compatible Nova plugins installed, untick the checkbox to install the supplemental packs.  In normal cases, the XenServer host will not have compatible Nova plugins installed, so leave the checkbox enabled


Finish environment configuration
--------------------------------

#. Run `network verification check <http://docs.openstack.org/developer/fuel-docs/userdocs/fuel-user-guide/configure-environment/verify-networks.html>`_

#. Press `Deploy button <http://docs.openstack.org/developer/fuel-docs/userdocs/fuel-user-guide/deploy-environment/deploy-changes.html>`_ to once you are done with environment configuration.

#. After deployment is done, you will see in Horizon that all hypervisors are xen.

   .. image:: _static/fmhorizon00.png
      :width: 100%
