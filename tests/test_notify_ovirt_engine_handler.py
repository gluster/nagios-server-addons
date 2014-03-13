#!/usr/bin/python
# Copyright 2014 Red Hat, Inc.
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

import cpopen
import mock
from plugins import notify_ovirt_engine_handler
import subprocess
from testrunner import PluginsTestCase as TestCaseBase


class TestOvirtNotificationHandler(TestCaseBase):
    # Method to test the post_ovirt_external_event() method
    @mock.patch('plugins.notify_ovirt_engine_handler.cpopen.Popen')
    def testPostOvirtExternalEvent(self, mock_popen):
        reference = cpopen.Popen('any command',
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        out = "sample output"
        err = ""
        reference.communicate.return_value = (out, err)
        response = notify_ovirt_engine_handler.postOvirtExternalEvent(
            "http://ovirt.com", "test", "test", "test",
            "test/test-cert", "test/cookie")
        reference.communicate.assert_called_with()
        mock_popen.assert_called_with(
            ['curl', '--request', 'POST', '--header',
             'Accept: application/json', '--header',
             'Content-Type: application/xml', '--header',
             'Prefer: persistent-auth', '--cacert', 'test/test-cert',
             '--user', 'test:test', '--cookie', 'test/cookie', '--cookie-jar',
             'test/cookie', '--data', 'test', 'http://ovirt.com/events'],
            stderr=-1, stdout=-1)
        self.assertEquals(out, response, "Invalid response")

    # Method to test the post_ovirt_external_event() method
    @mock.patch('plugins.notify_ovirt_engine_handler.postOvirtExternalEvent')
    def testProcessNagiosEvent(self, mock_postOvirtExternalEvent):
            notify_ovirt_engine_handler.processNagiosEvent(
                "test-cluster1", "node-1", "Test-Service", "Service",
                "CRITICAL", "100", "http://ovirt.com", "test-user",
                "test-pwd", "test/cert")

            mock_postOvirtExternalEvent.assert_called_with(
                'http://ovirt.com', 'test-user', 'test-pwd',
                "<event><origin>Nagios</origin><severity>ALERT</severity>"
                "<description>Test-Service in host 'node-1' in cluster"
                " 'test-cluster1' is CRITICAL</description><custom_id>100"
                "</custom_id></event>", 'test/cert', '/tmp/cookies.txt')

    def _verifyArguments(self, args, argsExpected):
        self.assertEquals(args.cluster, argsExpected["cluster"])
        self.assertEquals(args.host, argsExpected["host"])
        self.assertEquals(args.glusterEntity, argsExpected["glusterEntity"])
        self.assertEquals(args.service, argsExpected["service"])
        self.assertEquals(args.status, argsExpected["status"])
        self.assertEquals(args.eventId, argsExpected["eventId"])
        self.assertEquals(args.ovirtEngineUrl, argsExpected["ovirtEngineUrl"])
        self.assertEquals(args.username, argsExpected["username"])
        self.assertEquals(args.password, argsExpected["password"])
        self.assertEquals(args.certFile, argsExpected["certFile"])

    # Method to test the argument parsing
    def testArgumentParser(self):
        parser = notify_ovirt_engine_handler.createParser()
        argsInput = {"cluster": "Test-Cluster", "host": "Test-Node",
                     "glusterEntity": "Service", "service": "Test-Service",
                     "status": "OK", "eventId": "123",
                     "ovirtEngineUrl": "http://test.com:8080",
                     "username": "test", "password": "test",
                     "certFile": "/test/certfile"}
        args = parser.parse_args(
            ['-c', argsInput["cluster"], '-H', argsInput["host"],
             '-g', argsInput["glusterEntity"], '-s', argsInput["service"],
             '-t', argsInput["status"], '-e', argsInput["eventId"],
             '-o', argsInput["ovirtEngineUrl"], '-u', argsInput["username"],
             '-p', argsInput["password"], '-C', argsInput["certFile"]])
        self._verifyArguments(args, argsInput)
