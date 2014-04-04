#!/usr/bin/python
import sys
import commands
import random
import argparse
import livestatus
import os

_NRPEPath = "/usr/lib64/nagios/plugins/check_nrpe"


def excecNRPECommand(host):
    #Get the address of the host
    answer = livestatus.checkLiveStatus("GET hosts\nColumns: address\n"
                                        "Filter: display_name = "
                                        + host + "\n")
    command = (_NRPEPath + " -H " + answer.rstrip() + " -c " +
               "check_vol_utilization -a " + args.volume + " " +
               str(args.warning) + " " + str(args.critical))
    status, output = commands.getstatusoutput(command)
    return status, output


def showVolumeUtilization(args):
    table = livestatus.readLiveStatus("GET hostgroups\nColumns: members\n"
                                      "Filter: name = "
                                      + args.hostgroup + "\n")
    tab1 = table[0]
    list_hosts = tab1[0].split(",")
    #First take a random host from the group and send the request
    host = random.choice(list_hosts)
    status, output = excecNRPECommand(host)
    #if success return from here
    if "Volume Utilization" in output:
        return status, output
    #radom host is not able to execute the command
    #Now try to iterate through the list of hosts
    #in the host group and send the command until
    #the command is successful
    for host in list_hosts:
        status, output = excecNRPECommand(host)
        #if success return from here
        if "Volume Utilization" in output:
            return status, output
            break
    return status, output


def parse_input():
    parser = argparse.ArgumentParser(
        usage='%(prog)s [-h] <hostgroup>  <volume> -w <Warning> -c <Critical>')
    parser.add_argument(
        "hostgroup",
        help="Name of the hostgroup in which the volume belongs to")
    parser.add_argument(
        "volume",
        help="Name of the volume to get the Utilization")
    parser.add_argument(
        "-w",
        "--warning",
        action="store",
        type=int,
        help="Warning Threshold in percentage")
    parser.add_argument(
        "-c",
        "--critical",
        action="store",
        type=int,
        help="Critical Threshold in percentage")
    args = parser.parse_args()
    if not args.critical or not args.warning:
        print "UNKNOWN:Missing critical/warning threshold value."
        sys.exit(3)
    if args.critical <= args.warning:
        print "UNKNOWN:Critical must be greater than Warning."
        sys.exit(3)
    return args

if __name__ == '__main__':
    args = parse_input()
    status, output = showVolumeUtilization(args)
    print output
    exit(os.WEXITSTATUS(status))
