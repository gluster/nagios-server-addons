#!/usr/bin/python
# Copyright 2014 Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA
#

from plugins import discovery, server_utils
from plugins.config_generator import GLUSTER_AUTO_CONFIG
from plugins.config_generator import HOST_SERVICES
from plugins.config_generator import VOL_NAME
from plugins.config_generator import CHANGE_MODE
from plugins.config_generator import CHANGE_MODE_ADD
from plugins.config_generator import CHANGE_MODE_REMOVE
from plugins.config_generator import CHANGE_MODE_UPDATE
from plugins.config_generator import NOTES
from glusternagios.glustercli import HostStatus
from testrunner import PluginsTestCase as TestCaseBase


class TestDiscovery(TestCaseBase):
    def _mockExecNRPECommand(self, host, command, arguments=None,
                             timeout=None):
        if command == "discover_volume_list":
            return self._getVolumeNames()
        elif command == "discover_volume_info":
            return self._getVolumeInfo(arguments[0])
        elif command == "discoverpeers":
            return self._getPeers()
        elif command == "discoverhostparams":
            return self._getHostParams(host)

    def _getLogicalComponents(self):
        result = {}
        result['volumes'] = []
        result['volumes'].append(self._getVolumeInfo("V1")['V1'])
        result['volumes'].append(self._getVolumeInfo("V2")['V2'])
        return result

    def _getVolumeInfo(self, volumeName):
        result = {}
        if volumeName == "V1":
            volume = {"bricks": [{"brickpath": "/bricks/v1-1",
                                  "hostUuid": "0000-1111",
                                  "hostip": "172.16.53.1"}],
                      "type": "DISTRIBUTE", "name": "V1"}

        elif volumeName == "V2":
            volume = {"bricks": [{"brickpath": "/bricks/v2-1",
                                  "hostUuid": "0000-1112",
                                  "hostip": "172.16.53.2"}],
                      "type": "DISTRIBUTE", "name": "V2"}
        result[volume['name']] = volume
        return result

    def _getVolumeNames(self):
        result = {}
        result['V1'] = {"type": "DISTRIBUTE", "name": "V1"}
        result['V2'] = {"type": "DISTRIBUTE", "name": "V2"}
        return result

    def _getPeers(self):
        result = []
        result.append({"hostip": "lo", "uuid": "0000-1111",
                       'status': HostStatus.CONNECTED})
        result.append({"hostip": "172.16.53.2", "uuid": "0000-1112",
                       'status': HostStatus.CONNECTED})
        return result

    def _getHostParams(self, hostip):
        if hostip == "172.16.53.1":
            return {"hostname": "node-1"}
        elif hostip == "172.16.53.2":
            return {"hostname": "node-2"}

    def _verifyClusterData(self, clusterdata, clusterName, host):

        self.assertEqual(clusterdata['name'], clusterName)
        self.assertEqual(clusterdata['hosts'][0]['hostip'], host)
        for host in clusterdata['hosts']:
            hostDetails = self._getHostParams(host['hostip'])
            self.assertEqual(host['hostname'], hostDetails['hostname'])
            self.assertEqual(len(host['bricks']), 1)
        volumes = self._getLogicalComponents()['volumes']
        self.assertEqual(len(clusterdata['volumes']), len(volumes))

        for i in range(len(volumes)):
            self._verifyVolume(volumes[i], clusterdata['volumes'][i])

    def _verifyVolume(self, expected, actual):
        self.assertEqual(expected['name'], actual['name'])
        self.assertEqual(expected['type'], actual['type'])

    # Method to test the discoverCluster() method
    def testDiscoverCluster(self):
        server_utils.execNRPECommand = self._mockExecNRPECommand
        clusterName = "test-cluster"
        host = "172.16.53.1"
        clusterdata = discovery.discoverCluster(host,
                                                clusterName,
                                                timeout=None)
        self._verifyClusterData(clusterdata, clusterName, host)

    def mockFindDeletedServices(self, hostConfig):
        return [{'service_description': 'Brick - /bricks/v1-deleted',
                CHANGE_MODE: CHANGE_MODE_REMOVE}]

    def mockGetServiceConfig(self, serviceDesc, hostName):
        if serviceDesc == 'Brick - /bricks/v1-no-change':
            return self.fillServiceModel({'service_description': serviceDesc,
                                          'host_name': hostName,
                                          'use':
                                          'gluster-brick-status-service',
                                          VOL_NAME: 'V1'})
        elif serviceDesc == 'Brick - /bricks/v1-new':
            return None
        elif serviceDesc == 'Brick - /bricks/v1-update':
            return self.fillServiceModel({'service_description': serviceDesc,
                                          'host_name': hostName,
                                          'use':
                                          'gluster-brick-status-service',
                                          VOL_NAME: 'V1',
                                          NOTES: 'Volume Type : Replicate'})
        elif serviceDesc == GLUSTER_AUTO_CONFIG:
            return self.fillServiceModel({'service_description': serviceDesc,
                                          'host_name': hostName,
                                          'use': 'gluster-service',
                                          'check_command':
                                          'gluster_auto_discovery!'
                                          '10.70.43.0!10.70.43.57'})

    def fillServiceModel(self, values):
        serviceModel = {}
        for key, value in values.iteritems():
            serviceModel[key] = value
        return serviceModel

    def testFindServiceDelta(self):
        server_utils.getServiceConfig = self.mockGetServiceConfig
        discovery.findDeletedServices = self.mockFindDeletedServices
        serviceDelta = discovery.findServiceDelta(self.getDummyHostConfig())
        self.assertEqual(len(serviceDelta), 4)
        service = discovery.findServiceInList(
            serviceDelta, 'Brick - /bricks/v1-no-change')
        self.assertEqual(service, None)
        service = discovery.findServiceInList(
            serviceDelta, 'Brick - /bricks/v1-new')
        self.assertEqual(service[CHANGE_MODE], CHANGE_MODE_ADD)
        service = discovery.findServiceInList(
            serviceDelta, 'Brick - /bricks/v1-update')
        self.assertEqual(service[CHANGE_MODE], CHANGE_MODE_UPDATE)
        self.assertEqual(service[VOL_NAME], 'V2')
        service = discovery.findServiceInList(
            serviceDelta, 'Brick - /bricks/v1-deleted')
        self.assertEqual(service[CHANGE_MODE], CHANGE_MODE_REMOVE)
        service = discovery.findServiceInList(
            serviceDelta, GLUSTER_AUTO_CONFIG)
        self.assertEqual(service[CHANGE_MODE], CHANGE_MODE_UPDATE)
        self.assertEqual(service['check_command'],
                         'gluster_auto_discovery!10.70.43.57!10.70.43.57')

    def getDummyHostConfig(self):
        hostServices = []
        hostServices.append({'service_description':
                             'Brick - /bricks/v1-no-change',
                             'host_name': 'host-1',
                             'use': 'gluster-brick-status-service',
                             VOL_NAME: 'V1'})
        hostServices.append({'service_description': 'Brick - /bricks/v1-new',
                             'host_name': 'host-1',
                             'use': 'gluster-brick-status-service',
                             VOL_NAME: 'V1'})
        hostServices.append({'service_description':
                             'Brick - /bricks/v1-update',
                             'host_name': 'host-1',
                             'use': 'gluster-brick-status-service',
                             VOL_NAME: 'V2',
                             NOTES: 'Volume Type : Replicate'})
        hostServices.append({'service_description': GLUSTER_AUTO_CONFIG,
                             'host_name': 'host-1',
                             'use': 'gluster-service',
                             'check_command':
                             'gluster_auto_discovery!10.70.43.57!10.70.43.57'})
        hostConfig = {HOST_SERVICES: hostServices}
        return hostConfig
