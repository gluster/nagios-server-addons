#!/usr/bin/python
import sys
import json
import random
import argparse
import livestatus

from glusternagios import utils
import server_utils


def _getListHosts(hostgroup):
    table = livestatus.readLiveStatus("GET hostgroups\nColumns: members\n"
                                      "Filter: name = "
                                      + hostgroup + "\n")
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


def _getVolUtilizationNRPECommand(volume, warning, critical):
    return ("check_vol_utilization -a " + volume + " " +
            str(warning) + " " + str(critical))


def _getVolStatusNRPECommand(volume):
    return ("check_vol_status -a %s %s" % (volume, 'info'))


def _getVolQuotaStatusNRPECommand(volume):
    return ("check_vol_status -a %s %s" % (volume, 'quota'))


def _getVolSelfHealStatusNRPECommand(volume):
    return ("check_vol_status -a %s %s" % (volume, 'self-heal'))


def _getVolGeoRepStatusNRPECommand(volume):
    return ("check_vol_status -a %s %s" % (volume, 'geo-rep'))


#This function gets the replica pairs
#bricks - list of bricks in the volume
#pair_index - nth pair of replica's needs to be returned
#rCount - replica count
def getReplicaSet(bricks, pair_index, rCount):
    start_index = (pair_index*rCount)-rCount
    return(bricks[start_index:start_index+rCount])


def _getVolDetailNRPECommand(volume):
    return ("discover_volume_info -a %s" % (volume))


def _getVolumeStatusOutput(hostgroup, volume):
    status, output = _executeRandomHost(hostgroup,
                                        _getVolStatusNRPECommand(volume))
    if status == utils.PluginStatusCode.OK:
        brick_details = json.loads(livestatus.readLiveStatusAsJSON(
            "GET services\n"
            "Columns: description state host_address host_name\n"
            "Filter: host_groups >= %s\n"
            "Filter: custom_variable_values >= %s\n"
            "Filter: description ~ Brick - \n"
            % (hostgroup, volume)))
        #output will be as below:
        #[[u'Brick - /root/b3', 0, u'10.70.42.246', u'nishanth-rhs-2']]
        #parse this to find the no of critical/ok bricks and list of
        #critical bricks
        bricks_ok = 0
        bricks_critical = 0
        brick_list_critical = []
        for brick_detail in brick_details:
            if brick_detail[1] == utils.PluginStatusCode.OK:
                bricks_ok += 1
            elif brick_detail[1] == utils.PluginStatusCode.CRITICAL:
                bricks_critical += 1
                #get the critical brick's host uuid if not present
                #int the list
                custom_vars = json.loads(livestatus.readLiveStatusAsJSON(
                    "GET hosts\n"
                    "Columns: custom_variables\n"
                    "Filter: groups >= %s\n"
                    "Filter: name = %s\n"
                    % (hostgroup, brick_detail[3])))
                brick_dict = {}
                brick_dict['brick'] = brick_detail[2] + ":" + \
                    brick_detail[0][brick_detail[0].find("/"):]
                brick_dict['uuid'] = custom_vars[0][0]['HOST_UUID']
                brick_list_critical.append(brick_dict)
        #Get volume details
        nrpeStatus, nrpeOut = _executeRandomHost(
            hostgroup, _getVolDetailNRPECommand(volume))
        volInfo = json.loads(nrpeOut)
        #Get the volume type
        vol_type = volInfo[volume]['type']
        if bricks_ok == 0 and bricks_critical > 0:
            status = utils.PluginStatusCode.CRITICAL
            output = "CRITICAL: Volume : %s type - All bricks " \
                     "are down " % (vol_type)
        elif bricks_ok > 0 and bricks_critical == 0:
            status = utils.PluginStatusCode.OK
            output = "OK: Volume : %s type - All bricks " \
                     "are Up " % (vol_type)
        elif bricks_critical > 0:
            if (vol_type == "DISTRIBUTE"):
                status = utils.PluginStatusCode.CRITICAL
                output = "CRITICAL: Volume : %s type \n Brick(s) - <%s> " \
                         "is|are down " % \
                         (vol_type, ', '.join(dict['brick']for dict in
                                              brick_list_critical))
            elif (vol_type == "DISTRIBUTED_REPLICATE" or
                    vol_type == "REPLICATE"):
                output = "WARNING: Volume : %s type \n Brick(s) - <%s> " \
                         "is|are down, but replica pair(s) are up" % \
                         (vol_type, ', '.join(dict['brick']for dict in
                                              brick_list_critical))
                status = utils.PluginStatusCode.WARNING
                bricks = []
                for brick in volInfo[volume]['bricks']:
                    bricks.append(
                        {'brick': brick['brickaddress'] + ":" +
                            brick['brickpath'], 'uuid': brick['hostUuid']})
                #check whether the replica is up for the bricks
                # which are down
                rCount = int(volInfo[volume]['replicaCount'])
                noOfReplicas = len(bricks)/rCount
                for index in range(1, noOfReplicas+1):
                    replica_list = getReplicaSet(bricks, index, rCount)
                    noOfBricksDown = 0
                    for brick in replica_list:
                        for brick_critical in brick_list_critical:
                            if brick.get('uuid') == brick_critical.get('uuid')\
                                    and brick.get('brick').split(':')[1] == \
                                    brick_critical.get('brick').split(':')[1]:
                                noOfBricksDown += 1
                                break
                    if noOfBricksDown == rCount:
                        output = "CRITICAL: Volume : %s type \n Bricks " \
                                 "- <%s> are down, along with one or more " \
                                 "replica pairs" % \
                                 (vol_type,
                                  ', '.join(dict['brick']for dict in
                                            brick_list_critical))
                        status = utils.PluginStatusCode.CRITICAL
                        break
            else:
                output = "WARNING: Volume : %s type \n Brick(s) - <%s> " \
                         "is|are down" % (vol_type,
                                          ', '.join(dict['brick']
                                                    for dict in
                                                    brick_list_critical))
                status = utils.PluginStatusCode.WARNING
        return status, output
    return status, output


def _getVolumeQuotaStatusOutput(hostgroup, volume):
    # get current volume quota status
    table = livestatus.readLiveStatus("GET services\n"
                                      "Columns: state long_plugin_output\n"
                                      "Filter: description = "
                                      "Volume Quota - %s" % volume)
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
    return _executeRandomHost(hostgroup, _getVolQuotaStatusNRPECommand(volume))


def execNRPECommand(command):
    status, output, err = utils.execCmd(command.split(), raw=True)
    return status, output


def _executeRandomHost(hostgroup, command):
    list_hosts = _getListHosts(hostgroup)
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
        return _getVolumeStatusOutput(args.hostgroup, args.volume)
    elif args.option == 'utilization':
        command = _getVolUtilizationNRPECommand(
            args.volume, args.warning, args.critical)
    elif args.option == 'quota':
        return _getVolumeQuotaStatusOutput(args.hostgroup, args.volume)
    elif args.option == 'self-heal':
        command = _getVolSelfHealStatusNRPECommand(args.volume)
    elif args.option == 'geo-rep':
        command = _getVolGeoRepStatusNRPECommand(args.volume)

    return _executeRandomHost(args.hostgroup, command)


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
