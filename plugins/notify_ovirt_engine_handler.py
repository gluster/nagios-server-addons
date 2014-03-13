#!/usr/bin/python
#
# notify_ovirt_engine_handler.py -- Event handler which notifies
# nagios events to Ovirt engine using external events Rest API in Ovirt
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

import argparse
import cpopen
import datetime
from glusternagios.utils import HostStatus
from glusternagios.utils import PluginStatus
import json
from subprocess import PIPE
import sys


COOKIES_FILE = "/tmp/cookies.txt"


class OvirtEventSeverity:
    NORMAL = "NORMAL"
    ALERT = "ALERT"


def postOvirtExternalEvent(serverUrl, username, password, bodyData,
                           certFile, cookie):
    externalCommand = ["curl", "--request", "POST", "--header",
                       "Accept: application/json", "--header",
                       "Content-Type: application/xml", "--header",
                       "Prefer: persistent-auth"]
    if certFile is not None:
        externalCommand.extend(["--cacert", certFile])
    else:
        externalCommand.append("--insecure")
    externalCommand.extend(["--user", "%s:%s" % (username, password),
                            "--cookie", cookie, "--cookie-jar",
                            cookie, "--data", bodyData,
                            "%s/events" % (serverUrl)])
    process = cpopen.Popen(externalCommand, stdout=PIPE, stderr=PIPE)
    output = process.communicate()[0]
    return output


def composeEventMessage(glusterEntity, service, host, cluster, status):
    messages = {'Host': "Host '%s' in cluster '%s' is %s" %
                (host, cluster, status),
                'Volume': "Volume  '%s' in cluster '%s' is %s" %
                (host, cluster, status),
                'Brick': "Brick '%s' in host '%s' in cluster '%s' is %s" %
                (service, host, cluster, status),
                'Cluster': "Cluster '%s' is %s" % (host, status),
                'Service': "%s in host '%s' in cluster '%s' is %s" %
                (service, host, cluster, status),
                }

    return messages.get(glusterEntity)


def processNagiosEvent(cluster, host, service, glusterEntity, status,
                       globalEventId, ovirtEngineUrl,
                       username, password, certFile):
        severity = OvirtEventSeverity.NORMAL

        if status == PluginStatus.CRITICAL or status == HostStatus.DOWN:
                severity = OvirtEventSeverity.ALERT

        description = composeEventMessage(glusterEntity, service,
                                          host, cluster, status)
        bodyData = "<event><origin>Nagios</origin><severity>%s</severity>" \
                   "<description>%s</description>" \
                   "<custom_id>%s</custom_id></event>" \
                   % (severity, description, globalEventId)
        return postOvirtExternalEvent(ovirtEngineUrl, username, password,
                                      bodyData, certFile, COOKIES_FILE)


def handleNagiosEvent(args):
    # Notifies Ovirt Engine about service/host state change
    exitStatus = 0
    if args.eventId is None:
        t = datetime.datetime.now()
        args.eventId = int(t.strftime("%s"))
    try:
        response = processNagiosEvent(args.cluster, args.host,
                                      args.service, args.glusterEntity,
                                      args.status, args.eventId,
                                      args.ovirtEngineUrl, args.username,
                                      args.password, args.certFile)
        responseData = json.loads(response)
        if responseData.get("id") is None:
            print "Failed to submit event %s to ovirt engine at %s" \
                % (args.eventId, args.ovirtEngineUrl)
            exitStatus = -1
        else:
            print "Nagios event %s posted to ovirt engine  %s " \
                % (args.eventId, responseData['href'])

    except Exception as exp:
        print (str(exp))
        exitStatus = -1

    return exitStatus


# Method to parse the arguments
def createParser():
    parser = argparse.ArgumentParser(prog="notify_ovirt_engine_handler.py",
                                     description="Notifies Nagios events to "
                                     "ovirt engine through external events "
                                     "REAT API")
    parser.add_argument('-c', '--cluster', action='store', dest='cluster',
                        type=str, required=True, help='Cluster name')
    parser.add_argument('-H', '--host', action='store', dest='host',
                        type=str, required=False, help='Host name')
    parser.add_argument('-g', '--glusterEntity', action='store',
                        dest='glusterEntity', type=str,
                        required=True, help='Gluster entity')
    parser.add_argument('-s', '--service', action='store', dest='service',
                        type=str, required=False, help='Service name')
    parser.add_argument('-t', '--status', action='store', dest='status',
                        type=str, required=True, help='Status')
    parser.add_argument('-e', '--eventId', action='store', dest='eventId',
                        type=str, required=False,
                        help='Global Nagios event ID')
    parser.add_argument('-o', '--ovirtServer', action='store',
                        dest='ovirtEngineUrl', type=str,
                        required=True, help='Ovirt Engine Rest API URL')
    parser.add_argument('-u', '--username', action='store', dest='username',
                        type=str, required=True, help='Ovirt user name')
    parser.add_argument('-p', '--password', action='store', dest='password',
                        type=str, required=False, help='Ovirt password')
    parser.add_argument('-C', '--cert_file', action='store', dest='certFile',
                        type=str, required=False,
                        help='CA certificate of the Ovirt Engine')
    return parser

# Main Method
if __name__ == "__main__":
    parser = createParser()
    arguments = parser.parse_args()
    return_status = handleNagiosEvent(arguments)
    sys.exit(return_status)
