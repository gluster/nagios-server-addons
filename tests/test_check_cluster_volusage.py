#
# Copyright 2014 Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301 USA
#
# Refer to the README and COPYING files for full details of the license
#

import mock

from testrunner import PluginsTestCase as TestCaseBase
from plugins import check_cluster_vol_usage


class TestClusterVolUsage(TestCaseBase):

    # Method to test volume perf data when no matching host method
    @mock.patch('plugins.livestatus.readLiveStatus')
    def test_checkVolumePerfDataNoMatch(self, mock_readLiveStatus):
        mock_readLiveStatus.return_value = _getTable()
        testTotalUsed, testTotalAvail = (check_cluster_vol_usage
                                         .checkVolumePerfData
                                         ("dummy-cluster"))
        assert testTotalUsed == 0

    # Method to test volume perf data when no matching host method
    @mock.patch('plugins.livestatus.readLiveStatus')
    def test_checkVolumePerfDataMatch(self, mock_readLiveStatus):
        mock_readLiveStatus.return_value = _getTable()
        testTotalUsed, testTotalAvail = (check_cluster_vol_usage
                                         .checkVolumePerfData
                                         ("test-cluster"))
        print ("testTotal %s" % testTotalUsed)
        assert (testTotalUsed == 700)
        assert (testTotalAvail == 1134)

    # Method to test volume perf data when no matching host method
    @mock.patch('plugins.livestatus.readLiveStatus')
    def test_checkVolumePerfNoData(self, mock_readLiveStatus):
        mock_readLiveStatus.return_value = _getTableWithoutCustomAndPerData()
        testTotalUsed, testTotalAvail = (check_cluster_vol_usage
                                         .checkVolumePerfData
                                         ("test-cluster"))
        assert testTotalUsed == 0


def _getTable():
    table = [["Volume Utilization - data-vol",
              "test-cluster",
              "utilization=4%;70;90 total=734 used=300 free=434",
              "VOL_NAME;data-vol"],
             ["Volume Utilization - dist-rep",
              "test-cluster",
              "utilization=100%;70;90 total=400 used=400 free=0",
              "VOL_NAME;dist-rep"]]
    return table


def _getTableWithoutCustomAndPerData():
    table = [["brick1",
              "test-cluster",
              "",
              ""],
             ["brick2",
              "test-cluster",
              "",
              ""]]
    return table
