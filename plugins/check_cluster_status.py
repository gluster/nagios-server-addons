#!/usr/bin/python
#
# check_cluster_status
# Aggregated status for a gluster cluster
# The plugin reads status data using mk-livestatus
# Assumptions:
#  - Volume utilization service names has "Status"
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA
#

import sys
from argparse import ArgumentParser
import livestatus
from glusternagios import utils


def findClusterStatus(clusterName):
    exitStatus = utils.PluginStatusCode.OK
    # Write command to socket
    cmd = "GET services\nColumns: state\n" \
          "Filter: description ~~ %s\n" \
          "Filter: host_name = %s" % ('Volume Status -', clusterName)
    table = livestatus.readLiveStatus(cmd)
    noOfVolumesInCriticalState = 0
    noOfVolumesInUnknownState = 0
    noOfVolumesInWarningState = 0
    noOfVolumes = len(table)
    if noOfVolumes == 0:
        print "OK : No Volumes present in the cluster"
        return exitStatus
    for row in table:
        if len(row) > 0:
            if row[0] == '1':
                noOfVolumesInWarningState += 1
            elif row[0] == '2':
                noOfVolumesInCriticalState += 1
            elif row[0] == '3':
                noOfVolumesInUnknownState += 1

    if noOfVolumesInCriticalState == noOfVolumes:
        print "CRITICAL: All Volumes in the cluster are in Critical State"
        exitStatus = utils.PluginStatusCode.CRITICAL
    elif noOfVolumesInUnknownState == noOfVolumes:
        print "CRITICAL: All Volumes in the cluster are in Unknown State"
        exitStatus = utils.PluginStatusCode.CRITICAL
    elif noOfVolumesInCriticalState > 0:
        print "WARNING : Some Volumes in the cluster are in Critical State"
        exitStatus = utils.PluginStatusCode.WARNING
    elif noOfVolumesInUnknownState > 0:
        print "WARNING : Some Volumes in the cluster are in Unknown State"
        exitStatus = utils.PluginStatusCode.WARNING
    elif noOfVolumesInWarningState == noOfVolumes:
        print "WARNING : All Volumes in the cluster are in Warning State"
        exitStatus = utils.PluginStatusCode.WARNING
    elif noOfVolumesInWarningState > 0:
        print "WARNING : Some Volumes in the cluster are in Warning State"
        exitStatus = utils.PluginStatusCode.WARNING
    else:
        print "OK : None of the Volumes in the cluster are in Critical State"
    return exitStatus


def parse_input():

    parser = ArgumentParser(usage='%(prog)s [-h] <cluster>')
    parser.add_argument("cluster", help="Name of the cluster")
    args = parser.parse_args()
    return args


# Main method
if __name__ == "__main__":
    args = parse_input()
    # Find the cluster status
    exitStatus = findClusterStatus(args.cluster)
    sys.exit(exitStatus)
