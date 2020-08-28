import enum
import dataclasses
import logging

from typing import List

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class ModelInfo:
    name: str
    knownClasses: List[int]
    hasTraining: bool

    @property
    def numClasses(self):
        return len(self.knownClasses)


class TiktorchController:
    class State:
        Read = "READ"
        Loading = "LOADING"
        Ready = "READY"
        Empty = "EMPTY"
        Error = "ERROR"

    def __init__(self, operator, connectionFactory):
        self.connectionFactory = connectionFactory
        self.operator = operator
        self._stateListeners = []
        self._state = self.State.Empty

        self.operator.ModelInfo.notifyDirty(self._handleOperatorStateChange)
        self.operator.ModelSession.notifyDirty(self._handleOperatorStateChange)
        self.operator.ModelBinary.notifyDirty(self._handleOperatorStateChange)

    def loadModel(self, modelPath: str) -> None:
        self._state = self.State.Empty
        self._notifyStateChanged()

        with open(modelPath, "rb") as modelFile:
            modelBytes = modelFile.read()

        srvConfig = self.operator.ServerConfig.value
        connection = self.connectionFactory.ensure_connection(self.operator.ServerConfig.value)
        model = connection.create_model_session(modelBytes, [d.id for d in srvConfig.devices])
        info = ModelInfo(model.name, model.known_classes, model.has_training)

        self.operator.ModelBinary.setValue(modelBytes)
        self.operator.ModelSession.setValue(model)
        self.operator.ModelInfo.setValue(info)
        self.operator.NumClasses.setValue(info.numClasses)

        self._state = self.State.Ready

    def uploadModel(self):
        srvConfig = self.operator.ServerConfig.value
        modelBytes = self.operator.ModelBinary.value

        connection = self.connectionFactory.ensure_connection(self.operator.ServerConfig.value)
        model = connection.create_model_session(modelBytes, [d.id for d in srvConfig.devices])
        info = ModelInfo(model.name, model.known_classes, model.has_training)

        self.operator.ModelBinary.setValue(modelBytes)
        self.operator.ModelSession.setValue(model)
        self.operator.ModelInfo.setValue(info)
        self.operator.NumClasses.setValue(info.numClasses)

        self._state = self.State.Ready

    def closeModel(self):
        self.operator.ModelBinary.setValue(b"")
        self.operator.ModelInfo.setValue(None)

        model = self.operator.ModelSession.value
        self.operator.ModelSession.setValue(None)

        model.close()

    def _handleOperatorStateChange(self, *args, **kwargs):
        if self.operator.ModelInfo.ready() and self.operator.ModelBinary.ready() and not self.operator.ModelSession.ready():
            self._state = self.State.Read
        elif self.operator.ModelInfo.ready() and self.operator.ModelBinary.ready() and self.operator.ModelSession.ready():
            self._state = self.State.Ready
        elif not self.operator.ModelInfo.ready():
            self._state = self.State.Empty

        self._notifyStateChanged()

    @property
    def modelInfo(self):
        return self.operator.ModelInfo.value

    def registerListener(self, fn):
        self._stateListeners.append(fn)
        self._callListener(fn)

    def _callListener(self, fn):
        try:
            fn(self._state)
        except Exception:
            logger.exception("Failed to call listener %s", fn)

    def _notifyStateChanged(self):
        for fn in self._stateListeners:
            self._callListener(fn)
