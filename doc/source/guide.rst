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

   - Physical machines with two ethernet devices:

    - eth0 / “Access network”: Used to access the XenServer hosts and Fuel Master during setup.
    - eth1 / “VLAN network”: Carries all traffic during setup + use of OpenStack.  Untagged packets are tagged at the switch to ensure isolation from eth0.

   - Two virtual networks

    - VLAN 'A' on eth1 / “PXE network”: Used for node bootstrapping.
    - VLAN 'B' on eth1 / "br100": Used to give connectivity between VM and router.

4. To simplify the setup, the fuel master can also be installed on the XenServer hosts (so XenServer hosts can fully control the network setup), but this is not required.
One example deployment, shown below, makes use of VLAN 19 for the "PXE network" and provides an isolated network for eth1 by tagging any untagged traffic at the switch with VLAN 237

   .. image:: _static/topology00.png
      :width: 80%


Select Environment
------------------

#. Create a new environment with the Fuel UI wizard. Select "Kilo+Citrix XenServer on Ubuntu 14.04" from OpenStack Release dropdown list. At the moment you will see most of options are disabled in the wizard.

   .. image:: _static/fmwizard00.png
      :width: 80%

#. Create new VMs in XenCenter for the compute nodes

#. Select all Compute virtual Machines, Right click on one of the
   Virtual Machines and select "Add Management Network"

#. Use the dialog to add the Host Internal Management
   Network to the compute virtual machines

    .. image:: _static/HIMN_dialog.jpg
      :width: 80%

#. Add new VMs to the new environment according to `Fuel User Guide <https://docs.mirantis.com/openstack/fuel/fuel-7.0/user-guide.html#add-nodes-to-the-environment>`_ and configure them properly. A typical topology of 1 controller node + 3 compute nodes + 1 storage node is recommended.

#. Go to Settings tab and scroll down to "XenServer Plugin" section. You need to input the common access credentials to all XenServers that previously are used to create new VMs.

   .. image:: _static/fmsetting00.png
      :width: 80%

#. If the XenServer host already has compatible Nova plugins installed, untick the checkbox to install the supplemental packs.  In normal cases, the XenServer host will not have compatible Nova plugins installed, so leave the checkbox enabled


Finish environment configuration
--------------------------------

#. Run `network verification check <https://docs.mirantis.com/openstack/fuel/fuel-7.0/user-guide.html#verify-networks>`_

#. Press `Deploy button <https://docs.mirantis.com/openstack/fuel/fuel-7.0/user-guide.html#deploy-changes>`_ to once you are done with environment configuration.

#. After deployment is done, you will see in Horizon that all hypervisors are xen.

   .. image:: _static/fmhorizon00.png
      :width: 80%
