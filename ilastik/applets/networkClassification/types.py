from dataclasses import dataclass


@dataclass
class State:
    """
    Stores model state
    As opaque serialized tensors
    """
    model: bytes
    optimizer: bytes


@dataclass
class Model:
    code: bytes
    config: dict

    def __bool__(self):
        return bool(self.code)


Model.Empty = Model(b"", {})
