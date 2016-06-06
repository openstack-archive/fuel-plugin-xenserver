XenServer Plugin for Fuel 8.0
=============================

Requirements
------------

========================= ============================
Requirement               Version/Comment
========================= ============================
Fuel                      8.0
XenServer                 6.5 SP1 + Hotfix XS65ESP1013
XenServer plugin for Fuel 3.1.1
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

Limitations
-----------

* The plugin is **only** compatible with OpenStack environments deployed with
  **Neutron with VLAN segmentation** as network configuration in the
  environment configuration options. The plugin will disable incompatible
  options when the XenServer Release is selected.

