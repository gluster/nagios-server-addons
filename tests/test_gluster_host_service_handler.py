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

from plugins import gluster_host_service_handler as handler
from testrunner import PluginsTestCase as TestCaseBase


class TestGlusterHostServiceHandler(TestCaseBase):
    # Method to test the checkLiveStatus() method
    @mock.patch('plugins.gluster_host_service_handler.'
                'livestatus.socket.socket')
    def testCheckLiveStatus(self, mock_socket):
        reference = mock_socket(mock_socket.AF_UNIX, mock_socket.SOCK_STREAM)
        self.assertTrue(mock_socket, "called")
        reference.recv.return_value = "0\n"
        handler.checkLiveStatus("dummy host", "dummy srvc")
        reference.connect.assert_called_with('/var/spool/nagios/cmd/live')
        reference.send.assert_called_with("GET services\nColumns: state\n"
                                          "Filter: description = dummy srvc\n"
                                          "Filter: host_address = "
                                          "dummy host\n"
                                          "Separators: 10 124 44 59\n")
        self.assertEquals(0, handler.checkLiveStatus("dummy host",
                                                     "dummy srvc"))

    @mock.patch('plugins.gluster_host_service_handler._writeNagiosCommand')
    @mock.patch('plugins.gluster_host_service_handler.datetime')
    def testUpdateHostState(self, mock_datetime, mock_write_nagios_cmd):
        mock_datetime.datetime.now.return_value = "now"

        handler.update_host_state("dummy host", "dummy srvc", 0)
        mock_write_nagios_cmd.assert_called_with("[now] "
                                                 "PROCESS_HOST_CHECK_RESULT;"
                                                 "dummy host;0;"
                                                 "Host Status OK - "
                                                 "Services in good health\n")

        handler.update_host_state("dummy host", "dummy srvc", 1)
        mock_write_nagios_cmd.assert_called_with("[now] "
                                                 "PROCESS_HOST_CHECK_RESULT;"
                                                 "dummy host;1;"
                                                 "Host Status WARNING - "
                                                 "Service(s) [\'dummy srvc\']"
                                                 " in CRITICAL state\n")

        handler.update_host_state("dummy host", "dummy srvc", 1)
        mock_write_nagios_cmd.assert_called_with("[now] "
                                                 "PROCESS_HOST_CHECK_RESULT;"
                                                 "dummy host;1;"
                                                 "Host Status WARNING - "
                                                 "Service(s) [\'dummy srvc\']"
                                                 " in CRITICAL state\n")

    @mock.patch(
        'plugins.gluster_host_service_handler._getHostMonitoringSrvcList')
    @mock.patch('plugins.gluster_host_service_handler.checkLiveStatus')
    @mock.patch('plugins.gluster_host_service_handler.update_host_state')
    def testCheckAndUpdateHostStateToUp(self,
                                        mock_update_host_state,
                                        mock_checkLiveStatus,
                                        mock_srvc_list):
        mock_checkLiveStatus.return_value = 0
        mock_srvc_list.return_value = []

        handler.check_and_update_host_state_to_up("dummy host", "dummy srvc")

        self.assertTrue(mock_checkLiveStatus, "called")
        mock_update_host_state.assert_called_with("dummy host",
                                                  "dummy srvc",
                                                  0)
