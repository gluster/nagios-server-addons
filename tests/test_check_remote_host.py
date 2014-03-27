#
# Copyright 2014 Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301 USA
#
# Refer to the README and COPYING files for full details of the license
#

import mock
import socket

import plugins
from testrunner import PluginsTestCase as TestCaseBase


class TestCheckRemoteHost(TestCaseBase):
    # Method to test the checkLiveStatus() method
    @mock.patch('plugins.check_remote_host.livestatus.socket.socket')
    def testCheckLiveStatus(self, mock_socket):
        reference = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.assertTrue(mock_socket, "called")
        reference.recv.return_value = "0\n"
        plugins.check_remote_host.checkLiveStatus("dummy host", "dummy srvc")
        reference.connect.assert_called_with("/var/"
                                             "spool/nagios/cmd/live")
        reference.send.assert_called_with("GET services\nColumns: state\n"
                                          "Filter: description = dummy srvc\n"
                                          "Filter: host_address = "
                                          "dummy host\n"
                                          "Separators: 10 124 44 59\n")
        self.assertEquals(0,
                          plugins.
                          check_remote_host.
                          checkLiveStatus("dummy host", "dummy srvc"))
