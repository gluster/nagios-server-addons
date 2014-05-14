#!/usr/bin/python
# brick_status_event_handler.py Event handler for Brick status
# Service. Reschedules the check for volume status service whenever a
# brick status changes.
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
import sys
import datetime

import submit_external_command
from glusternagios import utils


GLUSTER_HOST_GROUP = "gluster-host"


def parse_input():
    parser = argparse.ArgumentParser(description="Nagios plugin to handle "
                                                 "brick status events")
    parser.add_argument('-hg', '--hostgroups', action='store',
                        dest='hostGroups',
                        type=str, required=True, help='Hostgroups')
    parser.add_argument('-st', '--statetype', action='store',
                        dest='stateType',
                        type=str, required=True, help='Service State Type')
    parser.add_argument('-v', '--volume', action='store', dest='volume',
                        type=str, required=True, help='Volume Name')
    args = parser.parse_args()
    return args


def _findClusterName(hostGroupNames):
    hostGroups = hostGroupNames.split(",")
    for hostGroup in hostGroups:
        if hostGroup != GLUSTER_HOST_GROUP:
            return hostGroup


if __name__ == '__main__':
    args = parse_input()
    if args.stateType == "SOFT":
        sys.exit(utils.PluginStatusCode.OK)
    hostName = _findClusterName(args.hostGroups)
    now = datetime.datetime.now()
    command = "SCHEDULE_SVC_CHECK"
    volumeStatusService = "Volume Status - %s" % args.volume
    cmdStr = "[%s] %s;%s;%s;%s\n" % (now, command, hostName,
                                     volumeStatusService, now)
    submit_external_command.submitExternalCommand(cmdStr)
    sys.exit(utils.PluginStatusCode.OK)
