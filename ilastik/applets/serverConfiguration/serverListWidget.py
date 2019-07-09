from PyQt5.Qt import QIcon, Qt, QModelIndex, QAbstractListModel
from PyQt5.QtWidgets import QWidget, QComboBox, QToolButton, QHBoxLayout

from ilastik.shell.gui.iconMgr import ilastikIcons


class ServerListWidget(QWidget):
    """
    Combo box widget with add/remove buttons
    """
    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self._model = None

        self._initUI()

    def _initUI(self):
        self.srvComboBox = QComboBox(self)
        self.addBtn = QToolButton(self)
        self.addBtn.setIcon(QIcon(ilastikIcons.AddSel))
        self.addBtn.clicked.connect(self._add)

        self.rmBtn = QToolButton(self)
        self.rmBtn.setIcon(QIcon(ilastikIcons.RemSel))
        self.rmBtn.clicked.connect(self._remove)

        layout = QHBoxLayout(self)
        layout.addWidget(self.srvComboBox)
        layout.addWidget(self.addBtn)
        layout.addWidget(self.rmBtn)

    def _add(self) -> None:
        if self._model:
            idx = self._model.addNewEntry()
            self.srvComboBox.setCurrentIndex(idx)

    def _remove(self) -> None:
        idx = self.currentIndex()
        self._model.removeEntry(idx)

    def setModel(self, model: "ServerListModel") -> None:
        self._model = model
        self.srvComboBox.setModel(self._model)

    @property
    def currentIndexChanged(self):
        return self.srvComboBox.currentIndexChanged

    def currentIndex(self) -> int:
        return self.srvComboBox.currentIndex()


class ServerListModel(QAbstractListModel):
    def __init__(self, parent=None, data=None):
        super().__init__(parent)
        self._data = data or []

    def rowCount(self, index: QModelIndex = QModelIndex()):
        return len(self._data)

    def index(self, row: int, column: int = 0, parent: QModelIndex = QModelIndex()):
        return self.createIndex(row, column)

    def addNewEntry(self):
        self.beginInsertRows(QModelIndex(), len(self._data), len(self._data) + 1)
        self._data.append({"name": "Unknown"})
        self.endInsertRows()
        return len(self._data) - 1

    def removeEntry(self, row: int):
        if self.hasIndex(row, 0):
            self.beginRemoveRows(QModelIndex(), row, row)
            del self._data[row]
            self.endRemoveRows()

    def flags(self, index):
        flags = super().flags(index)

        if index.isValid():
            flags |= Qt.ItemIsEditable
        else:
            flags = Qt.ItemIsDropEnabled

        return flags

    def setData(self, index, value, role=Qt.EditRole):
        if not index.isValid() or role != Qt.EditRole:
            return False

        row = index.row()
        self._data[row] = value
        self.dataChanged.emit(index, index)
        return True

    def data(self, index: QModelIndex, role: int):
        row = index.row()

        if role == Qt.DisplayRole:
            return self._data[row]["name"]
        elif role == Qt.EditRole:
            return self._data[row]

    def submit(self):
        print("submit")
        return super().submit()
