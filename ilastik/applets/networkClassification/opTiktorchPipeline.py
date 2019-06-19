import threading

import numpy

from lazyflow import stype, rtype
from lazyflow.classifiers import TikTorchLazyflowClassifierFactory
from lazyflow.graph import Operator, InputSlot, OutputSlot


class OpModelPipeline(Operator):
    ServerConfig = InputSlot(stype=stype.Opaque, rtype=rtype.Everything)

    ModelConfig = InputSlot(stype=stype.Opaque, rtype=rtype.Everything)
    BinaryModel = InputSlot(stype=stype.Opaque, rtype=rtype.Everything)
    BinaryModelState = InputSlot(stype=stype.Opaque, rtype=rtype.Everything)
    BinaryOptimizerState = InputSlot(stype=stype.Opaque, rtype=rtype.Everything)

    Server = OutputSlot(stype=stype.Opaque, rtype=rtype.Everything)
    Model = OutputSlot(stype=stype.Opaque, rtype=rtype.Everything)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._srv_factory = OpServerFactory(parent=self)
        self._srv_factory.ServerConfig.connect(self.ServerConfig)
        self.Server.connect(self._srv_factory.Server)

        self._model = OpModelLoad(parent=self)
        self._model.Server.connect(self._srv_factory.Server)
        self._model.Config.connect(self.ModelConfig)
        self._model.BinaryModel.connect(self.BinaryModel)
        self._model.BinaryModelState.connect(self.BinaryModelState)
        self._model.BinaryOptimizerState.connect(self.BinaryOptimizerState)
        self.Model.connect(self._model.Model)

    def propagateDirty(self, slot, subindex, roi):
        self.Model.setDirty()


class OpServerFactory(Operator):
    ServerConfig = InputSlot(stype=stype.Opaque, rtype=rtype.Everything)
    ServerFactory = InputSlot(
        stype=stype.Opaque,
        rtype=rtype.Everything,
        value=TikTorchLazyflowClassifierFactory,
    )

    Server = OutputSlot(stype=stype.Opaque, rtype=rtype.Everything)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cache = None
        self._cache_lock = threading.Lock()

    def _createServer(self):
        factory = self.ServerFactory.value
        return factory(self.ServerConfig.value)

    def execute(self, slot, subindex, roi, result):
        if self._cache:
            return self._cache

        with self._cache_lock:
            if self._cache is None:
                self._cache = self._createServer()

        return self._cache

    def setupOutputs(self):
        self.Server.meta.shape = (1,)
        self.Server.meta.dtype = object

    def propagateDirty(self, slot, subindex, roi):
        self._cache = None
        self.Server.setDirty()


def clean(data):
    cleaned = data

    if isinstance(data, dict):
        cleaned = {}
        for key, value in data.items():
            cleaned[key] = clean(value)

    elif isinstance(data, numpy.integer):
        cleaned = int(data)

    elif isinstance(data, numpy.ndarray):
        cleaned = tuple(clean(v) for v in data)

    return cleaned


class OpModelLoad(Operator):
    Server = InputSlot(stype=stype.Opaque, rtype=rtype.Everything)
    Config = InputSlot(stype=stype.Opaque, rtype=rtype.Everything)
    BinaryModel = InputSlot(stype=stype.Opaque, rtype=rtype.Everything)
    BinaryModelState = InputSlot(stype=stype.Opaque, rtype=rtype.Everything)
    BinaryOptimizerState = InputSlot(stype=stype.Opaque, rtype=rtype.Everything)

    Model = OutputSlot(stype=stype.Opaque, rtype=rtype.Everything)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cache = None
        self._cache_lock = threading.Condition()

    def setupOutputs(self):
        self.Model.meta.shape = (1,)
        self.Model.meta.dtype = object

    def propagateDirty(self, slot, subindex, roi):
        self._cache = None
        self.Model.setDirty()

    def _load_model(self):
        conf = clean(self.Config.value)

        model_binary = bytes(self.BinaryModel.value)
        model_state = bytes(self.BinaryModelState.value)
        opt_state = bytes(self.BinaryOptimizerState.value)

        srv = self.Server.value
        return srv.load_model(conf, model_binary, model_state, opt_state)

    def execute(self, slot, subindex, roi, result):
        if self._cache:
            return self._cache

        with self._cache_lock:
            if self._cache is None:
                self._cache = self._load_model()

        return self._cache
