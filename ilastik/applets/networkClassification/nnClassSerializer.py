###############################################################################
#   ilastik: interactive learning and segmentation toolkit
#
#       Copyright (C) 2011-2014, the ilastik developers
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
#          http://ilastik.org/license.html
###############################################################################
import pickle
import json

import numpy as np
import typing

from tiktorch.types import Model, ModelState

from ilastik.applets.base.appletSerializer import (
    AppletSerializer,
    SerialSlot,
    SerialListSlot,
    SerialBlockSlot,
)


class BinarySlot(SerialSlot):
    """
    Implements the logic for serializing a binary slot.

    wraps value with numpy.void to avoid the following error:
    ValueError: VLEN strings do not support embedded NULLs
    """
    @staticmethod
    def _saveValue(group, name, value):
        if value:
            group.create_dataset(name, data=np.void(value))

    @staticmethod
    def _getValue(subgroup, slot):
        val = subgroup[()]
        slot.setValue(val.tobytes())


class JSONSerialzierRegistry:
    _SERIALIZER_KEY_STR = "__serializer_key"
    _SERIALIZER_DATA_STR = "__serialized_data"

    def __init__(self):
        self._serializer_by_key = {}
        self._serializer_by_type = {}

    def register_serializer(self, type_, key):

        def _register_serializer(serializer_cls):
            self._serializer_by_type[type_] = (serializer_cls, key)
            self._serializer_by_key[key] = serializer_cls
            return serializer_cls

        return _register_serializer

    registerSerializer = register_serializer

    @property
    def encoder_cls(self):
        class Encoder(json.JSONEncoder):
            def default(encoder_self, obj):
                type_ = type(obj)
                serializer_cls, key = self._serializer_by_type.get(type_, (None, None))
                if not serializer_cls:
                    raise Exception(f"No serializer for class {type} found")
                serialized_data = serializer_cls.serialize(obj)

                return {
                    self._SERIALIZER_KEY_STR: key,
                    self._SERIALIZER_DATA_STR: serialized_data,
                }

        return Encoder


    def object_hook(self, dct):
        serializer_key = dct.get(self._SERIALIZER_KEY_STR, None)

        if not serializer_key:
            return dct

        serializer_cls = self._serializer_by_key.get(serializer_key)
        if not serializer_cls:
            raise Exception(f"Unknown serializer key {serializer_key}")

        return serializer_cls.deserialize(dct.get(self._SERIALIZER_DATA_STR))


class JSONSerialSlot(SerialSlot):
    """
    Implements the logic for serializing a json serializable object slot.

    wraps value with numpy.void to avoid the following error:
    ValueError: VLEN strings do not support embedded NULLs
    """
    @staticmethod
    def _saveValue(group, name, value):
        jsonString = json.dumps(value, cls=JSONEncoder)
        group.create_dataset(name, data=np.void(value))

    @staticmethod
    def _getValue(subgroup, slot):
        val = subgroup[()]
        slot.setValue(val.tobytes())


class NNClassificationSerializer(AppletSerializer):
    def __init__(self, topLevelOperator, projectFileGroupName):
        self.VERSION = 1

        slots = [
            SerialListSlot(topLevelOperator.LabelNames),
            SerialListSlot(topLevelOperator.LabelColors, transform=lambda x: tuple(x.flat)),
            SerialListSlot(topLevelOperator.PmapColors, transform=lambda x: tuple(x.flat)),
            SerialBlockSlot(
                topLevelOperator.LabelImages,
                topLevelOperator.LabelInputs,
                topLevelOperator.NonzeroLabelBlocks,
                name="LabelSets",
                subname="labels{:03d}",
                selfdepends=False,
                shrink_to_bb=True,
            ),
            BinarySlot(topLevelOperator.ModelBinary),
        ]

        super().__init__(projectFileGroupName, slots)
