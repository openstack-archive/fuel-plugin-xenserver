
Installation Guide
==================

Install the Plugin
------------------

To install the XenServer Fuel plugin:

#. Download it from the `Fuel Plugins Catalog`_
#. Copy the *rpm* file to the Fuel Master node:
   ::

      [root@home ~]# scp fuel-plugin-xenserver-3.1-3.1.0-1.noarch.rpm root@fuel:/tmp

#. Log into Fuel Master node and install the plugin using the
   `Fuel CLI <http://docs.openstack.org/developer/fuel-docs/userdocs/fuel-user-guide/cli.html>`_:

   ::

      [root@fuel-master ~]# fuel plugins --install /tmp/fuel-plugin-xenserver-3.1-3.1.0-1.noarch.rpm

#. Verify that the plugin is installed correctly:
   ::

     [root@fuel-master ~]# fuel plugins
     id | name                  | version | package_version
     ---|-----------------------|---------|----------------
     1  | fuel-plugin-xenserver | 3.1.0   | 4.0.0

Add Management Network tool
---------------------------

#. Download the HIMN tool `xencenter-himn-plugin <https://github.com/citrix-openstack/xencenter-himn-plugin>`_

#. Stop XenCenter if it is running

#. Install the HIMN tool

#. Re-start XenCenter

.. _Fuel Plugins Catalog: https://www.mirantis.com/validated-solution-integrations/fuel-plugins/
