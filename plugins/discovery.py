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
import datetime
import sys

from glusternagios import utils
from config_generator import GlusterNagiosConfManager
from constants import DEFAULT_AUTO_CONFIG_DIR
from constants import HOST_TEMPLATE_DIR
from constants import HOST_TEMPLATE_NAME
from constants import NRPE_PATH
import submit_external_command


serviceCmdPath = utils.CommandPath("service", "/sbin/service", )
nrpeCmdPath = utils.CommandPath("nrpe", NRPE_PATH, )


def excecNRPECommand(host, command):
    output = {}
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
    clusterdata = {}
    #Discover the logical components
    componentlist = excecNRPECommand(hostip, "discoverlogicalcomponents")
    #Discover the peers
    hostlist = excecNRPECommand(hostip, "discoverpeers")
    #Add the ip address of the root node to the peer list
    #to generate the configuration
    hostlist.append({"hostip": hostip})
    for host in hostlist:
        #Get host names
        hostDetails = excecNRPECommand(host['hostip'], "discoverhostparams")
        host.update(hostDetails)
        #Get the list of bricks for this host and add to dictionary
        host['bricks'] = []
        for volume in componentlist['volumes']:
            for brick in volume['bricks']:
                if brick['hostip'] == host['hostip']:
                    brick['volumeName'] = volume['name']
                    host['bricks'].append(brick)
    clusterdata['hosts'] = hostlist
    clusterdata['volumes'] = componentlist['volumes']
    clusterdata['name'] = cluster
    if not isHostsNamesUnique(clusterdata):
        setHostNameWithIP(clusterdata)
    return clusterdata


def setHostNameWithIP(clusterdata):
    for host in clusterdata['hosts']:
        host['hostname'] = host['hostip']


def isHostsNamesUnique(clusterdata):
    hostnames = {}
    for host in clusterdata['hosts']:
        if hostnames.get(host['hostname']) is None:
            hostnames[host['hostname']] = host['hostip']
        else:
            return False
    return True


def parse_input():
    parser = argparse.ArgumentParser(description="Gluster Auto Discover Tool")
    parser.add_argument('-c', '--cluster', action='store', dest='cluster',
                        type=str, required=True, help='Cluster name')
    parser.add_argument('-H', '--hostip', action='store', dest='hostip',
                        type=str, required=True, help='Host IP')
    parser.add_argument('-d', '--configdir', action='store', dest='configDir',
                        type=str, required=False,
                        help='Configuration directory '
                             'where output files will be written')
    args = parser.parse_args()
    return args


def getConfigManager(args):
    configDir = DEFAULT_AUTO_CONFIG_DIR
    if args.configDir is not None:
        configDir = args.configDir
    configManager = GlusterNagiosConfManager(
        configDir, HOST_TEMPLATE_DIR, HOST_TEMPLATE_NAME)
    return configManager


def _restartNagios():
    now = datetime.datetime.now()
    cmdStr = "[%s] RESTART_PROGRAM\n" % (now)
    submit_external_command.submitExternalCommand(cmdStr)


def _isNagiosRunning():
    (rc, out, err) = utils.execCmd([serviceCmdPath.cmd, 'nagios', 'status'])
    if rc == 0:
        return True
    else:
        return False


if __name__ == '__main__':
    args = parse_input()
    clusterdata = discoverCluster(args.hostip, args.cluster)
    configManager = getConfigManager(args)
    clusterConfing = configManager.generateNagiosConfigFromGlusterCluster(
        clusterdata)
    print " Cluster configurations re-synced successfully from host %s" % \
          (args.hostip)
    if _isNagiosRunning():
        _restartNagios()
    sys.exit(utils.PluginStatusCode.OK)
