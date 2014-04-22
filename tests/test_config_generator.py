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

import mock
from plugins import config_generator
from testrunner import PluginsTestCase as TestCaseBase


class TestGlusterNagiosConfManager(TestCaseBase):
    # Method to test the generateNagiosConfigFromGlusterCluster() method
    @mock.patch('plugins.config_generator.GlusterNagiosConfManager.'
                'generateConfigFiles')
    def testGenerateConfigFiles(self, mock_generateConfigFiles):
        confManager = self.__getGlusterNagiosConfManager()
        clusterData = self.__createDummyCluster()
        clusterConfig = confManager.generateNagiosConfigFromGlusterCluster(
            clusterData)
        mock_generateConfigFiles.assert_called()
        self.__verifyConfig(clusterConfig, clusterData)

    def __verifyConfig(self, clusterConfig, clusterData):
        self.assertTrue(len(clusterConfig), len(clusterData['hosts']) + 1)
        self.__verifyClusterConfig(clusterConfig[0], clusterData)
        for index in range(0, len(clusterData['hosts'])):
            self.__verifyHostConfig(clusterConfig[index + 1],
                                    clusterData['hosts'][index])

    def __verifyHostConfig(self, hostConfig, hostData):
        self.assertEqual(hostConfig['host_name'], hostData['hostname'])
        self.assertEqual(hostConfig['alias'], hostData['hostname'])
        self.assertEqual(hostConfig['address'], hostData['hostip'])
        self.assertEqual(hostConfig['use'], 'gluster-host')

    def __verifyClusterConfig(self, config, clusterData):
        self.assertEqual(config['host_name'], clusterData['name'])
        self.assertEqual(config['alias'], clusterData['name'])
        self.assertEqual(config['address'], clusterData['name'])
        self.assertEqual(config.get('check_command'), None)
        self.assertEqual(config['use'], 'gluster-cluster')

    def createBricks(self, count, volume, hostip):
        bricks = []
        for number in range(count):
            brickDir = "/mnt/Brick-%s" % (number + 1)
            bricks.append({'brickpath': brickDir,
                           'volumeName': volume,
                           'hostip': hostip})
        return bricks

    def __createDummyCluster(self):
        cluster = {'name': 'Test-Cluster', 'hosts': [], 'volumes': []}
        cluster['hosts'].append({'hostip': '10.70.43.1',
                                 'hostname': 'host-1',
                                 'bricks': self.createBricks(1, "Volume1",
                                                             '10.70.43.1')})
        cluster['hosts'].append({'hostip': '10.70.43.2',
                                 'hostname': 'host-2',
                                 'bricks': self.createBricks(2, "Volume1",
                                                             '10.70.43.2')})
        cluster['volumes'].append({'name': 'Volume1', "type": "T"})
        return cluster

    def __getGlusterNagiosConfManager(self):
        return config_generator.GlusterNagiosConfManager(
            "/tmp/nagios/gluster", "../config", "gluster-host.cfg.template")
