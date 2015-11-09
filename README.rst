==================
python-brickclient
==================

OpenStack Cinder brick client for local volume attachement


Features
--------

* Attach volume to localhost
* Detach volume
* Get volume connector information


Limitations
-----------
Current version supports only iSCSI, RBD and NFS protocols.

Dependencies
------------

Depends on Cinder driver's protocol, python-brickclient could require following
packages::

* open-iscsi - for volume attachment via iSCSI
* ceph-common - for volume attachment via iSCSI (Ceph)
* nfs-common - for volume attachment using NFS protocol

For any other imformation, refer to the parent project, Cinder:
  https://github.com/openstack/cinder

* License: Apache License, Version 2.0
* Source: http://git.openstack.org/cgit/openstack/python-brickclient
* Bugs: http://bugs.launchpad.net/cinder
