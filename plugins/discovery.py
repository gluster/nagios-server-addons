#!/usr/bin/python
# discovery.py Nagios plugin to discover Gluster entities using NRPE
# Copyright (C) 2014 Red Hat Inc
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA
#
import argparse
import json

import os
import shutil
import sys

from glusternagios import utils
from config_generator import GlusterNagiosConfManager
import server_utils
from constants import DEFAULT_AUTO_CONFIG_DIR
from constants import NRPE_PATH


from config_generator import CHANGE_MODE_ADD
from config_generator import CHANGE_MODE_REMOVE
from config_generator import CHANGE_MODE_UPDATE


nrpeCmdPath = utils.CommandPath("nrpe", NRPE_PATH, )


def excecNRPECommand(host, command):
    (returncode, outputStr, err) = utils.execCmd([nrpeCmdPath.cmd,
                                                  "-H", host, "-c", command])
    #convert to dictionary
    try:
        output = json.loads(outputStr[0])
    except Exception as e:
        e.args += (outputStr[0])
        raise
    return output


def discoverCluster(hostip, cluster):
    """
    This method helps to discover the nodes, volumes and bricks in the given
    gluster. It uses NRPE commands to contact the gluster nodes.

    Assumptions:
    First node returned by the "discoverpeers" NRPE command should be the same
    node where "discoverpeers" is executed.

    Parameters
    ----------
    hostip: Address of a node in the gluster cluster.
    cluster: Cluster Name

    Returns
    ---------
     Returns cluster details in the following dictinary format
    {
      'name': cluster-name,
     'volumes': [list-volumes],
    'host': [list-hosts]
    }
    each host in the list will a have list of bricks from the host.
    """

    clusterdata = {}
    #Discover the logical components
    componentlist = excecNRPECommand(hostip, "discoverlogicalcomponents")
    #Discover the peers
    hostlist = excecNRPECommand(hostip, "discoverpeers")
    #Add the ip address of the root node given by the user to the peer list
    hostlist[0]['hostip'] = hostip
    for host in hostlist:
        #Get host names
        hostDetails = excecNRPECommand(host['hostip'], "discoverhostparams")
        host.update(hostDetails)
        #Get the list of bricks for this host and add to dictionary
        host['bricks'] = []
        for volume in componentlist['volumes']:
            for brick in volume['bricks']:
                if brick['hostUuid'] == host['uuid']:
                    brick['volumeName'] = volume['name']
                    host['bricks'].append(brick)
    clusterdata['hosts'] = hostlist
    clusterdata['volumes'] = componentlist['volumes']
    clusterdata['name'] = cluster
    #Host names returned by "discoverhostparams" supposed to be unique. So host
    #name can be used to configure the host_name in nagios host.
    #But if host names are not unique then we have to use IP address to
    #configure host_name in nagios.
    if not isHostsNamesUnique(clusterdata):
        setHostNameWithIP(clusterdata)
    return clusterdata


# Set host address as the hostname
def setHostNameWithIP(clusterdata):
    for host in clusterdata['hosts']:
        host['hostname'] = host['hostip']


# Check host names are unique
def isHostsNamesUnique(clusterdata):
    hostnames = {}
    for host in clusterdata['hosts']:
        if hostnames.get(host['hostname']) is None:
            hostnames[host['hostname']] = host['hostip']
        else:
            return False
    return True


def getConfigManager(args):
    configDir = DEFAULT_AUTO_CONFIG_DIR
    if args.configDir is not None:
        configDir = args.configDir
    clusterConfigDir = configDir + "/" + args.cluster
    configManager = GlusterNagiosConfManager(clusterConfigDir)
    return configManager


#Find the given service in service list.
def findServiceInList(serviceList, serviceDescription):
    for service in serviceList:
        if service['service_description'] == serviceDescription:
            return service
    return None


#Find the given host in host list
def findHostInList(hostList, hostName):
    for host in hostList:
        if host['host_name'] == hostName:
            return host
    return None


#Find all deleted services in the host.
def findDeletedServices(host):
    deletedService = []
    serviceConfigs = server_utils.getServiceConfigByHost(host['host_name'])
    for serviceConfig in serviceConfigs:
        service = findServiceInList(host['host_services'],
                                    serviceConfig['service_description'])
        if service is None:
            deletedService.append(
                {'service_description': serviceConfig['service_description'],
                 'changeMode': CHANGE_MODE_REMOVE})
    return deletedService


#Check if auto config is changed. IP address in the check command will change
#when user runs the auto config using different host.
def findChangeInAutoConfig(newService, oldService):
    if newService['check_command'] != oldService['check_command']:
        changes = {}
        changes['check_command'] = newService['check_command']
        changes['service_description'] = newService['service_description']
        changes['host_name'] = newService['host_name']
        changes['changeMode'] = CHANGE_MODE_UPDATE
        return changes
    return None


#Find all Added/Deleted services in the given host.
#Note: 'Cluster Auto Config' is a special service. When user runs the
#auto-config using different host instead what is used previously then we
#have to update the host ip in existing auto-config service.
def findServiceDelta(host):
    serviceDelta = []
    for service in host['host_services']:
        serviceConfig = server_utils.getServiceConfig(
            service['service_description'], service['host_name'])
        if serviceConfig is None:
            service['changeMode'] = CHANGE_MODE_ADD
            serviceDelta.append(service)
        elif serviceConfig['service_description'] == "Cluster Auto Config":
            changes = findChangeInAutoConfig(service, serviceConfig)
            if changes:
                serviceDelta.append(changes)
    serviceDelta.extend(findDeletedServices(host))
    return serviceDelta


#Find newly added hosts and newly added services to the existing hosts
def findAddUpdateHosts(hosts):
    delta = []
    for host in hosts:
        hostConfing = server_utils.getHostConfigByName(host['host_name'])
        if hostConfing is None:
            host['changeMode'] = CHANGE_MODE_ADD
            delta.append(host)
        else:
            serviceDelta = findServiceDelta(host)
            if serviceDelta:
                host['changeMode'] = CHANGE_MODE_UPDATE
                host['host_services'] = serviceDelta
                delta.append(host)
    return delta


#Find deleted hosts in the given cluster.
def findDeletedHosts(hostgroup, hosts):
    deletedHosts = []
    hostConfigs = server_utils.getHostConfigsForCluster(hostgroup)
    for hostConfig in hostConfigs:
        host = findHostInList(hosts, hostConfig['host_name'])
        if host is None:
            deletedHosts.append({'host_name': hostConfig['host_name'],
                                 'changeMode': CHANGE_MODE_REMOVE})
    return deletedHosts


#Find Added/Deleted/Updated hosts in cluster
def findHostDelta(clusterConfig):
    hostDelta = []
    updated = findAddUpdateHosts(clusterConfig['_hosts'])
    hostDelta.extend(updated)
    hostDelta.extend(findDeletedHosts(clusterConfig['hostgroup_name'],
                                      clusterConfig['_hosts']))
    return hostDelta


#Find changes to the cluster
def findDelta(clusterConfig):
    delta = {}
    delta['hostgroup_name'] = clusterConfig['hostgroup_name']
    delta['alias'] = clusterConfig['alias']

    hostgroup = server_utils.getHostGroup(clusterConfig['hostgroup_name'])
    if hostgroup is None:
        delta['changeMode'] = CHANGE_MODE_ADD
        delta['_hosts'] = clusterConfig['_hosts']
        return delta

    hostDelta = findHostDelta(clusterConfig)
    delta['_hosts'] = hostDelta
    if hostDelta:
        delta['changeMode'] = CHANGE_MODE_UPDATE
    return delta


def parse_input():
    parser = argparse.ArgumentParser(description="Gluster Auto Discover Tool")
    parser.add_argument('-c', '--cluster', action='store', dest='cluster',
                        type=str, required=True, help='Cluster name')
    parser.add_argument('-H', '--hostip', action='store', dest='hostip',
                        type=str, required=True, help='Host IP')
    parser.add_argument('-m', '--mode', action='store', dest='mode',
                        choices=['auto', 'manual'], required=False,
                        default='manual', help='Mode')
    parser.add_argument('-d', '--configdir', action='store', dest='configDir',
                        type=str, required=False,
                        default=DEFAULT_AUTO_CONFIG_DIR,
                        help='Configuration directory where'
                             ' output files will be written')
    parser.add_argument('-f', '--force', action='store_true', dest='force',
                        help="Force sync the Cluster configuration")
    args = parser.parse_args()
    return args


#Clean the config directory
def cleanConfigDir(dir):
    if os.path.exists(dir):
        # Deleting the config dir to write new configs
        shutil.rmtree(dir)
    os.mkdir(dir)


#Preview the changes to cluster config
def previewChanges(clusterDelta):
    print "Changes :"
    clusterChangeMode = clusterDelta['changeMode']
    print "Hostgroup %s - %s" % (clusterDelta['hostgroup_name'],
                                 clusterChangeMode)
    for host in clusterDelta['_hosts']:
        if host.get('changeMode'):
            changeMode = host.get('changeMode')
        else:
            changeMode = clusterChangeMode
        print "Host %s - %s" % (host['host_name'], changeMode)
        for service in host.get('host_services'):
            if service.get('changeMode'):
                changeMode = service.get('changeMode')
            print "\t Service - %s -%s " % (service['service_description'],
                                            changeMode)


#Write the cluster configurations. If force mode is used then it will clean
#the config directory before writing the changes.
def writeDelta(clusterDelta, configManager, force):
    if force:
        cleanConfigDir(configManager.configDir)
    configManager.generateConfigFiles(clusterDelta)


def getConfirmation(message, default):
    while True:
        ans = raw_input("%s (Yes, No) [%s]: " % (message, default))
        if not ans:
            ans = default
        ans = ans.upper()
        if ans not in ['YES', 'NO']:
            print 'please enter Yes or No'
        if ans == 'YES':
            return True
        if ans == 'NO':
            return False

if __name__ == '__main__':
    args = parse_input()
    clusterdata = discoverCluster(args.hostip, args.cluster)
    configManager = getConfigManager(args)
    clusterDelta = configManager.generateNagiosConfig(clusterdata)
    if args.force:
        clusterDelta['changeMode'] = CHANGE_MODE_ADD
    else:
        clusterDelta = findDelta(clusterDelta)

    if clusterDelta.get('changeMode') is None:
        print "Cluster configurations are in sync"
        sys.exit(utils.PluginStatusCode.OK)
    #When auto config is run in manual mode, we will ask confirmation
    #before writing the config file and before restarting the Nagios
    if args.mode == "manual":
        print "Cluster configurations changed"
        previewChanges(clusterDelta)
        confirmation = getConfirmation(
            "Are you sure, you want to commit the changes?", "Yes")
        if confirmation:
            writeDelta(clusterDelta, configManager, args.force)
            print "Cluster configurations synced successfully from host %s" % \
                  (args.hostip)
            #If Nagios is running then try to restart. Otherwise don't do
            #anything.
            if server_utils.isNagiosRunning():
                confirmation = getConfirmation(
                    "Do you want to restart Nagios to start monitoring newly "
                    "discovered entities?", "Yes")
                if confirmation:
                    server_utils.restartNagios()
                    print "Nagios re-started successfully"
            else:
                print "Start the Nagios service to monitor"
    #auto mode means write the configurations without asking confirmation
    elif args.mode == "auto":
        writeDelta(clusterDelta, configManager, args.force)
        print "Cluster configurations synced successfully from host %s" % \
              (args.hostip)
        if server_utils.isNagiosRunning():
            server_utils.restartNagios()
    sys.exit(utils.PluginStatusCode.OK)
