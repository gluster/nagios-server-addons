<?php
#
# check_cluster_vol_usage -- template to generate RRD graph
# for cluster utilization plugin
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
$def[1]=""; $opt[1]=""; $ds_name[1]="";
$opt[1] = "--vertical-label \"% Usage\" -r --lower-limit 0 --upper-limit 100 --title \"$NAGIOS_HOSTNAME / $NAGIOS_SERVICEDISPLAYNAME\" --slope-mode -u 100 -N";
$ds_name[1] = "Cluster Utilization";

$def[1]  = "DEF:utilzation_in=$RRDFILE[1]:$DS[1]:AVERAGE " ;

$def[1] .= "CDEF:utilzation_out=utilzation_in ";
$def[1] .= "AREA:utilzation_out#ADD8E6:\"utilization\t\t\" ";
$def[1]  .= rrd::gprint("utilzation_out", array("LAST", "AVERAGE", "MAX"), "%6.2lf%%");

if ($WARN[1] != ""){
  $def[1] .= "LINE2:$WARN[1]#FFA500:\"Warning\\n\" ";
}
if ($CRIT[1] != ""){
  $def[1] .= "LINE2:$CRIT[1]#FF0000:\"Critical\\n\" ";
}
?>
