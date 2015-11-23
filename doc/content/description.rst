XenServer Plugin for Fuel 7.0
=============================

XenServer is an Open Source hypervisor with commercial support options
provided by Citrix.  This plugin provides a new Release definition in
Mirantis OpenStack to allow easy installation of production
environments based on XenServer with Fuel.

XenServer is freely available from `xenserver.org
<http://xenserver.org/open-source-virtualization-download.html>`_ and
can also be downloaded directly from `citrix.com
<http://www.citrix.com/downloads/xenserver.html>`_ if you have a My
Citrix account.

Documentation for XenServer can be found on `docs.vmd.citrix.com
<http://docs.vmd.citrix.com/XenServer/6.5.0/1.0/en_gb/>`_ and for how
XenServer works within OpenStack at docs.openstack.org in the
`OpenStack Configuration Reference
<http://docs.openstack.org/juno/config-reference/content/introduction-to-xen.html>`_
guide

Requirements
------------

========================= ============================
Requirement               Version/Comment
========================= ============================
Fuel                      7.0
XenServer                 6.5 SP1 + Hotfix XS65ESP1013
XenServer plugin for Fuel 2.0.0
========================= ============================

* This plugin will not install XenServer or configure the Virtual
  Machines used to run the OpenStack services.  Installation of
  XenServer and configuration of these Virtual Machines must be
  performed manually.
* Each hypervisor must have the same access credentials as Fuel
  does not support per-node settings.
* One Virtual Machine, which will be used to run Nova (the compute
  node), must exist on each hypervisor.  This must be created as an
  HVM guest (in XenCenter, use the "Other Install Media" template) and
  configured to PXE boot from the PXE network used by Fuel.
* XenCenter is expected to be used to configure VMs, and is required
  by the HIMN tool in the installation steps
* Network 'br100' must exist on the XenServer hypervisors.  This
  network will be added automatically to Virtual Machines and the
  compute nodes must have access to this network.

Limitations
-----------

* The plugin is **only** compatible with OpenStack environments deployed with
  **Nova Network** as network configuration in the environment configuration
  options. The plugin will disable incompatible options when the XenServer
  Release is selected.

