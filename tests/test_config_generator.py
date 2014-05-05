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
        self.assertTrue(len(clusterConfig), len(clusterData['hosts']) + 1)
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
            serviceDesc = "Brick Status - %s" % brick['brickpath']
            service = self._findServiceInList(hostConfig['host_services'],
                                              serviceDesc)
            self.assertNotEqual(service, None,
                                "Brick status service is not created")
            serviceDesc = "Brick Utilization - %s" % brick['brickpath']
            service = self._findServiceInList(hostConfig['host_services'],
                                              serviceDesc)
            self.assertNotEqual(service, None,
                                "Brick Utilization service is not created")

    def _verifyClusterConfig(self, config, clusterData):
        self.assertEqual(config['host_name'], clusterData['name'])
        self.assertEqual(config['alias'], clusterData['name'])
        self.assertEqual(config['address'], clusterData['name'])
        self.assertEqual(config.get('check_command'), None)
        self.assertEqual(config['use'], 'gluster-cluster')
        self._verifyClusterServices(config, clusterData)

    def _verifyClusterServices(self, clusterConfig, clusterData):
        self.assertEqual(len(clusterConfig['host_services']), 8)
        serviceDesc = 'Cluster - Quorum'
        service = self._findServiceInList(clusterConfig['host_services'],
                                          serviceDesc)
        self.assertNotEqual(service, None,
                            "Cluster Quorum service is not created")
        for volume in clusterData['volumes']:
            self._verifyVolumeServices(clusterConfig['host_services'], volume)

    def _verifyVolumeServices(self, serviceList, volume):
        serviceDesc = 'Volume Utilization - %s' % (volume['name'])
        service = self._findServiceInList(serviceList, serviceDesc)
        self.assertNotEqual(service, None,
                            "Volume utilization service is not created")
        serviceDesc = 'Volume Status - %s' % (volume['name'])
        service = self._findServiceInList(serviceList, serviceDesc)
        self.assertNotEqual(service, None,
                            "Volume Status service is not created")
        serviceDesc = 'Volume Quota - %s' % (volume['name'])
        service = self._findServiceInList(serviceList, serviceDesc)
        self.assertNotEqual(service, None,
                            "Volume Status Quota service is not created")
        serviceDesc = 'Volume Geo-Replication - %s' % (volume['name'])
        service = self._findServiceInList(serviceList, serviceDesc)
        self.assertNotEqual(service, None,
                            "Volume Geo-Replication service is not created")
        if 'Replicate' in volume['type']:
            serviceDesc = 'Volume Self-Heal - %s' % (volume['name'])
            service = self._findServiceInList(serviceList, serviceDesc)
            self.assertNotEqual(service, None,
                                "Volume Self-Heal service is not created")

    def _findServiceInList(self, serviceList, serviceDescription):
        for service in serviceList:
            if service['service_description'] == serviceDescription:
                return service
        return None

    def createBricks(self, count, volume, hostip):
        bricks = []
        for number in range(count):
            brickDir = "/mnt/Brick-%s" % (number + 1)
            bricks.append({'brickpath': brickDir,
                           'volumeName': volume,
                           'hostip': hostip})
        return bricks

    def _createDummyCluster(self):
        cluster = {'name': 'Test-Cluster', 'hosts': [], 'volumes': []}
        cluster['hosts'].append({'hostip': '10.70.43.1',
                                 'hostname': 'host-1',
                                 'bricks': self.createBricks(1, "Volume1",
                                                             '10.70.43.1')})
        cluster['hosts'].append({'hostip': '10.70.43.2',
                                 'hostname': 'host-2',
                                 'bricks': self.createBricks(2, "Volume1",
                                                             '10.70.43.2')})
        cluster['volumes'].append({'name': 'Volume1', "type": "Replicate"})
        return cluster

    def _getGlusterNagiosConfManager(self):
        return config_generator.GlusterNagiosConfManager("/tmp/nagios/gluster")
