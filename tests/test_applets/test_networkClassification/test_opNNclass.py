import pytest

import time
import random

from unittest import mock
from concurrent.futures import ThreadPoolExecutor

from ilastik.applets.networkClassification.opNNclass import (
    OpServerFactory,
    OpModelLoad,
    OpModelPipeline,
)
from lazyflow import rtype, stype
from lazyflow.graph import Operator, InputSlot, OutputSlot
from lazyflow.classifiers import TikTorchLazyflowClassifierFactory
from types import SimpleNamespace




class TestOpOpaqueCache:
    SERVER_CONFIG = {"srv": "srvconfig"}
    MODEL_CONFIG = {"model": "Cool Test Model"}
    MODEL_BINARY = b"modelbinary"
    MODEL_STATE = b"modelstate"
    OPTIMIZER_STATE = b"optimizerstate"

    @pytest.fixture
    def op(self, graph):
        return OpModelPipeline(graph=graph)

    def test_model_pipeline_creates_server_and_loads_model(self, op):
        factory_mock = mock.Mock()
        srv_mock = mock.Mock()
        factory_mock.return_value = srv_mock
        op.ServerConfig.setValue(self.SERVER_CONFIG)
        op._srv_factory.ServerFactory.setValue(factory_mock)

        op.ModelConfig.setValue(self.MODEL_CONFIG)
        op.BinaryModel.setValue(self.MODEL_BINARY)
        op.BinaryModelState.setValue(self.MODEL_STATE)
        op.BinaryOptimizerState.setValue(self.OPTIMIZER_STATE)

        model = op.Model.value

        factory_mock.assert_called_with(self.SERVER_CONFIG)
        srv_mock.load_model.assert_called_with(
            self.MODEL_CONFIG, self.MODEL_BINARY, self.MODEL_STATE, self.OPTIMIZER_STATE
        )

    def test_real_config(self, op):
        SERVER_CONFIG = {
            "address": "127.0.0.1",
            "port1": 9999,
            "port2": 9994,
            "devices": [],
        }

        op.ServerConfig.setValue(SERVER_CONFIG)
        assert op.Server.value



# Split serialization and non serialization procedures


class OpB(Operator):
    In = InputSlot()
    Out = OutputSlot()

    def setupOutputs(self):
        print("setup b")
        self.Out.setValue(self.In.value)

    def propagateDirty(self, *args, **kwargs):
        pass

def test_a(graph):
    op_a = OpA(graph=graph)
    op_b = OpB(graph=graph)

    op_a.Out.connect(op_b.In)
    op_a.In.setValue("fadf")
    print(op_b.Out.value)

    # On serialize we get data from StoredBinaryModel
    # On deserialize we set data to BinaryModel
    # Operator one of?

# Plan:
# 0. Create test for applet serialization
# 1. Implement applet serializer for model binary/state...
# 2. Implement one of op for serialization

from ilastik.applets.base.appletSerializer import AppletSerializer, BinarySlot, SerialSlot

import json


def json_dumps_binary(value):
    return json.dumps(value, ensure_ascii=False).encode("utf-8")

def json_loads_binary(value):
    return json.loads(value.decode("utf-8"))

class ModelSlot(SerialSlot):
    def _saveValue(self, group, name, value):
        model_group = group.require_group(self.name)

        if value:
            model_group.create_dataset("code", data=value.code)
            model_group.create_dataset("state.model", data=value.state.model)
            model_group.create_dataset("state.optimizer", data=value.state.optimizer)
            model_group.create_dataset("config", data=json_dumps_binary(value.config))
        else:
            model_group.create_dataset("code", data=b'')
            model_group.create_dataset("state.model", data=b'')
            model_group.create_dataset("state.optimizer", data=b'')
            model_group.create_dataset("config", data=b'')

    def _getValue(self, dset, slot):
        code = None
        if "code" in dset:
            code = dset["code"].value

        if not code:
            slot.setValue(Model.Empty)
            return

        model = Model(
            code=dset["code"].value,
            state=State(
                model=dset["state.model"].value,
                optimizer=dset["state.optimizer"].value,
            ),
            config=json.loads(dset["config"].value),
        )
        slot.setValue(model)


class NNSerializer(AppletSerializer):
    def __init__(self, topLevelOperator, projectFileGroupName):
        self.VERSION = 1

        slots = [
            ModelSlot(topLevelOperator.Out),
        ]

        super().__init__(projectFileGroupName, slots)

import h5py

class TestModelSlotSerialization:

    class OpA(Operator):
        Out = OutputSlot()

        def setupOutputs(self):
            self.Out.meta.shape = (1,)
            self.Out.meta.dtype = object

        def execute(self, *args, **kwargs):
            pass

        def propagateDirty(self, *args, **kwargs):
            pass

    @pytest.fixture
    def op(self, graph):
        op = self.OpA(graph=graph)
        op.Out.setValue(Model(
            b"code",
            State(b"state", b"opt_state"), {"val": 1}
        ))
        return op

    @pytest.fixture
    def serializer(self, op):
        return NNSerializer(op, 'mygroup')

    @pytest.fixture
    def serialized(self, serializer, op):
        outfile = h5py.File("/tmp/data.h5", 'w')

        serializer.serializeToHdf5(outfile, None)

        yield outfile

        outfile.close()

    def test_serialization(self, graph, serialized):
        key_to_serialized = [
            ("code", b"code"),
            ("state.model", b"state"),
            ("state.optimizer", b"opt_state"),
            ("config", b'{"val": 1}'),
        ]

        for key, serialized_value in key_to_serialized:
            assert serialized[f"mygroup/Out/{key}"].value == serialized_value

    def test_deserializetion(self, graph, serialized):
        op_a = self.OpA(graph=graph)
        serializer = NNSerializer(op_a, 'mygroup')
        serializer.deserializeFromHdf5(serialized, None)

        assert op_a.Out.value == Model(b"code", State(b"state", b"opt_state"), {"val": 1})

    def test_consecutive_serialization(self, graph, serializer, serialized, op):
        op.Out.setValue(Model.Empty)

        serializer.serializeToHdf5(serialized, None)
        serializer.deserializeFromHdf5(serialized, None)

        assert not op.Out.value
        assert op.Out.value is Model.Empty


import importlib

def test_it():
    import sys
    sys = importlib.reload(sys)
