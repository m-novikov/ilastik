import pytest
from PyQt5 import QtGui, QtCore, QtWidgets

from ilastik.applets.serverConfiguration.serverConfigGui import ServerConfigGui, QWidget
from ilastik.applets.serverConfiguration.opServerConfig import DEFAULT_REMOTE_SERVER_CONFIG



@pytest.fixture
def srvgui():
    return QWidget()



class Prop:
    class Box:
        def __init__(self, value):
            self.value = value

    def __init__(self):
        self._name = None

    def __get__(self, instance, type=None):
        assert self._name
        if instance:
            val = instance.__dict__[self._name]
            return self.Box(val)

        return self
    
    def __set__(self, instance, value):
        instance.__dict__[self._name] = value

    def __set_name__(self, owner, name):
        self._name = name


class SrvConfigOp:
    LocalServerConfig = Prop()
    RemoteServerConfig = Prop()
    UseLocalServer = Prop()

    def toggleServerConfig(self, use_local):
        pass

    def setLocalServerConfig(self, value):
        self.LocalServerConfig = value

    def setRemoteServerConfig(self, value):
        self.RemoteServerConfig = value


@pytest.fixture()
def server_config_op():
    op = SrvConfigOp()
    op.LocalServerConfig = {}
    op.RemoteServerConfig = DEFAULT_REMOTE_SERVER_CONFIG
    op.UseLocalServer = True
    return op


@pytest.fixture()
def srvgui(qtbot, server_config_op):
    w = ServerConfigGui(None, server_config_op)
    qtbot.addWidget(w)
    return w

def test_server_gui(qtbot, srvgui):
    srvgui.show()
    qtbot.waitForWindowShown(srvgui)
    qtbot.stopForInteraction()


class CheckableTabWidget(QtWidgets.QTabWidget):

    checkBoxList = []

    def addTab(self, widget, title):
        super().addTab(widget, title)
        checkBox = QtWidgets.QCheckBox()
        self.checkBoxList.append(checkBox)
        self.tabBar().setTabButton(self.tabBar().count()-1, QtWidgets.QTabBar.LeftSide, checkBox)
        checkBox.stateChanged.connect(lambda checkState: self.__emitStateChanged(checkBox, checkState))

    def isChecked(self, index):
        return self.tabBar().tabButton(index, QtWidgets.QTabBar.LeftSide).checkState() != QtCore.Qt.Unchecked

    def setCheckState(self, index, checkState):
        self.tabBar().tabButton(index, QtWidgets.QTabBar.LeftSide).setCheckState(checkState)

    def __emitStateChanged(self, checkBox, checkState):
        index = self.checkBoxList.index(checkBox)
        #self.emit(QtCore.SIGNAL('stateChanged(int, int)'), index, checkState)


def test_w(qtbot):
    w = CheckableTabWidget()
    qtbot.add_widget(w)
    w.addTab(QWidget(), "TITLE1")
    w.addTab(QWidget(), "TITLE2")
    w.show()
    qtbot.waitForWindowShown(w)
    qtbot.stopForInteraction()
