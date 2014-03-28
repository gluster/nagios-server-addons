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
import commands
import json
import datetime
import re
from config_generator import GlusterNagiosConfManager

#from glusternagios import utils
from constants import DEFAULT_AUTO_CONFIG_DIR
from constants import HOST_TEMPLATE_DIR
from constants import HOST_TEMPLATE_NAME
from constants import NRPE_PATH
from constants import NAGIOS_COMMAND_FILE_PATH


def excecNRPECommand(command):
    """
    This function executes NRPE command and return the result
    """
    status = commands.getoutput(command)
    return status


def discoverhostdetails(host, args):
    hostparamsdict = {}
    command = NRPE_PATH + " -H " + host + " -c discoverhostparams"
    hostparams = excecNRPECommand(command)
    #convert to dictionary
    try:
        hostparamsdict = json.loads(hostparams)
    except Exception, e:
        e.args += (hostparams,)
        raise
    return hostparamsdict


def discoverlogicalcomponents(host):
    componentlist = []
    command = NRPE_PATH + " -H " + host + " -c discoverlogicalcomponents"
    components = excecNRPECommand(command)
    try:
        componentlist = json.loads(components)
    except Exception, e:
        e.args += (components,)
        #print e.args
        raise
    return componentlist


def discovercluster(args):
    """

    :rtype : None
    """
    ipPat = re.compile("^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
    clusterdata = {}
    #Discover the logical components
    componentlist = discoverlogicalcomponents(args.hostip)
    #Discover the peers
    command = NRPE_PATH + " -H " + args.hostip + " -c discoverpeers"
    hosts = excecNRPECommand(command)
    hostlist = json.loads(hosts)

    #Add the ip address of the root node to the peer list
    #to generate the configuration
    hostlist.append({"hostip": args.hostip})
    for host in hostlist:
        if(ipPat.match(host['hostip'])):
            host.update(discoverhostdetails(host['hostip'], args))
            #Get the list of bricks for this host and add to dictionary
            host['bricks'] = \
                [brick for brick in componentlist
                 if brick["hostip"] == host['hostip']]
    clusterdata['hosts'] = hostlist
    clusterdata['volumes'] =\
        [volume for volume in componentlist
         if volume["srvctype"] == "volume"]
    clusterdata['name'] = args.cluster
    return clusterdata


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


def __restartNagios():
    now = datetime.datetime.now()
    cmdStr = "[%s] RESTART_PROGRAM\n" % (now)
    with open(NAGIOS_COMMAND_FILE_PATH, "w") as f:
        f.write(cmdStr)


if __name__ == '__main__':
    args = parse_input()
    clusterdata = discovercluster(args)
    configManager = getConfigManager(args)
    clusterConfing = configManager.generateNagiosConfigFromGlusterCluster(
        clusterdata)
    print " Cluster configurations re-synced successfully from host %s" % \
          (args.hostip)
    __restartNagios()
