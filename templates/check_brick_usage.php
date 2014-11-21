<?php
#
# check_interfaces -- template to generate RRD graph
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

#
# set graph labels
foreach ($this->DS as $KEY=>$VAL) {
  # $VAL['NAME'] = str_replace("_","/",$VAL['NAME']);
  $ds_name[$KEY] = "Brick Utilization ";
  $graph_type = $VAL['LABEL'];
  if ($graph_type == "Thin-pool" ) {
    $ds_name[$KEY] .= "(Thin-pool)";
  }
  $name[$KEY] = "Brick Path: " . $NAGIOS__SERVICEBRICK_DIR;

  # set graph labels
  $max_limit = $VAL['MAX'];
  $opt[$KEY]     = "--vertical-label \"%(Total: $max_limit GB) \"  --lower-limit 0 --upper-limit 100 -r --title \"$name[$KEY]\" ";

  # Graph Definitions
  $def[$KEY]     = rrd::def( "var1", $VAL['RRDFILE'], $VAL['DS'], "AVERAGE" );

  # disk graph rendering
  $def[$KEY]    .= rrd::area( "var1", "#008000", "Brick Usage" );
  $def[$KEY] .= rrd::gprint  ("var1", array("LAST","MAX","AVERAGE"), "%3.4lf %S%%");
  $i = 1;
  $k = $KEY;

  # create warning line and legend
  $def[$k] .= rrd::line2( $VAL['WARN'], "#FFA500", "Warning\\n");

# create critical line and legend
  $def[$k] .= rrd::line2( $VAL['CRIT'], "#FF0000", "Critical\\n");
  $def[$k] .= rrd::comment ("   \\n");
}
?>
