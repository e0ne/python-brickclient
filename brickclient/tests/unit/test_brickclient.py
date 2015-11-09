# -*- coding: utf-8 -*-

# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""
test_brickclient
----------------------------------

Tests for `brickclient` module.
"""

import mock

from cinderclient import exceptions as cinder_exceptions
from oslotest import base

from brickclient import client
from brickclient import exceptions


class TestBrickClient(base.BaseTestCase):
    def setUp(self):
        super(TestBrickClient, self).setUp()
        self.volume_id = '3d96b134-75bd-492b-8372-330455cae38f'
        self.hostname = 'hostname'
        self.client = client.Client()

    @mock.patch('brickclient.utils.get_my_ip')
    @mock.patch('brickclient.utils.get_root_helper')
    @mock.patch('os_brick.initiator.connector.get_connector_properties')
    def test_get_connector(self, mock_connector, mock_root_helper,
                           mock_my_ip):
        mock_root_helper.return_value = 'root-helper'
        mock_my_ip.return_value = '1.0.0.0'

        self.client.get_connector()
        mock_connector.assert_called_with('root-helper', '1.0.0.0',
                                          enforce_multipath=False,
                                          multipath=False)

    @mock.patch('brickclient.utils.get_my_ip')
    @mock.patch('brickclient.utils.get_root_helper')
    @mock.patch('os_brick.initiator.connector.get_connector_properties')
    def test_get_connector_with_multipath(self, mock_connector,
                                          mock_root_helper, mock_my_ip):
        mock_root_helper.return_value = 'root-helper'
        mock_my_ip.return_value = '1.0.0.0'

        self.client.get_connector(True, True)
        mock_connector.assert_called_with('root-helper', '1.0.0.0',
                                          enforce_multipath=True,
                                          multipath=True)

    def test_attach_reserve_fail(self):
        self.client.volumes_client = mock.MagicMock()
        self.client.volumes_client.reserve.side_effect = (
            cinder_exceptions.BadRequest(400))
        self.assertRaises(exceptions.BadRequest,
                          self.client.attach,
                          'vol_id', 'hostname')

    def _init_fake_cinderclient(self, protocol):
        # Init fake cinderclient
        self.mock_vc = mock.MagicMock()
        conn_data = {'key': 'value'}
        connection = {'driver_volume_type': protocol, 'data': conn_data}
        self.mock_vc.volumes.initialize_connection.return_value = connection
        self.client.volumes_client = self.mock_vc
        return connection

    def _init_fake_os_brick(self, mock_conn_prop):
        # Init fakes for os-brick
        conn_props = mock.Mock()
        mock_conn_prop.return_value = conn_props
        mock_connector = mock.MagicMock()
        mock_connect = mock.Mock()
        mock_connector.return_value = mock_connect
        self.client._brick_get_connector = mock_connector
        mock_connect.connect_volume = mock.Mock()

        return conn_props, mock_connect

    @mock.patch('os_brick.initiator.connector.get_connector_properties')
    def test_attach_iscsi(self, mock_conn_prop):
        connection = self._init_fake_cinderclient('iscsi')
        conn_props, mock_connect = self._init_fake_os_brick(mock_conn_prop)

        self.client.attach(self.volume_id, self.hostname)
        self.mock_vc.volumes.initialize_connection.assert_called_with(
            self.volume_id, conn_props)
        mock_connect.connect_volume.assert_called_with(connection['data'])

    @mock.patch('os_brick.initiator.connector.get_connector_properties')
    def test_attach_rbd(self, mock_conn_prop):
        connection = self._init_fake_cinderclient('rbd')
        conn_props, mock_connect = self._init_fake_os_brick(mock_conn_prop)

        self.client._attach_rbd_volume = mock.Mock()
        self.client.attach(self.volume_id, self.hostname)
        self.mock_vc.volumes.initialize_connection.assert_called_with(
            self.volume_id, conn_props)
        self.client._attach_rbd_volume.assert_called_with(connection)
        mock_connect.connect_volume.assert_called_with(connection['data'])

    def test_begin_detaching_fail(self):
        self.client.volumes_client = mock.MagicMock()
        self.client.volumes_client.begin_detaching.side_effect = (
            cinder_exceptions.BadRequest(400))
        self.assertRaises(exceptions.BadRequest,
                          self.client.detach,
                          'vol_id')

    @mock.patch('os_brick.initiator.connector.get_connector_properties')
    def test_detach_iscsi(self, mock_conn_prop):
        connection = self._init_fake_cinderclient('iscsi')
        conn_props, m_connect = self._init_fake_os_brick(mock_conn_prop)

        self.client.detach(self.volume_id)
        self.mock_vc.volumes.initialize_connection.assert_called_with(
            self.volume_id, conn_props)
        m_connect.disconnect_volume.assert_called_with(connection['data'], {})

    @mock.patch('os_brick.initiator.connector.get_connector_properties')
    def test_detach_rbd(self, mock_conn_prop):
        connection = self._init_fake_cinderclient('rbd')
        conn_props, mock_connect = self._init_fake_os_brick(mock_conn_prop)
        self.client._detach_rbd_volume = mock.Mock()

        self.client.detach(self.volume_id)
        self.mock_vc.volumes.initialize_connection.assert_called_with(
            self.volume_id, conn_props)
        mock_connect.disconnect_volume.assert_called_with(
            connection['data'], {})
        self.client._detach_rbd_volume.assert_called_with(connection)

    @mock.patch('os_brick.initiator.connector.get_connector_properties')
    def test_detach_nfs(self, mock_conn_prop):
        connection = self._init_fake_cinderclient('nfs')
        conn_props, mock_connect = self._init_fake_os_brick(mock_conn_prop)
        self.client._detach_nfs_volume = mock.Mock()

        self.client.detach(self.volume_id)
        self.mock_vc.volumes.initialize_connection.assert_called_with(
            self.volume_id, conn_props)
        mock_connect.disconnect_volume.assert_called_with(
            connection['data'], {})
        self.client._detach_nfs_volume.assert_called_with(connection)

    @mock.patch('brickclient.utils.safe_execute')
    def test__attach_rbd_volume(self, mock_execute):
        connection = {'data': {'name': 'pool/volume'}}
        self.client._attach_rbd_volume(connection)

        mock_execute.assert_called_with(['rbd', 'map', 'volume',
                                         '--pool', 'pool'])

    @mock.patch('brickclient.utils.safe_execute')
    def test__detach_rbd_volume(self, mock_execute):
        connection = {'data': {'name': 'pool/volume'}}
        self.client._detach_rbd_volume(connection)

        dev_name = '/dev/rbd/pool/volume'
        mock_execute.assert_called_with(['rbd', 'unmap', dev_name])

    @mock.patch('brickclient.utils.safe_execute')
    def test__detach_nfs_volume(self, mock_execute):
        connection = {'data': {'export': 'export_path'}}
        self.client._detach_nfs_volume(connection)
        mock_execute.assert_called_with(['umount', 'export_path'])
