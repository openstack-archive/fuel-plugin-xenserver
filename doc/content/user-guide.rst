User Guide
==========

Intro
-----

XenServer Fuel Plugin will help to deploy Mirantis OpenStack over XenServer hosts and make sure they work as xenapi rather than qemu.


Usage
-----

- Create a new environment with the Fuel UI wizard. Select "Juno+Citrix XenServer on Ubuntu 14.04.1" from OpenStack Release dropdown list. At the moment you will see most of options are disabled in the wizard.

   .. image:: /raw/master/doc/images/fmwizard00.png
      :width: 100%

- Create new VMs in XenCenter for all roles and use `xencenter-himn-plugin <https://github.com/citrix-openstack/xencenter-himn-plugin>`_ to add management network to those supposed to run as Compute Nodes.

- Add new VMs to the new environment according to `Fuel User Guide <https://docs.mirantis.com/openstack/fuel/fuel-6.1/user-guide.html#add-nodes-to-the-environment>`_ and configure them properly. A typical topology of 1 controller node + 3 compute nodes + 1 storage node is recommended.

- Go to Settings tab and scroll down to "XenServer Plugin" section. You need to input the common access credentials to all XenServers that previously are used to create new VMs.

   .. image:: /raw/master/doc/images/fmsetting00.png
      :width: 100%

- Click "Deploy Changes" button

- After deployment is done, you will see in Horizon that all hypervisors are xen.

   .. image:: /raw/master/doc/images/fmhorizon00.png
      :width: 100%