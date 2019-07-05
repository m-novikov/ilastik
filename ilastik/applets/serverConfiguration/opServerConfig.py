###############################################################################
#   ilastik: interactive learning and segmentation toolkit
#
#       Copyright (C) 2011-2019, the ilastik team
#                                <team@ilastik.org>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# In addition, as a special exception, the copyright holders of
# ilastik give you permission to combine ilastik with applets,
# workflows and plugins which are not covered under the GNU
# General Public License.
#
# See the LICENSE file for details. License information is also available
# on the ilastik web site at:
#           http://ilastik.org/license.html
###############################################################################
from ilastik.utility.operatorSubView import OperatorSubView
from lazyflow.graph import Operator, InputSlot, OutputSlot
from lazyflow import stype

from typing import Optional, Dict

LOCAL = "local"
REMOTE = "remote"

LOCAL_SERVER_CONFIG = {
    "name": "Local",
    "type": LOCAL,
    "config": {
        "address": "localhost",
        "port1": "5556",
        "port2": "5557",
        "devices": []
    }
}

LOCAL_SERVER_CONFIG = {
    "name": "Remote",
    "type": REMOTE,
    "config": {
        "username": "",
        "ssh_key": "",
        "address": "",
        "port1": "5556",
        "port2": "5557",
        "devices": []
    }
}


class OpServerConfig(Operator):
    name = "OpServerConfig"
    category = "top-level"

    ServerConfigs = InputSlot(value=[], stype=stype.Opaque)
    Selection = InputSlot()

    ServerConfig = OutputSlot()

    def setupOutputs(self):
        configs = self.ServerConfigs.value
        selection = self.Selection.value
        self.ServerConfig.setValue(configs[selection])

    def propagateDirty(self, slot, subindex, roi):
        pass

    def execute(self, slot, subindex, roi, result):
        pass

    def addLane(self, laneIndex):
        pass

    def removeLane(self, laneIndex, finalLength):
        pass

    def getLane(self, laneIndex):
        return OperatorSubView(self, laneIndex)
