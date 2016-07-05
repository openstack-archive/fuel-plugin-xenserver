XenServer Plugin for Fuel 9.0
=============================

Requirements
------------

========================= ============================
Requirement               Version/Comment
========================= ============================
Fuel                      9.0
XenServer                 7.0
XenServer plugin for Fuel @PLUGIN_VERSION@
========================= ============================

* This plugin will not install XenServer or configure the Virtual
  Machines used to run the OpenStack services.  Installation of
  XenServer and configuration of these Virtual Machines must be
  performed manually.
* File-based storage (EXT / NFS) must be used.  If using local storage
  then select "Enable thin provisioning" at host installation time
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

