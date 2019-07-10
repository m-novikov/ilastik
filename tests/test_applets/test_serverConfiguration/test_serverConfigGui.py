import pytest

from ilastik.applets.networkClassification import nnClassGui as nngui
from ilastik.applets.serverConfiguration.serverConfigGui import ServerConfigurationEditor
from ilastik.applets.serverConfiguration.serverListWidget import ServerListModel

from PyQt5 import uic
from PyQt5.Qt import QIcon, QStringListModel, QAbstractItemModel, QAbstractItemDelegate, Qt, QModelIndex, QDataWidgetMapper, pyqtProperty, QItemDelegate, QAbstractListModel, QListWidgetItem, pyqtSignal
from PyQt5.QtWidgets import QWidget, QComboBox, QToolButton, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit, QListWidget
from ilastik.shell.gui.iconMgr import ilastikIcons
from ilastik.applets.serverConfiguration.configStorage import ServerConfigStorage
from ilastik.applets.serverConfiguration import types


from configparser import ConfigParser

CONFIG = """
[ilastik]
debug: false
plugin_directories: ~/.ilastik/plugins,

[lazyflow]
threads: -1
total_ram_mb: 0

[tiktorch-server::myid1]
name = MyServer1
type = local
address = 127.0.0.1
port1 = 5543
port2 = 5542
devices =
   cpu0::CPU0
   gpu1::GPU6::enabled

[tiktorch-server::myid1::cpu0]
name = MyServer1
type = local
address = 127.0.0.1

[tiktorch-server::myid2]
name = MyServer2
type = remote
[tiktorch-server::myid3]
"""
# TODO: Config with no servers

@pytest.fixture
def widget(qtbot):
    conf = ConfigParser()
    conf.read_string(CONFIG)
    srv_storage = ServerConfigStorage(conf, dst="/home/novikov/myconfig")

    w = ServerConfigurationEditor()
    w.setModel(ServerListModel(conf_store=srv_storage))

    qtbot.addWidget(w)
    w.show()

    qtbot.waitForWindowShown(w)

    return w

# TODO: Add datawidget mapper to map config values to form
# TODO: Add user=True property to form widget which will accept json config as an argument

def test_change_index_changes_visibility(qtbot, widget):
    qtbot.stopForInteraction()


from io import StringIO



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

class TestServerParse:
    MALFORMED_MULTI_SERVER = """
[tiktorch-server::myid1]
    name = MyServer1
    type = local
    address = 127.0.0.1
    port1 = 5543
    port2 = 5542
    devices =
        cpu0::CPU0
        gpu1::MyCoolGPU::enabled

[tiktorch-server::myid2]
    name = MyServer2
    type = local

[tiktorch-server::myid3]
    name = MyServer3
    type = remote
    address = 8.8.8.8
    port1 = 5543
    port2 = 5542
    ssh_key = /home/user/.ssh/id_rsa
    username = testuser
    devices =
        cpu0::CPU0
        gpu1::MyCoolGPU::enabled
"""

    NO_SERVER = ""

    SINGLE_SERVER = """
[tiktorch-server::myid1]
    name = MyServer1
    type = local
    address = 127.0.0.1
    port1 = 5543
    port2 = 5542
    devices =
        cpu0::CPU0
        gpu1::MyCoolGPU::enabled
"""

    @pytest.fixture
    def parse(self):
        def _parse(conf_str):
            conf = ConfigParser()
            conf.read_string(conf_str)
            srv_storage = ServerConfigStorage(conf, dst='')
            return srv_storage.get_servers()

        return _parse

    def test_parsing_server(self, parse):
        servers = parse(self.SINGLE_SERVER)

        assert 1 == len(servers)
        srv = servers[0]

        assert isinstance(srv, types.ServerConfig)
        assert "MyServer1" == srv.name
        assert "local" == srv.type
        assert "127.0.0.1" == srv.address
        assert "5543" == srv.port1
        assert "5542" == srv.port2

    def test_parsing_multiserver(self, parse):
        servers = parse(self.MALFORMED_MULTI_SERVER)

        assert 2 == len(servers)
        fst, snd = servers

        assert isinstance(fst, types.ServerConfig)
        assert "MyServer1" == fst.name
        assert "local" == fst.type
        assert "127.0.0.1" == fst.address
        assert "5543" == fst.port1
        assert "5542" == fst.port2

        assert isinstance(snd, types.ServerConfig)
        assert "MyServer3" == snd.name
        assert "remote" == snd.type
        assert "8.8.8.8" == snd.address
        assert "5543" == snd.port1
        assert "5542" == snd.port2
        assert "testuser" == snd.username
        assert "/home/user/.ssh/id_rsa" == snd.ssh_key

    def test_parsing_noserver(self, parse):
        servers = parse(self.NO_SERVER)
        assert not servers


class TestServerParseDevices:
    NORMAL_DEVS = """
[tiktorch-server::myid1]
    name = MyServer1
    type = local
    address = 127.0.0.1
    port1 = 5543
    port2 = 5542
    devices =
        cpu0::CPU0
        gpu1::MyCoolGPU::enabled
"""

    MALFORMED_DEVS = """
[tiktorch-server::gpu]
    name = MalformedGPU
    type = local
    address = 127.0.0.1
    port1 = 5543
    port2 = 5542
    devices =
        ::cpu0::CPU0:::::::
        gpu1::MyCoolGPU::1


        gpu2::NormalGPU::enabled
"""

    EMPTY_DEVS = """
[tiktorch-server::gpu2]
    name = MalformedGPU2
    type = local
    address = 127.0.0.1
    port1 = 5543
    port2 = 5542
    devices =
"""

    NO_DEVS = """
[tiktorch-server::gpu2]
    name = MalformedGPU2
    type = local
    address = 127.0.0.1
    port1 = 5543
    port2 = 5542
"""

    @pytest.fixture
    def parse(self):
        def _parse(conf_str):
            conf = ConfigParser()
            conf.read_string(conf_str)
            srv_storage = ServerConfigStorage(conf, dst='')
            servers = srv_storage.get_servers()
            assert len(servers) == 1
            return servers[0].devices

        return _parse

    def test_parsing_devices(self, parse):
        devices = parse(self.NORMAL_DEVS)
        assert 2 == len(devices)
        fst, snd = devices

        assert "cpu0" == fst.id
        assert "CPU0" == fst.name
        assert not fst.enabled

        assert "gpu1" == snd.id
        assert "MyCoolGPU" == snd.name
        assert snd.enabled

    def test_parsing_malformed_devices(self, parse):
        devices = parse(self.MALFORMED_DEVS)
        assert 2 == len(devices)
        fst, snd = devices

        assert "gpu1" == fst.id
        assert "MyCoolGPU" == fst.name
        assert not fst.enabled

        assert "gpu2" == snd.id
        assert "NormalGPU" == snd.name
        assert snd.enabled

    def test_parsing_devices_empty_entry(self, parse):
        devices = parse(self.EMPTY_DEVS)
        assert not devices

    def test_parsing_devices_no_entry(self, parse):
        devices = parse(self.NO_DEVS)
        assert not devices


class TestStoringServers:
    @pytest.fixture
    def store(self):
        def _store(dst, servers):
            conf = ConfigParser()
            conf.read_string(dst.read())
            srv_storage = ServerConfigStorage(conf, dst=dst)
            srv_storage.store(servers)

        return _store

    @pytest.fixture
    def servers(self):
        return [
            types.ServerConfig(id='myid1', name='Server1', type='local', address='127.0.0.1', port1='3123', port2='3213', devices=[types.Device(id='cpu0', name='MyCpu1', enabled=True), types.Device(id='gpu1', name='GPU1', enabled=False)])
        ]

    def test_me(self, store, servers):
        from io import StringIO
        out = StringIO()
        store(out, servers)
        print(out.getvalue())
