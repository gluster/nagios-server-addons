#!/usr/bin/python
#
# check_cluster_vol_usage
# Aggregated cluster capacity utilization for a
# gluster cluster
# The plugin reads status data using mk-livestatus
# Assumptions:
#  - Volume utilization service names begin with "Volume-"
#  - Host name associated is cluster name
#  - All volume utilization output is of form
#    "used=<val>;warn;crit;min;max"
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
import re
from argparse import ArgumentParser
import json

import livestatus
from glusternagios import utils


def checkVolumePerfData(clusterName):

    # Write command to socket
    cmd = ("GET services\nColumns: description host_name "
           "perf_data custom_variables\n"
           "Filter: host_name = %s\n"
           "Filter: description ~~ %s\n"
           % (clusterName, 'Volume Utilization -'))

    perf_data_output = livestatus.readLiveStatusAsJSON(cmd)
    perf_data = json.loads(perf_data_output)
    numvolumes = 0
    totalUsed = 0.0
    totalAvail = 0.0
    for row in perf_data:
        numvolumes += 1
        if len(row) <= 3:
            return 0.0, 0.0

        perf_data = row[2]
        if len(perf_data) > 2:
            perf_arr = perf_data.split(' ')
            used = perf_arr[2].split('=')[1]
            avail = perf_arr[1].split('=')[1]

            totalUsed += float(re.match(r'\d*\.?\d+', used).group())
            totalAvail += float(re.match(r'\d*\.?\d+', avail).group())
    return numvolumes, totalUsed, totalAvail

# Main method
if __name__ == "__main__":

    parser = ArgumentParser(description="Calculate the aggregate "
                            "capacity usage in cluster")
    parser.add_argument('-w', '--warning',
                        action='store',
                        type=int,
                        dest='warn',
                        help='Warning in %%',
                        default=70)
    parser.add_argument('-c', '--critical',
                        action='store',
                        type=int,
                        dest='crit',
                        help='Critical threshold Warning in %%',
                        default=95)
    parser.add_argument('-hg', '--host-group',
                        action='store',
                        type=str,
                        dest='hostgroup',
                        help='Name of cluster or hostgroup',
                        required=True)
    args = parser.parse_args()
    # Check the various performance statuses for the host
    numVolumes, used, avail = checkVolumePerfData(args.hostgroup)
    statusstr = utils.PluginStatus.OK
    exitstatus = utils.PluginStatusCode.OK
    if numVolumes == 0:
        statusstr = utils.PluginStatus.OK
        exitstatus = utils.PluginStatusCode.OK
        print ("%s - No volumes found|used=0;%s;%s;0;%s;"
               % (statusstr, args.warn, args.crit, 100))
    elif numVolumes > 0 and used == 0 and avail == 0:
        statusstr = utils.PluginStatus.UNKNOWN
        exitstatus = utils.PluginStatusCode.UNKNOWN
        print ("%s - Volume utilization data could not be read" % statusstr)
    else:
        warn = int((args.warn * avail) / 100.0)
        crit = int((args.crit * avail) / 100.0)
        usedpercent = int((used / avail) * 100.0)
        if (usedpercent >= args.warn):
            statusstr = utils.PluginStatus.WARNING
            exitstatus = utils.PluginStatusCode.WARNING
        if (usedpercent >= args.crit):
            statusstr = utils.PluginStatus.CRITICAL
            exitstatus = utils.PluginStatusCode.CRITICAL
        availGB = utils.convertSize(avail, "KB", "GB")
        print ("%s - used %s%% of available %s GB|used=%s;%s;%s;0;%s;"
               % (statusstr, usedpercent,
                  availGB, usedpercent, args.warn, args.crit, 100))

    sys.exit(exitstatus)
