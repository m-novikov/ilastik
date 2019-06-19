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
from lazyflow.graph import Graph
from lazyflow.graph import Operator, InputSlot, OutputSlot
from lazyflow.classifiers import TikTorchLazyflowClassifierFactory
from types import SimpleNamespace


@pytest.fixture
def graph():
    return Graph()


@pytest.fixture
def op(graph):
    return OpServerFactory(graph=graph)


def test_factory(op):
    def factory(conf):
        time.sleep(random.random() * 0.1)
        return SimpleNamespace(**conf)

    factory_spy = mock.Mock(wraps=factory)

    op.ServerConfig.setValue({"val": 1})
    op.ServerFactory.setValue(factory_spy)

    with ThreadPoolExecutor(max_workers=4) as ex:
        list(ex.map(lambda _: op.Server.value, range(4)))

    factory_spy.assert_called_once()
    srv = op.Server.value
    assert srv.val == 1


def test_factory_default_value_is_tiktorch_factory(op):
    assert op.ServerFactory.value is TikTorchLazyflowClassifierFactory


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
