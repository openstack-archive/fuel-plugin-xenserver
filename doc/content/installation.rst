
Installation Guide
==================

Install the Plugin
------------------

To install the XenServer Fuel plugin:

#. Download it from the `Fuel Plugins Catalog`_
#. Copy the *rpm* file to the Fuel Master node:
   ::

      [root@home ~]# scp fuel-plugin-xenserver-1.0-1.0.0-1.noarch.rpm root@fuel-master:/tmp

#. Log into Fuel Master node and install the plugin using the
   `Fuel CLI <https://docs.mirantis.com/openstack/fuel/fuel-6.1/user-guide.html#using-fuel-cli>`_:

   ::

      [root@fuel-master ~]# fuel plugins --install /tmp/fuel-plugin-xenserver-1.0-1.0.0-1.noarch.rpm

#. Verify that the plugin is installed correctly:
   ::

     [root@fuel-master ~]# fuel plugins
     id | name                  | version | package_version
     ---|-----------------------|---------|----------------
     9  | fuel-plugin-xenserver | 1.0.0   | 2.0.0

Add Management Network tool
---------------------------

#. Download the `HIMN tool <http://ca.downloads.xensource.com/OpenStack/Plugins/>`_

#. Stop XenCenter if it is running

#. Install the HIMN tool

#. Re-start XenCenter

.. _Fuel Plugins Catalog: https://www.mirantis.com/products/openstack-drivers-and-plugins/fuel-plugins/
