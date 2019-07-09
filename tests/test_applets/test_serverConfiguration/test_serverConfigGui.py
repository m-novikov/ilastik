import pytest

from ilastik.applets.networkClassification import nnClassGui as nngui
from ilastik.applets.serverConfiguration.serverConfigGui import ServerConfigurationEditor
from ilastik.applets.serverConfiguration.serverListWidget import ServerListModel

from PyQt5 import uic
from PyQt5.Qt import QIcon, QStringListModel, QAbstractItemModel, QAbstractItemDelegate, Qt, QModelIndex, QDataWidgetMapper, pyqtProperty, QItemDelegate, QAbstractListModel, QListWidgetItem, pyqtSignal
from PyQt5.QtWidgets import QWidget, QComboBox, QToolButton, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit, QListWidget
from ilastik.shell.gui.iconMgr import ilastikIcons




@pytest.fixture
def widget(qtbot):
    w = ServerConfigurationEditor()
    w.setModel(ServerListModel(data=[{'name': 'Name 1', 'address': "127.0.0.1"}]))

    qtbot.addWidget(w)
    w.show()

    qtbot.waitForWindowShown(w)

    return w

# TODO: Add datawidget mapper to map config values to form
# TODO: Add user=True property to form widget which will accept json config as an argument

# def test_change_index_changes_visibility(qtbot, widget):
#     qtbot.stopForInteraction()

from configparser import ConfigParser

from io import StringIO


CONFIG = """
[ilastik]
debug: false
plugin_directories: ~/.ilastik/plugins,

[lazyflow]
threads: -1
total_ram_mb: 0

[tiktorch-server:myid1]
name = MyServer1

[tiktorch-server:myid2]
name = MyServer2
[tiktorch-server:myid3]
"""

def test_server_config_storage():
    conf = ConfigParser()
    conf.read_string(CONFIG)

    srv_storage = ServerConfigStorage(conf)
    assert len(srv_storage.get_servers()) == 3


def test_server_config_storing_server():
    conf = ConfigParser()
    conf.read_string(CONFIG)
    srv_storage = ServerConfigStorage(conf)
    out = StringIO()
    srv_storage.store([{"id": "MySrv1", "type": "local"}], out)

    result = out.getvalue()

    assert "MySrv1" in result
    assert "MyServer1" not in result, "absent sections should be removed"
    assert "ilastik" in result, "non related sections of config should stay"
