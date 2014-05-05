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

from pynag import Model

import server_utils
from glusternagios.glustercli import HostStatus

"""
Change mode helps to identify the change in the defintion.
"ADD" means the entity and all its sub entities are added.
"REMOVE" means the entity and all its sub entities are removed
"UPDATE" means the entity is changes. It may also means sub entities
are added or removed to the entity.
"""
CHANGE_MODE_ADD = "ADD"
CHANGE_MODE_REMOVE = "REMOVE"
CHANGE_MODE_UPDATE = "UPDATE"


class GlusterNagiosConfManager:

    def __init__(self, configDir):
        self.configDir = configDir

    #Create nagios host configuration with the given attributes
    def createHost(self, hostName, alias, template,
                   address, hostGroups, checkCommand, services, uuid):
        host = {}
        host['host_name'] = hostName
        host['alias'] = alias
        host['use'] = template
        host['address'] = address
        if checkCommand:
            host['check_command'] = checkCommand
        if hostGroups:
            host['hostgroups'] = hostGroups
        #Host service is not a field in host configuration. It helps to
        #aggregate all the host services under the host
        if services:
            host['host_services'] = services
        if uuid:
            host['_HOST_UUID'] = uuid
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
        serviceDesc = 'Volume Quota - %s' % (volume['name'])
        volumeService['service_description'] = serviceDesc
        volumeService['_VOL_NAME'] = volume['name']
        checkCommand = 'check_vol_quota_status!%s!%s' % \
                       (clusterName, volume['name'])
        volumeService['check_command'] = checkCommand
        volumeService['notes'] = "Volume type : %s" % (volume['type'])
        return volumeService

    def __createVolumeHealStatusService(self, volume, clusterName):
        volumeService = {}
        volumeService['host_name'] = clusterName
        volumeService['use'] = 'gluster-service-without-graph'
        serviceDesc = 'Volume Self-Heal - %s' % (volume['name'])
        volumeService['service_description'] = serviceDesc
        volumeService['_VOL_NAME'] = volume['name']
        checkCommand = 'check_vol_heal_status!%s!%s' % \
                       (clusterName, volume['name'])
        volumeService['check_command'] = checkCommand
        return volumeService

    def __createVolumeGeoRepStatusService(self, volume, clusterName):
        volumeService = {}
        volumeService['host_name'] = clusterName
        volumeService['use'] = 'gluster-service-without-graph'
        serviceDesc = 'Volume Geo-Replication - %s' % (volume['name'])
        volumeService['service_description'] = serviceDesc
        volumeService['_VOL_NAME'] = volume['name']
        checkCommand = 'check_vol_georep_status!%s!%s' % \
                       (clusterName, volume['name'])
        volumeService['check_command'] = checkCommand
        return volumeService

    def createClusterUtilizationService(self, clusterName):
        service = {}
        service['host_name'] = clusterName
        service['use'] = 'gluster-service-with-graph'
        service['service_description'] = 'Cluster Utilization'
        service['check_command'] = 'check_cluster_vol_usage!80!90'
        return service

    def createClusterQuorumService(self, clusterName):
        service = {}
        service['host_name'] = clusterName
        service['use'] = 'gluster-passive-service'
        service['service_description'] = 'Cluster - Quorum'
        return service

    def createClusterAutoConfigService(self, clusterName, hostIp):
        service = {}
        service['host_name'] = clusterName
        service['use'] = 'gluster-service'
        service['check_interval'] = '1440'
        service['service_description'] = 'Cluster Auto Config'
        service['check_command'] = "gluster_auto_discovery!%s" % (hostIp)
        return service

    #Create all volume related services for the given volume
    def createrVolumeServices(self, volumes, clusterName):
        volumeServices = []
        for volume in volumes:
            volumeService = self.__createVolumeUtilizationService(volume,
                                                                  clusterName)
            volumeServices.append(volumeService)
            volumeService = self.__createVolumeQuotaStatusService(volume,
                                                                  clusterName)
            volumeServices.append(volumeService)
            if 'REPLICATE' in volume['type'].upper():
                volumeService = (self.
                                 __createVolumeHealStatusService(volume,
                                                                 clusterName))
                volumeServices.append(volumeService)
            volumeService = (self.
                             __createVolumeGeoRepStatusService(volume,
                                                               clusterName))
            volumeServices.append(volumeService)
            volumeService = self.__createVolumeStatusService(volume,
                                                             clusterName)
            volumeServices.append(volumeService)
        return volumeServices

    def __createBrickUtilizationService(self, brick, hostName):
        brickService = {}
        brickService['use'] = 'brick-service'
        brickService['host_name'] = hostName
        serviceDesc = "Brick Utilization - %s" % brick['brickpath']
        brickService['service_description'] = serviceDesc
        brickService['_BRICK_DIR'] = brick['brickpath']
        brickService['_VOL_NAME'] = brick['volumeName']
        brickService['notes'] = "Volume : %s" % (brick['volumeName'])
        return brickService

    def __createBrickStatusService(self, brick, hostName):
        brickService = {}
        brickService['use'] = 'gluster-brick-status-service'
        brickService['host_name'] = hostName
        serviceDesc = "Brick - %s" % brick['brickpath']
        brickService['service_description'] = serviceDesc
        brickService['_BRICK_DIR'] = brick['brickpath']
        brickService['_VOL_NAME'] = brick['volumeName']
        brickService['notes'] = "Volume : %s" % (brick['volumeName'])
        return brickService

    #Create all Brick related service here.
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

    #Create a host group with the name
    def createHostGroup(self, name):
        return {'hostgroup_name': name, 'alias': name}

    #Create the Nagios configuration model in run time using list and
    #dictionary
    #Nagios config model hierarchy
    #########################################################################
    #Hostgroup
    #  --'_host' ---> List of host configurations in the host group
    #    --'host_services' ----> List of services in the host
    #########################################################################
    def generateNagiosConfig(self, cluster):
        hostGroup = self.createHostGroup(cluster['name'])
        hostsConfigs = []
        clusterServices = self.createrVolumeServices(
            cluster.get('volumes'), cluster['name'])
        # If there are volumes, then create a cluster utilization service
        if cluster.get('volumes'):
            clusterServices.append(self.createClusterUtilizationService(
                cluster['name']))
            clusterServices.append(self.createClusterQuorumService(
                cluster['name']))
        clusterServices.append(self.createClusterAutoConfigService(
            cluster['name'], cluster['hosts'][0]['hostip']))
        #Create host config for Gluster cluster with volume related services
        clusterHostConfig = self.createHost(
            cluster['name'], cluster['name'], "gluster-cluster",
            cluster['name'], None, None, clusterServices, None)
        hostsConfigs.append(clusterHostConfig)
        #Create host config for all hosts in the cluster with brick related
        #services
        for host in cluster['hosts']:
            if host['status'] == HostStatus.CONNECTED:
                brickServices = self.createBrickServices(host)
                hostGroups = "gluster_hosts,%s" % (cluster['name'])
                hostConfig = self.createHost(
                    host['hostname'], host['hostname'], "gluster-host",
                    host['hostip'], hostGroups, None, brickServices,
                    host.get('uuid'))
                hostsConfigs.append(hostConfig)
        hostGroup["_hosts"] = hostsConfigs
        return hostGroup

    #Get the config file name for the given hostname
    def getCfgFileName(self, hostname):
        return self.configDir + "/" + hostname + ".cfg"

    #Create Nagios config service for the given host group with all hosts.
    #Host group should contain the delta to be written to the configuration.
    #Delta will be processed using the change mode.
    def writeHostGroup(self, hostgroup):
        changeMode = hostgroup['changeMode']
        if changeMode == CHANGE_MODE_ADD:
            hostgroupModel = Model.Hostgroup()
            hostgroupModel['hostgroup_name'] = hostgroup['hostgroup_name']
            hostgroupModel['alias'] = hostgroup['alias']
            hostgroupModel.set_filename(
                self.getCfgFileName(hostgroup['hostgroup_name']))
            hostgroupModel.save()
        #Process all the hosts in the hostgroup. ChangeMode of the hostgroup
        #will be used to proces the host if there is not changeMode specified
        #in the host.
        if hostgroup['_hosts']:
            self.writeHosts(hostgroup['_hosts'], changeMode)

    #Fill the pynag model with the given values.
    #'changeMode' and 'host_services' are special fields which are
    #not meant to be writen to the nagios config, These fields are
    #used to represent the config model and changes.
    def fillModel(self, model, values):
        for key, value in values.iteritems():
            if key not in ['changeMode', 'host_services']:
                model[key] = value
        return model

    #Write service to nagios config
    def writeService(self, service, hostname):
        if service['changeMode'] == CHANGE_MODE_ADD:
            serviceModel = Model.Service()
            serviceModel = self.fillModel(serviceModel, service)
            serviceModel.set_filename(self.getCfgFileName(hostname))
            serviceModel.save()
        elif service['changeMode'] == CHANGE_MODE_REMOVE:
            serviceModel = Model.Service.objects.filter(
                host_name=hostname,
                service_description=service['service_description'])
            if serviceModel:
                serviceModel[0].delete()
        elif service['changeMode'] == CHANGE_MODE_UPDATE:
            serviceModel = server_utils.getServiceConfig(
                service['service_description'], service['host_name'])
            self.fillModel(serviceModel, service)
            serviceModel.save()

    #Write all services in the host.
    #host_services filed contains the list of services to be written to
    #nagios configuration
    def writeHostServices(self, host):
        for service in host['host_services']:
            if service.get('changeMode') is None:
                service['changeMode'] = host['changeMode']
            self.writeService(service, host['host_name'])

    #Write the host configuration with list of services to nagios configuration
    def writeHost(self, host):
        if host['changeMode'] == CHANGE_MODE_REMOVE:
            hostModel = Model.Host.objects.filter(
                host_name=host['host_name'])
            if hostModel:
                hostModel[0].delete(recursive=True)
            return
        if host['changeMode'] == CHANGE_MODE_ADD:
            hostModel = Model.Host()
            hostModel = self.fillModel(hostModel, host)
            hostModel.set_filename(self.getCfgFileName(host['host_name']))
            hostModel.save()

        if host.get('host_services'):
            self.writeHostServices(host)

    def writeHosts(self, hosts, chageMode):
        for host in hosts:
            if host.get('changeMode') is None:
                host['changeMode'] = chageMode
            self.writeHost(host)

    #Write the hostgroup delta to nagios configuration.
    def generateConfigFiles(self, delta):
        self.writeHostGroup(delta)
