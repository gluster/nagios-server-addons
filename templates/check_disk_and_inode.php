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

function endsWith($haystack, $needle)
{
  return $needle === "" || substr($haystack, -strlen($needle)) === $needle;
}

foreach ($this->DS as $KEY=>$VAL) {
  if ($VAL['TEMPLATE'] == "check_brick_usage") {
    $ds_name[$KEY] = "Brick Utilization";
  } else {
    $ds_name[$KEY] = "Disk Utilization";
  }
  $name[$KEY] = "Mount Path: ";
  $graph_type = $VAL['LABEL'];
  $max_limit = $VAL['MAX'];
  $unit = "GiB";
  if (endsWith($graph_type,".inode") || endsWith($graph_type,".thinpool") || endsWith($graph_type,".thinpool-metadata")) {
    list ($brick,$data_type) = explode (".", $graph_type);
    $ds_name[$KEY] .= "(";
    $ds_name[$KEY] .= $data_type;
    $ds_name[$KEY] .= ")";
    $name[$KEY] .= $brick ;
    if ($data_type == "inode"){
      $unit = "";
    }
  } else {
    $name[$KEY] .= $graph_type;
    $ds_name[$KEY] .= "(space)";
  }
  $opt[$KEY] = "--vertical-label \"%(Total: $max_limit $unit) \"  --lower-limit 0 --upper-limit 100 -r --title \"$name[$KEY]\" ";

  $def[$KEY]     = rrd::def( "var1", $VAL['RRDFILE'], $VAL['DS'], "AVERAGE" );

  $def[$KEY]    .= rrd::area( "var1", "#008000", "Brick Usage" );
  $def[$KEY] .= rrd::gprint  ("var1", array("LAST","MAX","AVERAGE"), "%.3lf %%");

  $def[$KEY] .= rrd::line2( $VAL['WARN'], "#FFA500", "Warning\\n");

  $def[$KEY] .= rrd::line2( $VAL['CRIT'], "#FF0000", "Critical\\n");
  $def[$KEY] .= rrd::comment ("   \\n");
}
?>
