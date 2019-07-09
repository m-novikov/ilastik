import os

from contextlib import contextmanager

from PyQt5 import uic
from PyQt5.Qt import Qt, QStringListModel, pyqtProperty, QListWidgetItem, pyqtSignal, QEvent
from PyQt5.QtCore import QStateMachine, QState, QSignalTransition, pyqtSignal
from PyQt5.QtWidgets import QWidget, QComboBox, QLabel, QLineEdit, QListWidget


class ServerConfigForm(QWidget):
    nameEdit: QLineEdit
    addressEdit: QLineEdit
    typeList: QComboBox
    port1Edit: QLineEdit
    port2Edit: QLineEdit
    deviceList: QListWidget

    # Remote server fields
    usernameEdit: QLineEdit
    usernameLabel: QLabel
    sshKeyEdit: QLineEdit
    sshKeyLabel: QLabel

    gotDevices = pyqtSignal()

    # TODO MAKE RELATIVE
    UI_FILE = "serverConfigForm.ui"

    @pyqtProperty(dict, user=True)
    def config(self):
        return self._config

    @config.setter
    def config(self, value):
        print("SETTING CONFIG TO", value)
        self._config = value
        self._updateFieldsFromConfig()

    def __init__(self, device_getter) -> None:
        super().__init__(None)
        self._initUI()

        self._config = {}
        self._device_getter = device_getter
        self._updating = False

    @property
    def _ui_path(self):
        local_dir = os.path.dirname(__file__)
        return os.path.join(local_dir, self.UI_FILE)

    def _initUI(self):
        """
        Load the ui file for the central widget.
        """
        uic.loadUi(self._ui_path, self)
        self.typeList.setModel(QStringListModel(["remote", "local"]))

        # Trigger state updates
        self.nameEdit.textChanged.connect(self._updateConfigFromFields)
        self.addressEdit.textChanged.connect(self._updateConfigFromFields)
        self.typeList.currentTextChanged.connect(self._updateConfigFromFields)
        self.port1Edit.textChanged.connect(self._updateConfigFromFields)
        self.port2Edit.textChanged.connect(self._updateConfigFromFields)
        self.usernameEdit.textChanged.connect(self._updateConfigFromFields)
        self.sshKeyEdit.textChanged.connect(self._updateConfigFromFields)
        self.deviceList.itemChanged.connect(self._updateConfigFromFields)

        # UI updates
        self.addressEdit.textChanged.connect(self._setServerTypeFromAddress)
        self.typeList.currentTextChanged.connect(self._changeRemoteFieldsVisibility)
        self.getDevicesBtn.clicked.connect(self._setDevices)
        self.deviceList.itemClicked.connect(self._deviceListSetCheckboxOnClick)

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

    def _deviceListSetCheckboxOnClick(self, item: 'DeviceListWidgetItem') -> None:
        if not item:
            return
        item.setCheckState(not item.checkState())

    def _setDevicesFromConfig(self):
        self.deviceList.clear()
        for checked, id_, name in self.config.get("devices", []):
            item = DeviceListWidgetItem(id_, name, self.deviceList)
            item.setCheckState(checked)

    def _setDevices(self):
        current_devices = self.config.get("devices", [])

        def get_device_state(id_):
            for dev in current_devices:
                if dev[1] == id_:
                    return dev[0]
            return False

        devices = self._device_getter(self._config)

        new_devices = []

        for id_, name in devices:
            state = get_device_state(id_)
            new_devices.append((state, id_, name))

        self.config = {**self.config, "devices": new_devices}
        self.gotDevices.emit()

    def _getDevices(self):
        result = []
        for idx in range(self.deviceList.count()):
            item = self.deviceList.item(idx)
            result.append((bool(item.checkState()), item.id, item.name))
        return result

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
        self._config["devices"] = self._getDevices()

    def _updateFieldsFromConfig(self):
        with self._batch_update_fields():
            self.nameEdit.setText(self._config.get("name", ""))
            self.addressEdit.setText(self._config.get("address", ""))
            self.typeList.setCurrentText(self._config.get("type", ""))
            self.port1Edit.setText(self._config.get("port1", ""))
            self.port2Edit.setText(self._config.get("port2", ""))
            self.usernameEdit.setText(self._config.get("username", ""))
            self.sshKeyEdit.setText(self._config.get("ssh_key", ""))
            self._setDevicesFromConfig()

    def keyPressEvent(self, event):
        if event.type() == QEvent.KeyPress:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                if self.saveBtn.isEnabled():
                    self.saveBtn.click()

        super().keyPressEvent(event)


class ServerFormWorkflow:
    class CheckedTranstion(QSignalTransition):
        def __init__(self, signal, *, target, testFn):
            super().__init__(signal)
            self.setTargetState(target)
            self._testFn = testFn

        def eventTest(self, event) -> bool:
            if not super().eventTest(event):
                return False

            return self._testFn()

    def __init__(self, form) -> None:
        self._form = form

        self._machine = machine = QStateMachine()

        init = self._make_initial_state(form)
        dev_fetched = self._make_dev_fetched_state(form)
        save = self._make_save_state(form)

        machine.addState(init)
        machine.addState(dev_fetched)
        machine.addState(save)
        machine.setInitialState(init)

        init.addTransition(form.gotDevices, dev_fetched)

        unselected_tr = self.CheckedTranstion(
            form.deviceList.itemChanged, target=dev_fetched, testFn=lambda: not self._hasSelectedItems()
        )
        save.addTransition(unselected_tr)
        save.addTransition(form.editBtn.clicked, init)

        selected_tr = self.CheckedTranstion(form.deviceList.itemChanged, target=save, testFn=self._hasSelectedItems)
        entered_dev_feched = self.CheckedTranstion(dev_fetched.entered, target=save, testFn=self._hasSelectedItems)

        dev_fetched.addTransition(selected_tr)
        dev_fetched.addTransition(entered_dev_feched)
        dev_fetched.addTransition(form.editBtn.clicked, init)

        machine.start()

    def _hasSelectedItems(self):
        for idx in range(self._form.deviceList.count()):
            if self._form.deviceList.item(idx).checkState():
                return True

        return False

    def _make_initial_state(self, form) -> QState:
        s = QState()
        s.assignProperty(form.editBtn, "enabled", False)
        s.assignProperty(form.saveBtn, "enabled", False)
        s.assignProperty(form.deviceList, "enabled", False)
        s.assignProperty(form.addressEdit, "enabled", True)
        s.assignProperty(form.typeList, "enabled", True)
        # Inputs
        s.assignProperty(form.usernameEdit, "enabled", True)
        s.assignProperty(form.sshKeyEdit, "enabled", True)
        s.assignProperty(form.port1Edit, "enabled", True)
        s.assignProperty(form.port2Edit, "enabled", True)
        return s

    def _make_dev_fetched_state(self, form) -> QState:
        s = QState()
        s.assignProperty(form.editBtn, "enabled", True)
        s.assignProperty(form.deviceList, "enabled", True)
        s.assignProperty(form.saveBtn, "enabled", False)
        s.assignProperty(form.port1Edit, "enabled", False)
        s.assignProperty(form.port2Edit, "enabled", False)
        s.assignProperty(form.addressEdit, "enabled", False)
        s.assignProperty(form.usernameEdit, "enabled", False)
        s.assignProperty(form.sshKeyEdit, "enabled", False)

        s.assignProperty(form.typeList, "enabled", False)
        return s

    def _make_save_state(self, form):
        s = QState()
        s.assignProperty(form.saveBtn, "enabled", True)
        return s


class DeviceListWidgetItem(QListWidgetItem):
    def __init__(self, id, name, parent):
        super().__init__(parent, type=QListWidgetItem.UserType)
        self.id = id
        self.name = name
        self.setText(f"{id} ({name})")
        self.setCheckState(Qt.Unchecked)
        # Negation of Qt.ItemIsUserCheckable so we would be able to toggle check state on line click
        # otherwise it will immidiatelly uncheck
        self.setFlags(self.flags() & (~Qt.ItemIsUserCheckable))

    def __repr__(self) -> str:
        return f'DeviceListWidgetItem(id: {self.id})'
