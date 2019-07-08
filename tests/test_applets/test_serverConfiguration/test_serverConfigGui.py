import pytest

from ilastik.applets.networkClassification import nnClassGui as nngui

from PyQt5.Qt import QIcon, QStringListModel, QAbstractItemModel, QAbstractItemDelegate, Qt, QModelIndex, QDataWidgetMapper, pyqtProperty, QItemDelegate, QAbstractListModel
from PyQt5.QtWidgets import QWidget, QComboBox, QToolButton, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit
from ilastik.shell.gui.iconMgr import ilastikIcons

class ServerListModel(QAbstractListModel):
    def __init__(self, parent=None, data=None):
        super().__init__(parent)
        self._data = data or []

    def rowCount(self, index: QModelIndex):
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

    def parent(self, index: QModelIndex) -> QModelIndex:
        return QModelIndex()

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

class ServerListWidget(QWidget):
    """
    Combo box widget with add/remove buttons
    """
    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self._model = None

        self._initUI()

    def _initUI(self):
        self._srvComboBox = QComboBox(self)
        self._addBtn = QToolButton(self)
        self._addBtn.setIcon(QIcon(ilastikIcons.AddSel))
        self._addBtn.clicked.connect(self._add)

        self._rmBtn = QToolButton(self)
        self._rmBtn.setIcon(QIcon(ilastikIcons.RemSel))
        self._rmBtn.clicked.connect(self._remove)

        layout = QHBoxLayout(self)
        layout.addWidget(self._srvComboBox)
        layout.addWidget(self._addBtn)
        layout.addWidget(self._rmBtn)

    def _add(self) -> None:
        if self._model:
            idx = self._model.addNewEntry()
            self._srvComboBox.setCurrentIndex(idx)

    def _remove(self) -> None:
        idx = self.currentIndex()
        self._model.removeEntry(idx)

    def setModel(self, model: ServerListModel) -> None:
        self._model = model
        self._srvComboBox.setModel(self._model)

    @property
    def currentIndexChanged(self):
        return self._srvComboBox.currentIndexChanged

    def currentIndex(self) -> int:
        return self._srvComboBox.currentIndex()


class ServerEditForm(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._nameEdit = QLineEdit()
        self._nameLabel = QLabel()
        self._nameLabel.setText('Name:')
        self._nameEdit.textChanged.connect(self._updateName)

        self._config = {}
        layout = QHBoxLayout(self)
        layout.addWidget(self._nameLabel)
        layout.addWidget(self._nameEdit)

    @pyqtProperty(dict, user=True)
    def config(self):
        return self._config

    def _updateName(self, value):
        print("UDPATE NAME", value)
        self._config["name"] = value

    @config.setter
    def config(self, value):
        self._config = value
        self._nameEdit.setText(value["name"])


class ServerFormItemDelegate(QItemDelegate):
    def setEditorData(self, editor: QWidget, index: QModelIndex) -> None:
        dst_prop = editor.metaObject().userProperty()
        if dst_prop.isValid():
            name = dst_prop.name()
            setattr(editor, name, index.data(role=Qt.EditRole))
            #return
        super().setEditorData(editor, index)

    def setModelData(self, editor: QWidget, model: QAbstractItemModel, index: QModelIndex) -> None:
        print("SEt MODEL DATA IS CALLED", editor, model, index)
        super().setModelData(editor, model, index)


class ServerListEditWidget(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._srv_list = ServerListWidget()
        self._srv_form = ServerEditForm()
        layout = QVBoxLayout(self)
        layout.addWidget(self._srv_list)
        layout.addWidget(self._srv_form)
        #self._nameEdit = QLineEdit()
        #layout.addWidget(self._nameEdit)

    def setModel(self, model):
        self._srv_list.setModel(model)
        #sel_model = self._srv_list.selectionModel()
        print(self._srv_form.metaObject().userProperty().isValid())

        #self._m = QStringListModel(['test', 'test2', 'test3'])
        self._mapper = QDataWidgetMapper(self)
        self._mapper.setModel(model)
        self._mapper.setItemDelegate(ServerFormItemDelegate(self))
        self._mapper.addMapping(self._srv_form, 1)
        self._mapper.setCurrentIndex(self._srv_list.currentIndex())
        self._srv_list.currentIndexChanged.connect(self._mapper.setCurrentIndex)


@pytest.fixture
def widget(qtbot):
    w = ServerListEditWidget()
    w.setModel(ServerListModel(data=[{'name': 'Name 1'}, {'name': 'Name 2'}]))

    qtbot.addWidget(w)
    w.show()

    qtbot.waitForWindowShown(w)

    return w

# TODO: Add datawidget mapper to map config values to form
# TODO: Add user=True property to form widget which will accept json config as an argument

def test_change_index_changes_visibility(qtbot, widget):
    qtbot.stopForInteraction()
