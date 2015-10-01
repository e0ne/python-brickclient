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

from os_brick.initiator import connector
from oslo_concurrency import processutils
import socket


def _get_my_ip():
    try:
        csock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        csock.connect(('8.8.8.8', 80))
        (addr, port) = csock.getsockname()
        csock.close()
        return addr
    except socket.error:
        return None


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
        # TODO(e0ne): use oslo.rootwrap
        root_helper = 'sudo'
        return connector.InitiatorConnector.factory(protocol, root_helper,
                                                    driver=driver,
                                                    execute=execute,
                                                    use_multipath=
                                                    use_multipath,
                                                    device_scan_attempts=
                                                    device_scan_attempts,
                                                    *args, **kwargs)

    def get_connector(self):
        # TODO(e0ne): use oslo.rootwrap
        # TODO(e0ne): multipath support
        root_helper = 'sudo'
        conn_prop = connector.get_connector_properties(root_helper,
                                                       _get_my_ip(),
                                                       multipath=False,
                                                       enforce_multipath=False)
        return conn_prop

    def attach(self, client, volume_id, hostname):
        # TODO(e0ne): use oslo.rootwrap
        # TODO(e0ne): multipath support
        root_helper = 'sudo'
        conn_prop = connector.get_connector_properties(root_helper,
                                                       _get_my_ip(),
                                                       multipath=False,
                                                       enforce_multipath=False)
        connection = client.volumes.initialize_connection(volume_id, conn_prop)
        brick_connector = self._brick_get_connector(
            connection['driver_volume_type'])

        device_info = brick_connector.connect_volume(connection['data'])
        client.volumes.attach(volume_id, None, None, host_name=hostname)
        return device_info

    def detach(self, client, volume_id):
        # TODO(e0ne): use oslo.rootwrap
        # TODO(e0ne): multipath support
        conn_prop = connector.get_connector_properties('sudo',
                                                       _get_my_ip(),
                                                       multipath=False,
                                                       enforce_multipath=False)
        connection = client.volumes.initialize_connection(volume_id, conn_prop)
        brick_connector = self._brick_get_connector(
            connection['driver_volume_type'])

        brick_connector.disconnect_volume(connection['data'], None)
        client.volumes.terminate_connection(volume_id, conn_prop)
        client.volumes.detach(volume_id)
