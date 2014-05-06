#!/usr/bin/python
import sys
import json
import random
import argparse
import livestatus
import os

from glusternagios import utils
import server_utils


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
    return ("check_vol_status -a %s %s" % (args.volume, 'info'))


def _getVolQuotaStatusNRPECommand(args):
    return ("check_vol_status -a %s %s" % (args.volume, 'quota'))


def _getVolSelfHealStatusNRPECommand(args):
    return ("check_vol_status -a %s %s" % (args.volume, 'self-heal'))


def _getVolGeoRepStatusNRPECommand(args):
    return ("check_vol_status -a %s %s" % (args.volume, 'geo-rep'))


def _getVolumeStatusOutput(args):
    status, output = _executeRandomHost(_getVolStatusNRPECommand(args), args)

    if status == utils.PluginStatusCode.OK:
        #Following query will return the output in format [[2,0]]
        #no.of bricks in OK state - 2 , CRITICAL state - 0
        brick_states_output = livestatus.readLiveStatusAsJSON(
            "GET services\n"
            "Filter: host_groups >= %s\n"
            "Filter: custom_variable_values >= %s\n"
            "Filter: description ~ Brick - \n"
            "Stats: state = 0\n"
            "Stats: state = 2\n"
            % (args.hostgroup, args.volume))
        brick_states = json.loads(brick_states_output)
        bricks_ok = brick_states[0][0]
        bricks_critical = brick_states[0][1]
        if bricks_ok == 0 and bricks_critical > 0:
            status = utils.PluginStatusCode.CRITICAL
            output = "All the bricks are in CRITICAL state"
        elif bricks_critical > 0:
            status = utils.PluginStatusCode.WARNING
            output = "One or more bricks are in CRITICAL state"
    return status, output


def _getVolumeQuotaStatusOutput(args):
    # get current volume quota status
    table = livestatus.readLiveStatus("GET services\n"
                                      "Columns: state long_plugin_output\n"
                                      "Filter: description = "
                                      "Volume Quota - %s" % args.volume)
    servicestatus = utils.PluginStatusCode.UNKNOWN
    statusoutput = ''
    if len(table) > 0:
        servicetab = table[0]
        servicestatus = servicetab[0]
        statusoutput = servicetab[1]
    if (int(servicestatus) == utils.PluginStatusCode.OK and
            statusoutput.find("QUOTA: OK") > -1):
        # if ok, don't poll
        return servicestatus, statusoutput
    return _executeRandomHost(_getVolQuotaStatusNRPECommand(args), args)


def execNRPECommand(command):
    status, output, err = utils.execCmd(command.split(), raw=True)
    return os.WEXITSTATUS(status), output


def _executeRandomHost(command, args):
    list_hosts = _getListHosts(args)
    host = random.choice(list_hosts)
    #Get the address of the host
    host_address = _getHostAddress(host)

    status, output = execNRPECommand(server_utils.getNRPEBaseCommand(
                                     host_address,
                                     timeout=args.timeout) + command)

    if status != utils.PluginStatusCode.UNKNOWN:
        return status, output
    #random host is not able to execute the command
    #Now try to iterate through the list of hosts
    #in the host group and send the command until
    #the command is successful
    for host in list_hosts:
        status, output = execNRPECommand(server_utils.getNRPEBaseCommand(
                                         host,
                                         timeout=args.timeout) + command)
        if status != utils.PluginStatusCode.UNKNOWN:
            return status, output
    return status, output


def showVolumeOutput(args):

    if args.option == 'status':
        return _getVolumeStatusOutput(args)
    elif args.option == 'utilization':
        command = _getVolUtilizationNRPECommand(args)
    elif args.option == 'quota':
        return _getVolumeQuotaStatusOutput(args)
    elif args.option == 'self-heal':
        command = _getVolSelfHealStatusNRPECommand(args)
    elif args.option == 'geo-rep':
        command = _getVolGeoRepStatusNRPECommand(args)

    return _executeRandomHost(command, args)


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
                                 'quota',
                                 'self-heal',
                                 'geo-rep'])
    parser.add_argument('-t', '--timeout',
                        action='store',
                        help='NRPE timeout')
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
