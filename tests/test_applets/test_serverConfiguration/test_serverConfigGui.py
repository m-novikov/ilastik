import pytest

from ilastik.applets.networkClassification import nnClassGui as nngui

from PyQt5 import uic
from PyQt5.Qt import QIcon, QStringListModel, QAbstractItemModel, QAbstractItemDelegate, Qt, QModelIndex, QDataWidgetMapper, pyqtProperty, QItemDelegate, QAbstractListModel, QListWidgetItem
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
        print("SET MODEl DATA", index.isValid(), self._data)
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

from contextlib import contextmanager

class ServerEditForm(QWidget):
    nameEdit: QLineEdit
    addressEdit: QLineEdit
    typeList: QComboBox
    usernameEdit: QLineEdit
    usernameLabel: QLabel
    port1Edit: QLineEdit
    port2Edit: QLineEdit
    sshKeyEdit: QLineEdit
    sshKeyLabel: QLabel

    # TODO MAKE RELATIVE
    UI_PATH = "/home/novikov/projects/ilastik-project/ilastik/ilastik/applets/serverConfiguration/serverConfig.ui"

    def __init__(self, device_getter) -> None:
        super().__init__(None)
        self._initUI()

        self._config = {}
        self._device_getter = device_getter
        self._updating = False

    @property
    def ui_path(self):
        #local_dir = os.path.split(__file__)[0] + "/"
        return self.UI_PATH

    def _initUI(self):
        """
        Load the ui file for the central widget.
        """
        uic.loadUi(self.ui_path, self)
        self.typeList.setModel(QStringListModel(["remote", "local"]))

        # Trigger state updates
        self.nameEdit.textChanged.connect(self._updateConfigFromFields)
        self.addressEdit.textChanged.connect(self._updateConfigFromFields)
        self.typeList.currentTextChanged.connect(self._updateConfigFromFields)
        self.port1Edit.textChanged.connect(self._updateConfigFromFields)
        self.port2Edit.textChanged.connect(self._updateConfigFromFields)
        self.usernameEdit.textChanged.connect(self._updateConfigFromFields)
        self.sshKeyEdit.textChanged.connect(self._updateConfigFromFields)

        # UI updates
        self.addressEdit.textChanged.connect(self._setServerTypeFromAddress)
        self.typeList.currentTextChanged.connect(self._changeRemoteFieldsVisibility)
        self.getDevicesBtn.clicked.connect(self._setDevices)

    def _setRemoteFieldsVisibility(self, value: bool) -> None:
        self.sshKeyEdit.setVisible(value)
        self.sshKeyLabel.setVisible(value)
        self.usernameEdit.setVisible(value)
        self.usernameLabel.setVisible(value)

    def _setServerTypeFromAddress(self, address: str):
        if address in ("localhost", "127.0.0.1"):
            self.typeList.setCurrentText("local")
        else:
            self.typeList.setCurrentText("remote")

    def _changeRemoteFieldsVisibility(self):
        if self.typeList.currentText() == "local":
            self._setRemoteFieldsVisibility(False)
        else:
            self._setRemoteFieldsVisibility(True)

    def _setDevices(self):
        devices = self._device_getter(self._config)
        self.deviceList.clear()
        for d in devices:
            item = QListWidgetItem(f"{d[0]} ({d[1]})", self.deviceList)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)

    @pyqtProperty(dict, user=True)
    def config(self):
        return self._config

    @config.setter
    def config(self, value):
        self._config = value
        self._updateFieldsFromConfig()

    @contextmanager
    def _batch_update_fields(self):
        self._updating = True
        yield
        self._updating = False

    def _updateConfigFromFields(self):
        if self._updating:
            return

        self._config["name"] = self.nameEdit.text()
        self._config["address"] = self.addressEdit.text()
        self._config["type"] = self.typeList.currentText()
        self._config["port1"] = self.port1Edit.text()
        self._config["port2"] = self.port2Edit.text()
        self._config["username"] = self.usernameEdit.text()
        self._config["ssh_key"] = self.sshKeyEdit.text()

    def _updateFieldsFromConfig(self):
        with self._batch_update_fields():
            self.nameEdit.setText(self._config.get("name", ""))
            self.addressEdit.setText(self._config.get("address", ""))
            self.typeList.setCurrentText(self._config.get("type", ""))
            self.port1Edit.setText(self._config.get("port1", ""))
            self.port2Edit.setText(self._config.get("port2", ""))
            self.usernameEdit.setText(self._config.get("username", ""))
            self.sshKeyEdit.setText(self._config.get("ssh_key", ""))


class ServerFormItemDelegate(QItemDelegate):
    def setEditorData(self, editor: QWidget, index: QModelIndex) -> None:
        dst_prop = editor.metaObject().userProperty()
        if dst_prop.isValid():
            name = dst_prop.name()
            setattr(editor, name, index.data(role=Qt.EditRole))

        super().setEditorData(editor, index)

def _devices_list(config):
    return [('a', 'test a'), ('b', 'test b')]

class ServerListEditWidget(QWidget):

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._srv_list = ServerListWidget()
        self._srv_form = ServerEditForm(_devices_list)
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
    w.setModel(ServerListModel(data=[{'name': 'Name 1', 'address': "127.0.0.1"}]))

    qtbot.addWidget(w)
    w.show()

    qtbot.waitForWindowShown(w)

    return w

# TODO: Add datawidget mapper to map config values to form
# TODO: Add user=True property to form widget which will accept json config as an argument

def test_change_index_changes_visibility(qtbot, widget):
    qtbot.stopForInteraction()
