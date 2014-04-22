#!/usr/bin/python
# submit_external_command.py Nagios plugin to submit external command
# to nagios
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

from glusternagios import utils
from constants import NAGIOS_COMMAND_FILE_PATH


def parse_input():
    parser = argparse.ArgumentParser(description="Nagios external "
                                                 "command submission tool")
    parser.add_argument('-c', '--command', action='store', dest='command',
                        type=str, required=True, help='External Command')
    parser.add_argument('-H', '--hostName', action='store', dest='hostName',
                        type=str, required=True, help='Host Name')
    parser.add_argument('-s', '--service', action='store', dest='service',
                        type=str, required=False,
                        help='Service Description')
    parser.add_argument('-t', '--time', action='store', dest='dateTime',
                        type=str, required=True,
                        help='Service Description')
    args = parser.parse_args()
    return args


def submitExternalCommand(cmdStr):
    with open(NAGIOS_COMMAND_FILE_PATH, "w") as f:
        f.write(cmdStr)


if __name__ == '__main__':
    args = parse_input()
    cmdStr = "[%s] %s;%s;%s;%s\n" % (args.dateTime, args.command,
                                     args.hostName, args.service,
                                     args.dateTime)
    submitExternalCommand(cmdStr)
    sys.exit(utils.PluginStatusCode.OK)
