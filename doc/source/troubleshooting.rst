Troubleshooting
===============

#. Logging

   In addition to the Astute log, XenServer Fuel Plugin has its own log under
   /var/log/fuel-plugin-xenserver on all Compute and Controller nodes.

   Besides HIMN tool mentioned in Installation Guide also has its own log
   under ``%LOCALAPPDATA%/Temp/XCHIMN.log``.

   You can upload issued logs to https://cis.citrix.com or send to support if
   they are requested. `Writing Good Bug Reports for XenServer`_ might be a
   good reference to follow.

#. XenServer hotfixes

   If you are using XenServer 6.5, please install SP1 and all hotfixes before
   attempting to deploy.

.. _Writing Good Bug Reports for XenServer: https://www.citrix.com/blogs/2012/07/16/writing-good-bug-reports-for-xenserver/
