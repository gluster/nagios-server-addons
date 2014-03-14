#!/usr/bin/python
#
# livestatus.py
# Utils to query livestatus
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

import socket
from plugins import constants

_socketPath = constants.LIVESTATUS_SOCKETPATH


def readLiveStatus(cmd):
    # Change the default separators to
    # Linefeed for row, | for columns,
    # comma for lists such as contacts, semicolon for lists such as hosts
    cmd += "\nSeparators: 10 124 44 59"
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(_socketPath)

    # Write command to socket
    s.send(cmd)

    # Close socket
    s.shutdown(socket.SHUT_WR)

    # Read the answer
    answer = s.recv(1000)
    # Parse the answer into a table
    table = [line.split('|') for line in answer.split('\n')[:-1]]

    return table
