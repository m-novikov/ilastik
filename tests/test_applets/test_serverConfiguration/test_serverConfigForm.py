import pytest

from PyQt5.Qt import Qt

from ilastik.applets.serverConfiguration.serverConfigForm import ServerConfigForm


class TestServerConfigForm:
    DEVICE_LIST = [
        ('cpu', 'CPU'),
        ('gpu:0', 'GPU 0'),
        ('gpu:1', 'GPU 1'),
    ]

    @pytest.fixture
    def form(self, qtbot):
        def _devices_list(config):
            return self.DEVICE_LIST

        form = ServerConfigForm(_devices_list)
        form.show()

        qtbot.addWidget(form)
        return form

    def test_form_creation_line_edits(self, qtbot, form):
        data = {
            "name": "MyTestName",
            "address": "test.com",
            "port1": "8291",
            "port2": "8292",
        }

        fields = [
            (form.nameEdit, "name"),
            (form.addressEdit, "address"),
            (form.port1Edit, "port1"),
            (form.port2Edit, "port2"),
        ]

        form.config = data

        for field, key in fields:
            assert data[key] == field.text()

    def test_form_input(self, qtbot, form):
        data = {"name": "MyTestName"}
        form.config = data
        qtbot.keyClicks(form.nameEdit, "42")
        assert "MyTestName42" == form.config["name"]

    def test_autoguess_server(self, qtbot, form):
        assert "remote" == form.typeList.currentText()

        qtbot.keyClicks(form.addressEdit, "127.0.0.1")

        assert "local" == form.typeList.currentText()

    def test_device_list(self, qtbot, form):
        qtbot.mouseClick(form.getDevicesBtn, Qt.LeftButton)
        expected_devices = [
            (False, dev_id, dev_name)
            for dev_id, dev_name in self.DEVICE_LIST
        ]
        assert "devices" in form.config
        assert expected_devices == form.config["devices"]

        test_item = form.deviceList.item(1)
        click_pos = form.deviceList.visualItemRect(test_item).center()

        qtbot.mouseClick(form.deviceList.viewport(), Qt.LeftButton, pos=click_pos)

        assert form.config["devices"][1][0]

    def test_device_list_from_config(self, qtbot, form):
        config = {"devices": [
            (True, "cpu", "CPU"),
            (False, "gpu:0", "GPU 12"),
        ]}
        form.config = config
        assert 2 == form.deviceList.count()
        for idx in range(form.deviceList.count()):
            widget_item = form.deviceList.item(idx)
            device = config["devices"][idx]
            assert bool(widget_item.checkState()) == device[0]
            assert device[1] in widget_item.text()

    def test_device_list_merging(self, qtbot, form):
        config = {"devices": [
            (True, "gpu:1", "GPU 12"),
        ]}
        form.config = config

        qtbot.mouseClick(form.getDevicesBtn, Qt.LeftButton)
        assert 3 == form.deviceList.count()

        has_gpu1 = False
        for idx in range(form.deviceList.count()):
            widget_item = form.deviceList.item(idx)
            if widget_item.id == "gpu:1":
                assert widget_item.checkState()
                has_gpu1 = True

        assert has_gpu1
