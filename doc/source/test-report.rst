Test Report for XenServer Fuel Plugin
=====================================

Revision history
================

.. tabularcolumns:: |p{1.5cm}|p{2.5cm}|p{7cm}|p{4.5cm}|

.. list-table::
   :header-rows: 1

   * - Version
     - Revision Date
     - Editor
     - Comment
   * - 1.0
     - 25.09.2015
     - John Hua(john.hua@citrix.com)
     - First draft.
   * - 2.0
     - 8.11.2015
     - John Hua(john.hua@citrix.com)
     - Revised for Mirantis Fuel 7.0
   * - 3.0
     - 13.04.2016
     - John_Hua(john.hua@citrix.com)
       Jianghua_Wang(jianghua.wang@citrix.com)
     - Revised for Mirantis Fuel 8.0
   * - 3.1
     - 19.04.2016
     - John Hua(john.hua@citrix.com)
     - Rewrite in RST

Document purpose
================

This document provides test run results for the XenServer Fuel Plugin version 3.0.0 on Mirantis OpenStack 8.0.

Test environment
================

The following is the hardware configuration for target nodes used for verification. For other things, just follow the test plan.

.. list-table::
   :header-rows: 1

   * - Node Type
     - vCPU
     - Memory
     - Disk
   * - Controller
     - 4
     - 6GB
     - 80GB
   * - Compute
     - 4
     - 4GB
     - 60GB
   * - Storage
     - 4
     - 4GB
     - 60GB

Test coverage and metrics
-------------------------

* Test Coverage – 100%
* Tests Passed – 100%
* Tests Failed – 0%

Test results summary
====================

Type of testing
===============

System Testing
--------------

.. list-table::
   :header-rows: 1

   * - Parameter
     - Value
   * - Total quantity of executed test cases
     - 12
   * - Total quantity of not executed test cases
     - 0
   * - Quantity of automated test cases
     - 0
   * - Quantity of not automated test cases
     - 0

Detailed test run results
-------------------------

.. tabularcolumns:: |p{1cm}|p{4cm}|p{1.2cm}|p{1.2cm}|p{1.2cm}|p{7cm}|

.. list-table::
   :header-rows: 1

   * - #
     - Test case ID
     - Passed
     - Failed
     - Skipped
     - Comment
   * - 1
     - Install XenServer Fuel Plugin
     - Yes
     -
     -
     -
   * - 2
     - Prepare Nodes
     - Yes
     -
     -
     -
   * - 3
     - Install XenCenter HIMN plugin
     - Yes
     -
     -
     -
   * - 4
     - Add Host Internal Management Network to Compute Nodes
     - Yes
     -
     -
     -
   * - 5
     - Create an OpenStack environment with XenServer Fuel Plugin
     - Yes
     -
     -
     -
   * - 6
     - Verify hypervisor type
     - Yes
     -
     -
     -
   * - 7
     - Create guest instances
     - Yes
     -
     -
     -
   * - 8
     - Verify Fuel Health Checks
     - Yes
     -
     -
     -
   * - 9
     - Add/Remove compute node
     - Yes
     -
     -
     - Removing a compute node will cause “Sanity tests-Check that required services are running” fail. “Some nova services have not been started.. Please refer to OpenStack logs for more details.”
   * - 10
     - Add/Remove controller  node
     - Yes
     -
     -
     - Removing a controller node will cause “Sanity tests-Check that required services are running” fail. “Some nova services have not been started.. Please refer to OpenStack logs for more details.”
   * - 11
     - Uninstall of plugin with deployed environment
     - Yes
     -
     -
     -
   * - 12
     - Uninstall of plugin
     - Yes
     -
     -
     -
   * - Total
     -
     - 12
     - 0
     - 0
     -
   * - Total,%
     -
     - 100
     - 0
     - 0
     -

Known issues
============

No issues were found during the testing
