#!/usr/bin/python
# server_utils.py Utility methods used by nagios-server-addons module
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
import sys
import json
import datetime
from pynag import Model

from glusternagios import utils
import submit_external_command
from constants import NRPE_PATH
from constants import NAGIOS_PATH


serviceCmdPath = utils.CommandPath("service", "/sbin/service", )
nrpeCmdPath = utils.CommandPath("check_nrpe", NRPE_PATH, )
nagiosCmdPath = utils.CommandPath("nagios", NAGIOS_PATH, )


def restartNagios():
    now = datetime.datetime.now()
    cmdStr = "[%s] RESTART_PROGRAM\n" % (now)
    submit_external_command.submitExternalCommand(cmdStr)


def isNagiosRunning():
    (rc, out, err) = utils.execCmd([serviceCmdPath.cmd, 'nagios', 'status'])
    if rc == 0:
        return True
    else:
        return False


def getServiceConfig(serviceDesc, hostName):
    serviceConfig = Model.Service.objects.filter(
        service_description=serviceDesc, host_name=hostName)
    if serviceConfig:
        return serviceConfig[0]
    else:
        return None


def getServiceConfigByHost(hostName):
    serviceConfigs = Model.Service.objects.filter(host_name=hostName)
    return serviceConfigs


def getHostConfigByName(hostName):
    hostConfigs = Model.Host.objects.filter(host_name=hostName)
    if hostConfigs:
        return hostConfigs[0]
    else:
        return None


def getHostConfigsForCluster(clusterName):
    hostgroup = getHostGroup(clusterName)
    if hostgroup:
        return hostgroup.get_effective_hosts()
    else:
        return []


def getHostGroup(name):
    hostgroup = Model.Hostgroup.objects.filter(hostgroup_name=name)
    if hostgroup:
        return hostgroup[0]
    else:
        return None


def getUuidToHostConfigDict():
    hostConfigs = Model.Host.objects.all
    resultDict = {}
    for hostConfig in hostConfigs:
        if hostConfig.get("_HOST_UUID", None) is not None:
            resultDict[hostConfig.get("_HOST_UUID")] = hostConfig
    return resultDict


def getNRPEBaseCommand(host, timeout=None):
    command = NRPE_PATH + " -H " + host
    if timeout is not None:
        command += " -t %s" % timeout
    command += " -c "
    return command


def execNRPECommand(host,
                    command,
                    arguments=None,
                    timeout=None,
                    json_output=True):
    nrpeCmd = getNRPEBaseCommand(host, timeout).split()
    nrpeCmd.append(command)
    if arguments:
        nrpeCmd.append('-a')
        nrpeCmd.extend(arguments)
    (returncode, outputStr, err) = utils.execCmd(nrpeCmd, raw=True)
    if returncode == 0:
        if json_output:
            try:
                resultDict = json.loads(outputStr)
            except Exception as e:
                e.args += (outputStr,)
                raise
            return resultDict
        else:
            return outputStr
    else:
        print "Failed to execute NRPE command '%s' in host '%s' " \
              "\nError : %s" \
              "Make sure NRPE server in host '%s' is configured to accept " \
              "requests from Nagios server" % (command, host, outputStr, host)
        sys.exit(utils.PluginStatusCode.CRITICAL)
