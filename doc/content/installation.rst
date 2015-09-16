
Installation Guide
==================

Install the Plugin
------------------

To install the XenServer Fuel plugin:

#. Download it from the `xensource download server`_
#. Copy the *rpm* file to the Fuel Master node:
   ::

      [root@home ~]# scp xenserver-fuel-plugin-0.4-0.4.0-1.noarch.rpm root@fuel-master:/tmp

#. Log into Fuel Master node and install the plugin using the
   `Fuel CLI`_:

   ::

      [root@fuel-master ~]# fuel plugins --install xenserver-fuel-plugin-0.4-0.4.0-1.noarch.rpm

#. Verify that the plugin is installed correctly:
   ::

      [root@fuel-master ~]# fuel plugins
      id | name    | version | package_version
      ---|---------|---------|----------------
      2  | xenserver-fuel-plugin | 0.4.0   | 2.0.0

      [root@fuel-master ~]# fuel rel
      id | name                                    | state     | operating_system | version
      ---|-----------------------------------------|-----------|------------------|-------------
      2  | Juno on Ubuntu 14.04.1                  | available | Ubuntu           | 2014.2.2-6.1
      9  | Juno+Citrix XenServer on Ubuntu 14.04.1 | available | Ubuntu           | 2014.2.2-6.1
      1  | Juno on CentOS 6.5                      | available | CentOS           | 2014.2.2-6.1


.. _xensource download server: http://ca.downloads.xensource.com/OpenStack/Mirantis/
.. _Fuel CLI: https://docs.mirantis.com/openstack/fuel/fuel-6.1/user-guide.html#using-fuel-cli