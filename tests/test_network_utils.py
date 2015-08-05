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

from plugins import network_utils
from testrunner import PluginsTestCase as TestCaseBase


class TestNetworkUtils(TestCaseBase):
    def mockGetFlags(self, device):
        if device == 'lo':
            return 73
        else:
            return 4163

    def mockGetDevices(self):
        return ['lo', 'etho', 'eth1']

    def mockGetIpAddr(self, device):
        if device == 'lo':
            return '127.0.0.1'
        else:
            return '10.70.42.1'

    def mockGethostbyname_ex(self, host):
        if host == 'test.host.com':
            return host, [], ['10.70.42.1']
        else:
            return host, [], ['82.94.164.162']

    def setUpMocks(self):
        network_utils.ethtool.get_active_devices = self.mockGetDevices
        network_utils.ethtool.get_flags = self.mockGetFlags
        network_utils.ethtool.get_ipaddr = self.mockGetIpAddr
        network_utils.socket.gethostbyname_ex = self.mockGethostbyname_ex

    # Methods to test validateHostAddress(address)
    def testValidateHostAddressWithEmptyAddress(self):
        self.setUpMocks()
        validationMsg = network_utils.validateHostAddress(None)
        self.assertEqual('Please specify host Address', validationMsg)

    def testValidateHostAddressWithLoopBackAddress(self):
        self.setUpMocks()
        validationMsg = network_utils.validateHostAddress("127.0.0.1")
        self.assertEqual("Address '127.0.0.1' can't be mapped to non loopback "
                         "devices on this host", validationMsg)

    def testValidateHostAddressWithValidAddress(self):
        self.setUpMocks()
        validationMsg = network_utils.validateHostAddress("10.70.42.1")
        self.assertEqual(None, validationMsg)

    def testValidateHostAddressWithInvalidFQDN(self):
        self.setUpMocks()
        validationMsg = network_utils.validateHostAddress("this-is-"
                                                          "invalid-fqdn")
        self.assertEqual("Host FQDN name 'this-is-invalid-fqdn' has no domain "
                         "suffix", validationMsg)

        validationMsg = network_utils.validateHostAddress("this.is."
                                                          "invalid.fqdn.")
        self.assertEqual("Host FQDN name 'this.is.invalid.fqdn.' has invalid "
                         "domain name", validationMsg)

        validationMsg = network_utils.validateHostAddress("test.host."
                                                          "com.notfound")
        self.assertEqual("The following addreses: 'set(['82.94.164.162'])' "
                         "can't be mapped to non loopback devices on this "
                         "host", validationMsg)

    def testValidateHostAddressWithValidFQDN(self):
        self.setUpMocks()
        validationMsg = network_utils.validateHostAddress("test.host.com")
        self.assertEqual(None, validationMsg)
