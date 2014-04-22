#!/usr/bin/python
#
# config_generator.py - Nagios configuration generator for gluster
# entities. Copyright (C) 2014 Red Hat Inc
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

from jinja2 import Environment, FileSystemLoader
import os
import shutil


class GlusterNagiosConfManager:

    def __init__(self, configDir, configTemplateDir, hostTemplateName):
        self.configDir = configDir
        self.configTemplateDir = configTemplateDir
        self.hostTemplateName = hostTemplateName
        self.__loadJinja()

    def __loadJinja(self):
        self.jinjaEnv = Environment(
            loader=FileSystemLoader(self.configTemplateDir))
        self.hostTemplate = self.jinjaEnv.get_template(self.hostTemplateName)

    def __createHostConfig(self, host):
        hostConfigStr = self.hostTemplate.render(host=host)
        hostConfig = {'name': host['host_name'], 'config': hostConfigStr}
        return hostConfig

    def createHost(self, hostName, alias, template,
                   address, hostGroups, checkCommand, services):
        host = {}
        host['host_name'] = hostName
        host['alias'] = alias
        host['use'] = template
        host['address'] = address
        if checkCommand:
            host['check_command'] = checkCommand
        if hostGroups:
            host['hostgroups'] = hostGroups

        if services:
            host['host_services'] = services
        return host

    def __createVolumeUtilizationService(self, volume, clusterName):
        volumeService = {}
        volumeService['host_name'] = clusterName
        volumeService['use'] = 'gluster-service-with-graph'
        serviceDesc = 'Volume Utilization - %s' % (volume['name'])
        volumeService['service_description'] = serviceDesc
        volumeService['_VOL_NAME'] = volume['name']
        checkCommand = 'check_vol_utilization!%s!%s!70!90' % \
                       (clusterName, volume['name'])
        volumeService['check_command'] = checkCommand
        volumeService['notes'] = "Volume type : %s" % (volume['type'])
        return volumeService

    def __createVolumeStatusService(self, volume, clusterName):
        volumeService = {}
        volumeService['host_name'] = clusterName
        volumeService['use'] = 'gluster-service-without-graph'
        serviceDesc = 'Volume Status - %s' % (volume['name'])
        volumeService['service_description'] = serviceDesc
        volumeService['_VOL_NAME'] = volume['name']
        checkCommand = 'check_vol_status!%s!%s' % \
                       (clusterName, volume['name'])
        volumeService['check_command'] = checkCommand
        volumeService['notes'] = "Volume type : %s" % (volume['type'])
        return volumeService

    def __createVolumeQuotaStatusService(self, volume, clusterName):
        volumeService = {}
        volumeService['host_name'] = clusterName
        volumeService['use'] = 'gluster-service-without-graph'
        serviceDesc = 'Volume Status Quota - %s' % (volume['name'])
        volumeService['service_description'] = serviceDesc
        volumeService['_VOL_NAME'] = volume['name']
        checkCommand = 'check_vol_quota_status!%s!%s' % \
                       (clusterName, volume['name'])
        volumeService['check_command'] = checkCommand
        volumeService['notes'] = "Volume type : %s" % (volume['type'])
        return volumeService

    def createClusterUtilizationService(self, clusterName):
        service = {}
        service['host_name'] = clusterName
        service['use'] = 'gluster-service-with-graph'
        service['service_description'] = 'Cluster Utilization'
        service['check_command'] = 'check_cluster_vol_usage!80!90'
        return service

    def createClusterAutoConfigService(self, clusterName, hostIp):
        service = {}
        service['host_name'] = clusterName
        service['use'] = 'generic-service'
        service['service_description'] = 'Cluster Auto Config'
        service['check_command'] = "gluster_auto_discovery!%s" % (hostIp)
        service['check_interval'] = '1440'
        return service

    def createrVolumeServices(self, volumes, clusterName):
        volumeServices = []
        for volume in volumes:
            volumeService = self.__createVolumeUtilizationService(volume,
                                                                  clusterName)
            volumeServices.append(volumeService)
            volumeService = self.__createVolumeQuotaStatusService(volume,
                                                                  clusterName)
            volumeServices.append(volumeService)
            volumeService = self.__createVolumeStatusService(volume,
                                                             clusterName)
            volumeServices.append(volumeService)
        return volumeServices

    def __createBrickUtilizationService(self, brick, hostName):
        brickService = {}
        brickService['use'] = 'brick-service'
        brickService['host_name'] = hostName
        serviceDesc = "Brick Utilization - %s:%s" % (hostName,
                                                     brick['brickpath'])
        brickService['service_description'] = serviceDesc
        brickService['_BRICK_DIR'] = brick['brickpath']
        brickService['_VOL_NAME'] = brick['volumeName']
        brickService['notes'] = "Volume : %s" % (brick['volumeName'])
        return brickService

    def __createBrickStatusService(self, brick, hostName):
        brickService = {}
        brickService['use'] = 'gluster-brick-passive-service'
        brickService['host_name'] = hostName
        serviceDesc = "Brick Status - %s:%s" % (hostName,
                                                brick['brickpath'])
        brickService['service_description'] = serviceDesc
        brickService['_BRICK_DIR'] = brick['brickpath']
        brickService['_VOL_NAME'] = brick['volumeName']
        brickService['notes'] = "Volume : %s" % (brick['volumeName'])
        return brickService

    def createBrickServices(self, host):
        brickServices = []
        for brick in host['bricks']:
            brickService = self.__createBrickUtilizationService(
                brick, host['hostname'])
            brickServices.append(brickService)
            brickService = self.__createBrickStatusService(
                brick, host['hostname'])
            brickServices.append(brickService)
        return brickServices

    def generateNagiosConfigFromGlusterCluster(self, cluster):
        hostsConfigs = []
        clusterServices = self.createrVolumeServices(
            cluster.get('volumes'), cluster['name'])
        # If there are volumes, then create a cluster utilization service
        if cluster.get('volumes'):
            clusterServices.append(self.createClusterUtilizationService(
                cluster['name']))
        clusterServices.append(self.createClusterAutoConfigService(
            cluster['name'], cluster['hosts'][-1]['hostip']))
        clusterHostConfig = self.createHost(
            cluster['name'], cluster['name'], "gluster-cluster",
            cluster['name'], None, None, clusterServices)
        hostsConfigs.append(clusterHostConfig)
        for host in cluster['hosts']:
            brickServices = self.createBrickServices(host)
            hostGroups = "gluster_hosts,%s" % (cluster['name'])
            hostConfig = self.createHost(
                host['hostname'], host['hostname'], "gluster-host",
                host['hostip'], hostGroups, "", brickServices)
            hostsConfigs.append(hostConfig)
        self.generateConfigFiles(hostsConfigs)
        return hostsConfigs

    def generateConfigFiles(self, hosts):
        clusterConfig = {'name': None, 'hostConfigs': []}
        clusterConfigDir = None
        for host in hosts:
            if host['use'] == 'gluster-cluster':
                clusterConfigDir = self.configDir + "/" + host['host_name']
                self.__prepareConfDir(clusterConfigDir)
                clusterConfig['name'] = host['host_name']
            hostConfig = self.__createHostConfig(host)
            clusterConfig['hostConfigs'].append(hostConfig)
        for hostConfig in clusterConfig['hostConfigs']:
            self.__writeHostConfig(clusterConfigDir, hostConfig)

    def __prepareConfDir(self, confDir):
        if os.path.exists(confDir):
            # Deleting the config dir to write new configs
            shutil.rmtree(confDir)
        os.mkdir(confDir)

    def __writeHostConfig(self, clusterConfigDir, hostConfig):
        if not clusterConfigDir:
            raise Exception("Cluster configuration directory can't None")
        configFilePath = clusterConfigDir + "/" + hostConfig['name'] + ".cfg"
        with open(configFilePath, 'w') as configFile:
            configFile.write(hostConfig['config'])
