#!/usr/bin/python
import sys
import commands
import random
import argparse
import livestatus
import os
from glusternagios import utils

_NRPEPath = "/usr/lib64/nagios/plugins/check_nrpe"


def _getListHosts(args):
    table = livestatus.readLiveStatus("GET hostgroups\nColumns: members\n"
                                      "Filter: name = "
                                      + args.hostgroup + "\n")
    tab1 = table[0]
    list_hosts = tab1[0].split(",")
    #First take a random host from the group and send the request
    return list_hosts


def _getHostAddress(host):
    # Get the address of the host
    host_address = livestatus.checkLiveStatus("GET hosts\nColumns: address\n"
                                              "Filter: display_name = "
                                              + host + "\n")
    return host_address.rstrip()


def _getVolUtilizationNRPECommand(args):
    return ("check_vol_utilization -a " + args.volume + " " +
            str(args.warning) + " " + str(args.critical))


def _getVolStatusNRPECommand(args):
    return ("check_vol_status -a " + args.volume)


def _getVolQuotaStatusNRPECommand(args):
    return ("check_vol_quota_status -a " + args.volume)


def _getNRPEBaseCmd(host):
    return _NRPEPath + " -H " + host + " -c "


def execNRPECommand(command):
    status, output = commands.getstatusoutput(command)
    return os.WEXITSTATUS(status), output


def _getVolumeQuotaStatusOutput(args):
    # get current volume quota status
    table = livestatus.checkLiveStatus("GET services\n"
                                       "Columns: status plugin_output\n"
                                       "Filter: service_description = "
                                       "Volume Status Quota - " + args.volume)
    servicestatus = table[0]
    statusoutput = table[1]
    if (servicestatus == utils.PluginStatusCode.OK and
            statusoutput.find("QUOTA: OK") > -1):
        # if ok, don't poll
        return servicestatus, statusoutput
    return _executeRandomHost(_getVolQuotaStatusNRPECommand(args))


def _executeRandomHost(command):
    list_hosts = _getListHosts(args)
    host = random.choice(list_hosts)
    #Get the address of the host
    host_address = _getHostAddress(host)

    status, output = execNRPECommand(_getNRPEBaseCmd(host_address) + command)

    if status != utils.PluginStatusCode.UNKNOWN:
        return status, output
    #random host is not able to execute the command
    #Now try to iterate through the list of hosts
    #in the host group and send the command until
    #the command is successful
    for host in list_hosts:
        status, output = execNRPECommand(_getNRPEBaseCmd(_getHostAddress(host))
                                         + command)
        if status != utils.PluginStatusCode.UNKNOWN:
            return status, output
    return status, output


def showVolumeOutput(args):

    if args.option == 'status':
        command = _getVolStatusNRPECommand(args)
    elif args.option == 'utilization':
        command = _getVolUtilizationNRPECommand(args)
    elif args.option == 'quota':
        return _getVolumeQuotaStatusOutput(args)

    return _executeRandomHost(command)


def parse_input():
    parser = argparse.ArgumentParser(
        usage='%(prog)s [-h] <hostgroup>  <volume> -w <Warning>'
        ' -c <Critical> [-o|--option]')
    parser.add_argument(
        "hostgroup",
        help="Name of the hostgroup to which the volume belongs")
    parser.add_argument(
        "volume",
        help="Name of the volume being queried")
    parser.add_argument(
        "-w",
        "--warning",
        action="store",
        type=int,
        default=70,
        help="Warning Threshold in percentage")
    parser.add_argument(
        "-c",
        "--critical",
        action="store",
        type=int,
        default=90,
        help="Critical Threshold in percentage")
    parser.add_argument('-o', '--option',
                        action='store',
                        help='the volume option to check',
                        choices=['utilization',
                                 'status',
                                 'quota'])
    args = parser.parse_args()
    if args.critical <= args.warning:
        print "UNKNOWN:Critical must be greater than Warning."
        sys.exit(utils.PluginStatusCode.UNKNOWN)
    return args

if __name__ == '__main__':
    args = parse_input()
    status, output = showVolumeOutput(args)
    print (output)
    exit(status)
