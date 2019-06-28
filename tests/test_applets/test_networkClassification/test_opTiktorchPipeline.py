import random
import time

from types import SimpleNamespace
from unittest import mock
from concurrent.futures import ThreadPoolExecutor

import pytest

from ilastik.applets.networkClassification.opTiktorchPipeline import OpModelPipeline, OpServerFactory, OpModelLoad
from ilastik.applets.networkClassification import types


@pytest.fixture(autouse=True)
def srv_mock(graph):
    def factory(conf):
        time.sleep(random.random() * 0.1)
        return SimpleNamespace(**conf)

    factory_spy = mock.Mock(wraps=factory)

    patcher = mock.patch(
        'ilastik.applets.networkClassification.opTiktorchPipeline.TikTorchLazyflowClassifierFactory',
        factory_spy
    )
    mocked = patcher.start()
    yield mocked
    patcher.stop()


class TestOpModelPipeline:
    @pytest.fixture
    def op(self, graph):
        return OpModelPipeline(graph=graph)

    def test_server(self, op):
        op.ServerConfig.setValue({"val": 1})
        srv = op.Server.value
        assert srv.val == 1

    def test_factory(self, op, srv_mock):
        op.ServerConfig.setValue({"val": 1})

        with ThreadPoolExecutor(max_workers=4) as ex:
            list(ex.map(lambda _: op.Server.value, range(4)))

        srv_mock.assert_called_once()

    def test_setting_new_server_config_triggers_dirtyness_and_resets_cache(self, op, srv_mock):
        callback = mock.Mock()

        op.ServerConfig.setValue({"val": 1})

        assert op.Server.value.val == 1
        srv_mock.assert_called_once()

        op.Server.notifyDirty(callback)
        callback.assert_not_called()

        op.ServerConfig.setValue({"val": 2})
        callback.assert_called_once_with(op.Server, mock.ANY)

        assert op.Server.value.val == 2
        assert srv_mock.call_count == 2


class TestOpModelLoad:
    @pytest.fixture
    def srv_mock(self):
        return mock.Mock()

    @pytest.fixture
    def model(self):
        return types.Model(b"code", {"conf_value": 42})

    @pytest.fixture
    def state(self):
        return types.State(b"model_state", b"optimizer_state")

    @pytest.fixture
    def op(self, graph, srv_mock, model, state):
        op = OpModelLoad(graph=graph)
        op.Server.setValue(srv_mock)
        op.Model.setValue(model)
        op.State.setValue(state)
        return op

    def test_access_to_handle_calls_load_model(self, op, srv_mock):
        assert op.Handle.value
        srv_mock.load_model.assert_called_once()


from PyQt5.QtCore import QObject, pyqtProperty, pyqtSignal


class MyObject(QObject):
    valueChanged = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self._name = 12

    @pyqtProperty(int, notify=valueChanged)
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        if self._name != value:
            self._name = value
            self.valueChanged.emit()


def test_me():
    o = MyObject()
    def foo(*args):
        print("HELLO")
        print(args)
    o.valueChanged.connect(foo)
    o.name = 2
    assert False
