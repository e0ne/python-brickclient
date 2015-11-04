# Copyright (c) 2011 OpenStack Foundation
# Copyright 2010 Jacob Kaplan-Moss
# Copyright 2011 Piston Cloud Computing, Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
"""
brickclient implementation
"""

from __future__ import print_function

from brickclient import utils
from os_brick.initiator import connector
from oslo_concurrency import processutils


class Client(object):
    def __init__(self, volumes_client=None):
        self.volumes_client = volumes_client

    def _brick_get_connector(self, protocol, driver=None,
                             execute=processutils.execute,
                             use_multipath=False,
                             device_scan_attempts=3,
                             *args, **kwargs):
        """Wrapper to get a brick connector object.
        This automatically populates the required protocol as well
        as the root_helper needed to execute commands.
        """
        return connector.InitiatorConnector.factory(protocol,
                                                    utils.get_root_helper(),
                                                    driver=driver,
                                                    execute=execute,
                                                    use_multipath=
                                                    use_multipath,
                                                    device_scan_attempts=
                                                    device_scan_attempts,
                                                    *args, **kwargs)

    def get_connector(self, multipath=False, enforce_multipath=False):
        conn_prop = connector.get_connector_properties(utils.get_root_helper(),
                                                       utils.get_my_ip(),
                                                       multipath=multipath,
                                                       enforce_multipath=
                                                       enforce_multipath)
        return conn_prop

    def attach(self, volume_id, hostname, multipath=False,
               enforce_multipath=False):
        conn_prop = connector.get_connector_properties(utils.get_root_helper(),
                                                       utils.get_my_ip(),
                                                       multipath=multipath,
                                                       enforce_multipath=
                                                       enforce_multipath)
        connection = self.volumes_client.volumes.initialize_connection(
            volume_id, conn_prop)

        protocol = connection['driver_volume_type']
        protocol = protocol.upper()
        nfs_mount_point_base = connection.get('mount_point_base')
        brick_connector = self._brick_get_connector(
            protocol, nfs_mount_point_base=nfs_mount_point_base)

        device_info = brick_connector.connect_volume(connection['data'])
        if protocol == 'RBD':
            # TODO(e0ne): move to attach_rbd_volume() function
            pool, volume = connection['data']['name'].split('/')
            cmd = ['rbd', 'map', volume, '--pool', pool]
            processutils.execute(*cmd, root_helper=utils.get_root_helper(),
                                 run_as_root=True)
        self.volumes_client.volumes.attach(volume_id, None, None,
                                           host_name=hostname)
        return device_info

    def detach(self, volume_id, multipath=False, enforce_multipath=False):
        conn_prop = connector.get_connector_properties(utils.get_root_helper(),
                                                       utils.get_my_ip(),
                                                       multipath=multipath,
                                                       enforce_multipath=
                                                       enforce_multipath)
        connection = self.volumes_client.volumes.initialize_connection(
            volume_id, conn_prop)
        nfs_mount_point_base = connection.get('mount_point_base')
        brick_connector = self._brick_get_connector(
            connection['driver_volume_type'],
            nfs_mount_point_base=nfs_mount_point_base)

        # TODO(e0ne): use real device info from params
        device_info = {}
        brick_connector.disconnect_volume(connection['data'], device_info)
        protocol = connection['driver_volume_type']
        protocol = protocol.upper()
        if protocol == 'RBD':
            # TODO(e0ne): move to detach_rbd_volume() function
            pool, volume = connection['data']['name'].split('/')
            dev_name = '/dev/rbd/{pool}/{volume}'.format(pool=pool,
                                                         volume=volume)
            cmd = ['rbd', 'unmap', dev_name]
            processutils.execute(*cmd,
                                 root_helper=utils.get_root_helper(),
                                 run_as_root=True)
        elif protocol == 'NFS':
            nfs_share = connection['data']['export']
            cmd = ['umount', nfs_share]
            processutils.execute(*cmd, root_helper=utils.get_root_helper(),
                                 run_as_root=True)
        self.volumes_client.volumes.terminate_connection(volume_id, conn_prop)
        self.volumes_client.volumes.detach(volume_id)
