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

from plugins import config_generator
from plugins.config_generator import GLUSTER_AUTO_CONFIG
from plugins.config_generator import HOST_SERVICES
from glusternagios.glustercli import HostStatus
from testrunner import PluginsTestCase as TestCaseBase


class TestGlusterNagiosConfManager(TestCaseBase):
    # Method to test the generateNagiosConfigFromGlusterCluster() method
    def testGenerateNagiosConfig(self):
        confManager = self._getGlusterNagiosConfManager()
        clusterData = self._createDummyCluster()
        clusterConfig = confManager.generateNagiosConfig(
            clusterData)
        self._verifyConfig(clusterConfig, clusterData)

    def _verifyConfig(self, clusterConfig, clusterData):
        self.assertTrue(clusterConfig['hostgroup_name'], clusterData['name'])
        self.assertTrue(len(clusterConfig['_hosts']),
                        len(clusterData['hosts']) + 1)
        self._verifyClusterConfig(clusterConfig["_hosts"][0], clusterData)
        for index in range(0, len(clusterData['hosts'])):
            self._verifyHostConfig(clusterConfig['_hosts'][index + 1],
                                   clusterData['hosts'][index])

    def _verifyHostConfig(self, hostConfig, hostData):
        self.assertEqual(hostConfig['host_name'], hostData['hostname'])
        self.assertEqual(hostConfig['alias'], hostData['hostname'])
        self.assertEqual(hostConfig['address'], hostData['hostip'])
        self.assertEqual(hostConfig['use'], 'gluster-host')
        self._verifyHostServices(hostConfig, hostData)

    def _verifyHostServices(self, hostConfig, hostData):
        for brick in hostData['bricks']:
            self._checkServiceExists("Brick - %s" % brick['brickpath'],
                                     hostConfig[HOST_SERVICES])
            self._checkServiceExists(
                "Brick Utilization - %s" % brick['brickpath'],
                hostConfig[HOST_SERVICES])

    def _verifyClusterConfig(self, config, clusterData):
        self.assertEqual(config['host_name'], clusterData['name'])
        self.assertEqual(config['alias'], clusterData['name'])
        self.assertEqual(config['address'], clusterData['name'])
        self.assertEqual(config.get('check_command'), None)
        self.assertEqual(config['use'], 'gluster-cluster')
        self._verifyClusterServices(config, clusterData)

    def _checkServiceExists(self, serviceDesc, serviceList):
        service = self._findServiceInList(serviceList, serviceDesc)
        self.assertNotEqual(service, None,
                            "%s service is not created" % serviceDesc)

    def _verifyClusterServices(self, clusterConfig, clusterData):
        totalServices = 0
        services = clusterConfig[HOST_SERVICES]
        self._checkServiceExists("Cluster - Quorum", services)
        self._checkServiceExists(GLUSTER_AUTO_CONFIG, services)
        self._checkServiceExists("Cluster Utilization", services)

        totalServices += 3

        for volume in clusterData['volumes']:
            totalServices += self._verifyVolumeServices(
                clusterConfig[HOST_SERVICES], volume)
        self.assertEqual(len(clusterConfig[HOST_SERVICES]), totalServices)

    def _verifyVolumeServices(self, serviceList, volume):
        serviceDesc = 'Volume Utilization - %s' % (volume['name'])
        self._checkServiceExists('Volume Utilization - %s' % (volume['name']),
                                 serviceList)
        self._checkServiceExists('Volume Status - %s' % (volume['name']),
                                 serviceList)
        serviceCount = 2

        if volume.get('quota') == 'on':
            self._checkServiceExists('Volume Quota - %s' % (volume['name']),
                                     serviceList)
            serviceCount += 1

        if volume.get('geo-rep') == 'on':
            self._checkServiceExists(
                'Volume Geo-Replication - %s' % (volume['name']), serviceList)
            serviceCount += 1

        if 'REPLICATE' in volume['type']:
            serviceDesc = 'Volume Split-brain status - %s' % (volume['name'])
            service = self._findServiceInList(serviceList, serviceDesc)
            self.assertNotEqual(service, None,
                                "Volume Split-brain service is not created")
            serviceCount += 1
        return serviceCount

    def _findServiceInList(self, serviceList, serviceDescription):
        for service in serviceList:
            if service['service_description'] == serviceDescription:
                return service
        return None

    def createBricks(self, count, volume, hostip, base):
        bricks = []
        for number in range(count):
            brickDir = "%s-%s" % (base, (number + 1))
            bricks.append({'brickpath': brickDir,
                           'volumeName': volume,
                           'hostip': hostip})
        return bricks

    def _createDummyCluster(self):
        cluster = {'name': 'Test-Cluster', 'hosts': [], 'volumes': []}

        cluster['volumes'].append({'name': 'Volume1', "type": "REPLICATE",
                                   'quota': 'on', 'geo-rep': 'on'})
        host1Bricks = self.createBricks(1, "Volume1", '10.70.43.1',
                                        '/mnt/v1/bricks')
        host2Bricks = self.createBricks(2, "Volume1", '10.70.43.2',
                                        '/mnt/v1/bricks')

        cluster['volumes'].append({'name': 'Volume2', "type": "DISTRIBUTE"})
        host1Bricks.extend(self.createBricks(1, "Volume2", '10.70.43.1',
                                             '/mnt/v2/bricks'))
        host2Bricks.extend(self.createBricks(1, "Volume2", '10.70.43.2',
                                             '/mnt/v2/bricks'))

        cluster['hosts'].append({'hostip': '10.70.43.1',
                                 'hostname': 'host-1',
                                 'uuid': '0000-1111',
                                 'status': HostStatus.CONNECTED,
                                 'bricks': host1Bricks})
        cluster['hosts'].append({'hostip': '10.70.43.2',
                                 'hostname': 'host-2',
                                 'status': HostStatus.CONNECTED,
                                 'uuid': '0000-1112',
                                 'bricks': host2Bricks})
        return cluster

    def _getGlusterNagiosConfManager(self):
        return config_generator.GlusterNagiosConfManager("/tmp/nagios/gluster")
