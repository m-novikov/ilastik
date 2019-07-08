import pytest

from ilastik.applets.networkClassification import nnClassGui as nngui

from PyQt5.Qt import QIcon, QStringListModel, QAbstractItemModel, QAbstractItemDelegate, Qt, QModelIndex, QDataWidgetMapper, pyqtProperty, QItemDelegate
from PyQt5.QtWidgets import QWidget, QComboBox, QToolButton, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit
from ilastik.shell.gui.iconMgr import ilastikIcons

#When subclassing QAbstractItemModel, at the very least you must implement index(), parent(), rowCount(), columnCount(), and data(). These functions are used in all read-only models, and form the basis of editable models.
class ServerListModel(QAbstractItemModel):
    def __init__(self, parent=None, data=None):
        super().__init__(parent)
        self._data = data or []

    def rowCount(self, index: QModelIndex):
        return len(self._data)

    def columnCount(self, index: QModelIndex):
        return 2

    def index(self, row, column, parent):
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
        col = index.column()
        if col == 1:
            self._data[row] = value
            self.dataChanged.emit(index, index)
            return True
        return False


    def data(self, index: QModelIndex, role: int):
        row = index.row()
        col = index.column()
        if col == 1:
            return self._data[row]
        print("QUERY DATA", self._data[row])
        return self._data[row]['name']
        if role == Qt.DisplayRole:
            row = index.row()
            return self._data[row]['name']
        elif role == Qt.EditRole:
            row = index.row()
            return self._data[row]['name']

class ServerListWidget(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._srv_combo_box = QComboBox()
        self._add_btn = QToolButton()
        self._add_btn.setIcon(QIcon(ilastikIcons.AddSel))
        self._rm_btn = QToolButton()
        layout = QHBoxLayout(self)
        layout.addWidget(self._srv_combo_box)
        layout.addWidget(self._add_btn)
        layout.addWidget(self._rm_btn)
        self._add_btn.clicked.connect(self._add)
        self._rm_btn.clicked.connect(self._remove)
        self._model = None
        #self.srv_combo_box.currentIndexChanged.connect(lambda *a: print("Changed", a))

    def setModel(self, model) -> None:
        self._model = model
        self._srv_combo_box.setModel(self._model)

    def _add(self):
        if self._model:
            idx = self._model.addNewEntry()
            self._srv_combo_box.setCurrentIndex(idx)

    def _remove(self):
        idx = self.currentIndex()
        self._model.removeEntry(idx)

    @property
    def currentIndexChanged(self):
        return self._srv_combo_box.currentIndexChanged

    def currentIndex(self):
        return self._srv_combo_box.currentIndex()


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
