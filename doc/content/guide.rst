Xenserver Fuel Plugin User Guide
================================

Once the Fuel XenServer plugin has been installed (following
`Installation Guide`_), you can create *OpenStack* environments that
use XenServer as the underlying hypervisor

Select Environment
------------------

#. Create a new environment with the Fuel UI wizard. Select "Juno+Citrix XenServer on Ubuntu 14.04.1" from OpenStack Release dropdown list. At the moment you will see most of options are disabled in the wizard.

   .. image:: images/fmwizard00.png
      :width: 80%

#. Create new VMs in XenCenter for the compute nodes

#. Select all Compute virtual Machines, Right click on one of the
   Virtual Machines and select "Add Management Network"

#. Use the dialog to add the Host Internal Management
   Network to the compute virtual machines

    .. image:: images/HIMN_dialog.jpg
      :width: 80%

#. Add new VMs to the new environment according to `Fuel User Guide <https://docs.mirantis.com/openstack/fuel/fuel-6.1/user-guide.html#add-nodes-to-the-environment>`_ and configure them properly. A typical topology of 1 controller node + 3 compute nodes + 1 storage node is recommended.

#. Go to Settings tab and scroll down to "XenServer Plugin" section. You need to input the common access credentials to all XenServers that previously are used to create new VMs.

   .. image:: images/fmsetting00.png
      :width: 80%


Finish environment configuration
--------------------------------

#. Run `network verification check <https://docs.mirantis.com/openstack/fuel/fuel-6.1/user-guide.html#verify-networks>`_

#. Press `Deploy button <https://docs.mirantis.com/openstack/fuel/fuel-6.1/user-guide.html#deploy-changes>`_ to once you are done with environment configuration.

#. After deployment is done, you will see in Horizon that all hypervisors are xen.

   .. image:: images/fmhorizon00.png
      :width: 80%
