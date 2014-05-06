#!/usr/bin/python
# network_utils.py Network utility
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
import re
import socket
import ethtool
import logging


IPADDR_RE = re.compile(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}')
DOMAIN_RE = re.compile(
    flags=re.VERBOSE,
    pattern=r"""
    ^
    [\w\.\-\_]+
    \w+
    $
    """
)


def getNonLoopbackAddresses():
    devices = ethtool.get_active_devices()
    iplist = []

    for device in devices:
        try:
            flags = ethtool.get_flags(device)
            if flags and not (flags & ethtool.IFF_LOOPBACK):
                iplist.append(ethtool.get_ipaddr(device))
        except IOError as e:
            logging.error("unable to get ipaddr/flags for %s: %s"
                          % (device, e))
    return set(iplist)


def validateFQDNresolvability(fqdn):
    try:
        resolvedAddresses = set(socket.gethostbyname_ex(fqdn)[2])
    except socket.error:
        return "%s did not resolve into an IP address" % fqdn

    if not resolvedAddresses.issubset(getNonLoopbackAddresses()):
        return "The following addreses: '%s' can't be mapped to non " \
               "loopback devices on this host" % resolvedAddresses


def validateHostAddress(address):
    if not address:
        return "Please specify host Address"

    if IPADDR_RE.match(address):
        if not address in getNonLoopbackAddresses():
            return "Address '%s' can't be mapped to non loopback devices " \
                   "on this host" % address
        else:
            return

    if len(address) > 1000:
        return "FQDN has invalid length"

    components = address.split('.', 1)
    if len(components) < 2:
        return "Host FQDN name '%s' has no domain suffix" % address
    else:
        if not DOMAIN_RE.match(components[1]):
            return "Host FQDN name '%s' has invalid domain name" % address
    return validateFQDNresolvability(address)
