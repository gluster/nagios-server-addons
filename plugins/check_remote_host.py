#!/usr/bin/python
#
# check_remote_host.py -- nagios plugin uses Mklivestatus to get the overall
#                         status
# of a host. The services considered by default for the status of the host
# are -
# 	1. LV/Inode Service status
#	2. CPU Utilization
#	3. Memory Utilization
#	4. Network Utilization
#	5. Swap Utilization
#
# Copyright (C) 2014 Red Hat Inc
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301,USA
#

import os
import sys
import getopt
#import socket
import json

import livestatus

STATUS_OK = 0
STATUS_WARNING = 1
STATUS_CRITICAL = 2
STATUS_UNKNOWN = 3
_commandStatusStrs = {STATUS_OK: 'OK', STATUS_WARNING: 'WARNING',
                      STATUS_CRITICAL: 'CRITICAL', STATUS_UNKNOWN: 'UNKNOWN'}


# Load the host monitoring services list
def loadSrvcList():
    srvc_list = []
    with open("/etc/nagios/gluster/host-monitoring-services.in") as data_file:
        srvc_list = json.load(data_file)['serviceList']
    return srvc_list


# Method to execute livestatus
def checkLiveStatus(hostAddr, srvc):
    cmd = "GET services\nColumns: state\nFilter: " \
          "description = %s\n" \
          "Filter: host_address = %s" % (srvc, hostAddr)

    table = livestatus.readLiveStatus(cmd)

    if len(table) > 0 and len(table[0]) > 0:
        return int(table[0][0])
    else:
        return STATUS_UNKNOWN


# Method to show the usage
def showUsage():
    usage = "Usage: %s -H <Host Address>\n" % os.path.basename(sys.argv[0])
    sys.stderr.write(usage)


# Main method
if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hH:", ["help", "host="])
    except getopt.GetoptError as e:
        print (str(e))
        showUsage()
        sys.exit(STATUS_CRITICAL)

    hostAddr = ''
    if len(opts) == 0:
        showUsage()
        sys.exit(STATUS_CRITICAL)
    else:
        for opt, arg in opts:
            if opt in ("-h", "--help"):
                showUsage()
                sys.exit()
            elif opt in ("-H", "--host"):
                hostAddr = arg
            else:
                showUsage()
                sys.exit(STATUS_CRITICAL)

    # Load the services list
    srvc_list = loadSrvcList()

    # Calculate the consolidated status for the host based on above
    # status of individual services
    finalStatus = STATUS_OK
    criticalSrvcs = []
    for srvc in srvc_list:
        srvc_status = checkLiveStatus(hostAddr, srvc)
        finalStatus = finalStatus | srvc_status
        if srvc_status == STATUS_CRITICAL:
            criticalSrvcs.append(srvc)

    # Return the status
    if finalStatus == STATUS_CRITICAL:
        print "Host Status %s - Service(s) %s in CRITICAL state" % \
            (_commandStatusStrs[STATUS_WARNING], criticalSrvcs)
        sys.exit(STATUS_WARNING)

    print "Host Status %s - Services in good health" % \
        _commandStatusStrs[STATUS_OK]
    sys.exit(STATUS_OK)
