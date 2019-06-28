import threading

import numpy

from lazyflow import stype, rtype
from lazyflow.classifiers import TikTorchLazyflowClassifierFactory
from lazyflow.graph import Operator, InputSlot, OutputSlot


def _set_meta_for_opaque(*slots):
    # TODO: Opaque slots shouldn't require setupOutputs. Fix it in lazyflow.slot
    for slot in slots:
        slot.meta.shape = (1,)
        slot.meta.dtype = object


class OpModelPipeline(Operator):
    ServerConfig = InputSlot(stype=stype.Opaque)
    # Model: code of the model and hyperparameters config
    Model = InputSlot(stype=stype.Opaque)
    # ModelState includes serialized tensors and optimizer state
    ModelState = InputSlot(stype=stype.Opaque)

    # Server controls
    Server = OutputSlot(stype=stype.Opaque)
    # Model controls implies it's uploaded to the server and running
    ModelHandle = OutputSlot(stype=stype.Opaque)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._srv_factory = OpServerFactory(parent=self)
        self._srv_factory.ServerConfig.connect(self.ServerConfig)
        self.Server.connect(self._srv_factory.Server)

        self._model = OpModelLoad(parent=self)
        self._model.Server.connect(self._srv_factory.Server)
        self._model.Model.connect(self.Model)
        self._model.State.connect(self.ModelState)
        self.ModelHandle.connect(self._model.Handle)

    def setupOutputs(self):
        _set_meta_for_opaque(self.Model, self.State, self.ServerConfig)

    def propagateDirty(self, slot, subindex, roi):
        if slot == self.ServerConfig:
            self.Server.setDirty()

        self.ModelHandle.setDirty()


class OpServerFactory(Operator):
    ServerConfig = InputSlot(stype=stype.Opaque)

    Server = OutputSlot(stype=stype.Opaque)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cache = None
        self._cache_lock = threading.Lock()
        self._srv_factory = TikTorchLazyflowClassifierFactory

    def _createServer(self):
        return self._srv_factory(self.ServerConfig.value)

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
    Server = InputSlot(stype=stype.Opaque)
    Model = InputSlot(stype=stype.Opaque)
    State = InputSlot(stype=stype.Opaque)

    # Model handle allowin create checkpoint and query for block size
    Handle = OutputSlot(stype=stype.Opaque)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cache = None
        self._cache_lock = threading.Condition()

    def setupOutputs(self):
        _set_meta_for_opaque(self.Handle)

    def propagateDirty(self, slot, subindex, roi):
        self._cache = None
        self.Handle.setDirty()

    def _load_model(self):
        model = self.Model.value
        state = self.State.value
        srv = self.Server.value

        conf = clean(model.config)

        return srv.load_model(conf, model.code, state.model, state.optimizer)

    def execute(self, slot, subindex, roi, result):
        if self._cache:
            return self._cache

        with self._cache_lock:
            if self._cache is None:
                self._cache = self._load_model()

        return self._cache
