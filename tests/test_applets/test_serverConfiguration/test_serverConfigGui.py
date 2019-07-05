import pytest

from ilastik.applets.networkClassification import nnClassGui as nngui

from PyQt5.Qt import QIcon, QStringListModel, QAbstractItemModel, Qt, QModelIndex
from PyQt5.QtWidgets import QWidget, QComboBox, QToolButton, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit
from ilastik.shell.gui.iconMgr import ilastikIcons

#When subclassing QAbstractItemModel, at the very least you must implement index(), parent(), rowCount(), columnCount(), and data(). These functions are used in all read-only models, and form the basis of editable models.
class ServerListModel(QAbstractItemModel):
    def __init__(self, parent=None, data=None):
        super().__init__(parent)
        self._data = data

    def rowCount(self, index: QModelIndex):
        return len(self._data)

    def columnCount(self, index: QModelIndex):
        return 1

    def index(self, row, column, parent):
        return self.createIndex(row, column)

    def parent(self, index: QModelIndex) -> QModelIndex:
        return QModelIndex()

    def data(self, index: QModelIndex, role: int):
        if role == Qt.DisplayRole:
            row = index.row()
            return self._data[row]['name']


class ServerListWidget(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.srv_combo_box = QComboBox()
        self.add_btn = QToolButton()
        self.add_btn.setIcon(QIcon(ilastikIcons.AddSel))
        layout = QHBoxLayout(self)
        layout.addWidget(self.srv_combo_box)
        layout.addWidget(self.add_btn)

    def setModel(self, model) -> None:
        self.srv_combo_box.setModel(model)

class ServerEditForm(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._nameEdit = QLineEdit()
        self._nameLabel = QLabel()
        self._nameLabel.setText('Name:')
        layout = QHBoxLayout(self)
        layout.addWidget(self._nameLabel)
        layout.addWidget(self._nameEdit)

class ServerListEditWidget(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._srv_list = ServerListWidget()
        self._srv_form = ServerEditForm()
        layout = QVBoxLayout(self)
        layout.addWidget(self._srv_list)
        layout.addWidget(self._srv_form)

    def setModel(self, model):
        self._srv_list.setModel(model)


@pytest.fixture
def widget(qtbot):
    w = ServerListEditWidget()
    w.setModel(ServerListModel(data=[{'name': 'Name 1'}, {'name': 'Name 2'}]))

    qtbot.addWidget(w)
    w.show()

    qtbot.waitForWindowShown(w)

    return w


def test_change_index_changes_visibility(qtbot, widget):
    qtbot.stopForInteraction()
