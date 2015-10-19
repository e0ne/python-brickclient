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

    def get_connector(self):
        # TODO(e0ne): multipath support
        conn_prop = connector.get_connector_properties(utils.get_root_helper(),
                                                       utils.get_my_ip(),
                                                       multipath=False,
                                                       enforce_multipath=False)
        return conn_prop

    def attach(self, client, volume_id, hostname):
        # TODO(e0ne): multipath support
        conn_prop = connector.get_connector_properties(utils.get_root_helper(),
                                                       utils.get_my_ip(),
                                                       multipath=False,
                                                       enforce_multipath=False)
        connection = client.volumes.initialize_connection(volume_id, conn_prop)

        protocol = connection['driver_volume_type']
        protocol = protocol.upper()
        brick_connector = self._brick_get_connector(
            protocol)

        device_info = brick_connector.connect_volume(connection['data'])
        if protocol == 'RBD':
            # TODO(e0ne): move to attach_rbd_volume() function
            # TODO(e0ne): multipath support
            pool, volume = connection['data']['name'].split('/')
            cmd = ['rbd', 'map', volume, '--pool', pool]
            processutils.execute(*cmd, root_helper=utils.get_root_helper(),
                                 run_as_root=True)
        client.volumes.attach(volume_id, None, None, host_name=hostname)
        return device_info

    def detach(self, client, volume_id):
        # TODO(e0ne): multipath support
        conn_prop = connector.get_connector_properties(utils.get_root_helper(),
                                                       utils.get_my_ip(),
                                                       multipath=False,
                                                       enforce_multipath=False)
        connection = client.volumes.initialize_connection(volume_id, conn_prop)
        brick_connector = self._brick_get_connector(
            connection['driver_volume_type'])

        # TODO(e0ne): use real device info from params
        device_info = {}
        brick_connector.disconnect_volume(connection['data'], device_info)
        protocol = connection['driver_volume_type']
        protocol = protocol.upper()
        if protocol == 'RBD':
            # TODO(e0ne): move to detach_rbd_volume() function
            # TODO(e0ne): multipath support
            pool, volume = connection['data']['name'].split('/')
            dev_name = '/dev/rbd/{pool}/{volume}'.format(pool=pool,
                                                         volume=volume)
            cmd = ['rbd', 'unmap', dev_name]
            processutils.execute(*cmd, root_helper=utils.get_root_helper(),
                                 run_as_root=True)
        client.volumes.terminate_connection(volume_id, conn_prop)
        client.volumes.detach(volume_id)
