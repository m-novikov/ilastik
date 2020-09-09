###############################################################################
#   ilastik: interactive learning and segmentation toolkit
#
#       Copyright (C) 2011-2014, the ilastik developers
#                                <team@ilastik.org>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# In addition, as a special exception, the copyright holders of
# ilastik give you permission to combine ilastik with applets,
# workflows and plugins which are not covered under the GNU
# General Public License.
#
# See the LICENSE file for details. License information is also available
# on the ilastik web site at:
#          http://ilastik.org/license.html
###############################################################################
import os
import logging

from functools import partial
from collections import OrderedDict

import numpy
import yaml

from ilastik.widgets.progressDialog import PercentProgressDialog
from PyQt5 import uic
from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal, QTimer, QStringListModel, QObject, QModelIndex, QPersistentModelIndex
from PyQt5.QtGui import QColor, QIcon
from PyQt5.QtWidgets import (
    QWidget,
    QStackedWidget,
    QFileDialog,
    QMenu,
    QLineEdit,
    QVBoxLayout,
    QDialog,
    QGridLayout,
    QLabel,
    QPushButton,
    QHBoxLayout,
    QDesktopWidget,
    QComboBox,
)

from ilastik.applets.labeling.labelingGui import LabelingGui
from ilastik.utility.gui import threadRouted
from ilastik.utility import bind
from ilastik.shell.gui.iconMgr import ilastikIcons
from .tiktorchController import TiktorchController

from volumina.api import LazyflowSource, AlphaModulatedLayer, GrayscaleLayer
from volumina.utility import preferences

from lazyflow.operators import tiktorch
from lazyflow.cancel_token import CancellationTokenSource
from tiktorch.types import ModelState
from tiktorch.configkeys import TRAINING, NUM_ITERATIONS_DONE, NUM_ITERATIONS_MAX

logger = logging.getLogger(__name__)


def _listReplace(old, new):
    if len(old) > len(new):
        return new + old[len(new) :]
    else:
        return new




class ParameterDlg(QDialog):
    """
    simple window for setting parameters
    """

    def __init__(self, parent):
        self.hparams = None

        super(QDialog, self).__init__(parent=parent)

        self.optimizer_combo = QComboBox(self)
        self.optimizer_combo.addItem("Adam")
        self.optimizer_kwargs_textbox = QLineEdit()
        self.optimizer_kwargs_textbox.setPlaceholderText(
            "e.g. for Adam: {'lr': 0.0003, 'weight_decay':0.0001, amsgrad: True}"
        )

        self.criterion_combo = QComboBox(self)
        self.criterion_combo.addItem("BCEWithLogitsLoss")
        self.criterion_kwargs_textbox = QLineEdit()
        self.criterion_kwargs_textbox.setPlaceholderText("e.g.: {'reduce': False}")

        self.batch_size_textbox = QLineEdit()
        self.batch_size_textbox.setPlaceholderText("default: 1")

        grid = QGridLayout()
        grid.setSpacing(10)

        grid.addWidget(QLabel("Optimizer"), 1, 0)
        grid.addWidget(self.optimizer_combo, 1, 1)

        grid.addWidget(QLabel("Optimizer keyword arguments"), 2, 0)
        grid.addWidget(self.optimizer_kwargs_textbox, 2, 1)

        grid.addWidget(QLabel("Criterion"), 3, 0)
        grid.addWidget(self.criterion_combo, 3, 1)

        grid.addWidget(QLabel("Criterion keyword arguments"), 4, 0)
        grid.addWidget(self.criterion_kwargs_textbox, 4, 1)

        grid.addWidget(QLabel("Batch size"), 5, 0)
        grid.addWidget(self.batch_size_textbox, 5, 1)

        okButton = QPushButton("OK")
        okButton.clicked.connect(self.readParameters)
        cancelButton = QPushButton("Cancel")
        cancelButton.clicked.connect(self.close)

        hbox = QHBoxLayout()
        hbox.addStretch(1)
        hbox.addWidget(okButton)
        hbox.addWidget(cancelButton)

        vbox = QVBoxLayout()
        vbox.addLayout(grid)
        vbox.addLayout(hbox)

        self.setLayout(vbox)

        # self.resize(480, 200)
        self.setFixedSize(600, 200)
        self.center()

        self.setWindowTitle("Hyperparameter Settings")
        self.show()

    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)

        self.move(qr.topLeft())

    def readParameters(self):
        optimizer = self.optimizer_combo.currentText()
        optimizer_kwargs = yaml.load(self.optimizer_kwargs_textbox.text())
        if optimizer_kwargs is None:
            optimizer_kwargs = dict(lr=0.0003, weight_decay=0.0001, amsgrad=True)
            optimizer = "Adam"
        criterion = self.criterion_combo.currentText()
        criterion_kwargs = yaml.load(self.criterion_kwargs_textbox.text())
        if criterion_kwargs is None:
            criterion_kwargs = dict(reduce=False)
            criterion = "BCEWithLogitsLoss"
        batch_size = int(self.batch_size_textbox.text()) if len(self.batch_size_textbox.text()) > 0 else 1

        self.hparams = dict(
            optimizer_kwargs=optimizer_kwargs,
            optimizer_name=optimizer,
            criterion_kwargs=criterion_kwargs,
            criterion_name=criterion,
            batch_size=batch_size,
        )

        self.close()


class ValidationDlg(QDialog):
    """
    Settings for choosing the validation set
    """

    def __init__(self, parent):
        self.valid_params = None

        super(QDialog, self).__init__(parent=parent)

        self.validation_size = QComboBox(self)
        self.validation_size.addItem("10%")
        self.validation_size.addItem("20%")
        self.validation_size.addItem("30%")
        self.validation_size.addItem("40%")

        self.orientation = QComboBox(self)
        self.orientation.addItem("Top - Left")
        self.orientation.addItem("Top - Right")
        self.orientation.addItem("Top - Mid")
        self.orientation.addItem("Mid - Left")
        self.orientation.addItem("Mid - Right")
        self.orientation.addItem("Mid - Mid")
        self.orientation.addItem("Bottom - Left")
        self.orientation.addItem("Bottom - Right")
        self.orientation.addItem("Bottom - Mid")

        grid = QGridLayout()
        grid.setSpacing(10)

        grid.addWidget(QLabel("Validation Set Size"), 1, 0)
        grid.addWidget(self.validation_size, 1, 1)

        grid.addWidget(QLabel("Orientation"), 2, 0)
        grid.addWidget(self.orientation, 2, 1)

        okButton = QPushButton("OK")
        okButton.clicked.connect(self.readParameters)
        cancelButton = QPushButton("Cancel")
        cancelButton.clicked.connect(self.close)

        hbox = QHBoxLayout()
        hbox.addStretch(1)
        hbox.addWidget(okButton)
        hbox.addWidget(cancelButton)

        vbox = QVBoxLayout()
        vbox.addLayout(grid)
        vbox.addLayout(hbox)

        self.setLayout(vbox)

        self.center()

        self.setWindowTitle("Validation Set Settings")
        self.show()

    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)

        self.move(qr.topLeft())

    def readParameters(self):
        percentage = self.validation_size.currentText()[:-1]
        orientation = self.orientation.currentText()
        self.valid_params = dict(percentage=percentage, orientation=orientation)

        self.close()


class CheckpointManager:
    def __init__(self, widget, get_state, load_state, added, data):
        self._checkpoint_by_idx = {}

        self._get_state = get_state
        self._load_state = load_state
        self._added = added

        self._widget = widget
        self._widget.add_clicked.connect(self._add)
        self._widget.remove_clicked.connect(self._remove)
        self._widget.load_clicked.connect(self._load)

        self._load_data(data)
        self._count = 0

    def setData(self, data):
        self._load_data(data)

    def _load_data(self, data):
        self._widget.clear()
        self._checkpoint_by_idx = {}
        for entry in data:
            idx = self._widget.add_item(entry["name"])
            self._checkpoint_by_idx[idx] = entry

    def _add(self):
        state = self._get_state()
        self._count += 1
        name = f"{self._count}: Epoch: {state.epoch}. Loss: {state.loss}"

        idx = self._widget.add_item(name)
        self._checkpoint_by_idx[idx] = {"name": name, "state": state}
        self._added(self._checkpoint_by_idx.values())

    def _remove(self, removed_idx):
        del self._checkpoint_by_idx[removed_idx]
        self._widget.remove_item(removed_idx)

    def _load(self, load_idx):
        if load_idx.isValid():
            val = self._checkpoint_by_idx[load_idx]
            self._load_state(val["state"])


class CheckpointWidget(QWidget):
    add_clicked = pyqtSignal()
    remove_clicked = pyqtSignal(QPersistentModelIndex)
    load_clicked = pyqtSignal(QPersistentModelIndex)

    def __init__(self, *, parent, add, remove, load, view):
        super().__init__(parent=parent)

        self._add_btn = add
        self._remove_btn = remove
        self._load_btn = load
        self._view = view

        self._model = QStringListModel()
        self._view.setModel(self._model)

        self._add_btn.clicked.connect(self.add_clicked)
        self._remove_btn.clicked.connect(self._remove_click)
        self._load_btn.clicked.connect(self._load_click)

    def clear(self):
        self._model.setStringList([])

    def add_item(self, name: str) -> QPersistentModelIndex:
        self._model.insertRow(0)
        m_idx = self._model.index(0)
        self._model.setData(m_idx, name)
        return QPersistentModelIndex(m_idx)

    def remove_item(self, idx: QModelIndex):
        if idx.isValid():
            self._model.removeRow(idx.row())

    def _remove_click(self):
        idx = self._view.selectionModel().currentIndex()
        if idx.isValid():
            self.remove_clicked.emit(QPersistentModelIndex(idx))

    def _load_click(self):
        idx = self._view.selectionModel().currentIndex()
        if idx.isValid():
            self.load_clicked.emit(QPersistentModelIndex(idx))



class NNClassGui(LabelingGui):
    """
    LayerViewerGui class for Neural Network Classification
    """

    def viewerControlWidget(self):
        """
        Return the widget that controls how the content of the central widget is displayed
        """
        return self._viewerControlUi

    def centralWidget(self):
        """
        Return the widget that will be displayed in the main viewer area.
        """
        return self

    def stopAndCleanUp(self):
        """
        The gui should stop updating all data views and should clean up any resources it created
        """
        for fn in self.__cleanup_fns:
            fn()

        super(NNClassGui, self).stopAndCleanUp()

    def menus(self):
        """
        Return a list of QMenu widgets to be shown in the menu bar when this applet is visible
        """
        menus = super(NNClassGui, self).menus()

        advanced_menu = QMenu("TikTorch", parent=self)

        def settingParameter():
            """
            changing BatchSize
            """
            dlg = ParameterDlg(parent=self)
            dlg.exec_()

            self.topLevelOperatorView.update_config(dlg.hparams)

        set_parameter = advanced_menu.addAction("Set hyperparameters")
        set_parameter.triggered.connect(settingParameter)

        def object_wizard():
            wizard = MagicWizard()
            wizard.show()
            wizard.exec_()

        advanced_menu.addAction("Create TikTorch configuration").triggered.connect(object_wizard)

        def validationMenu():
            """
            set up the validation Menu
            """
            dlg = ValidationDlg(parent=self)
            dlg.exec_()

        advanced_menu.addAction("Validation Set").triggered.connect(validationMenu)

        menus += [advanced_menu]

        return menus

    def _get_model_state(self):
        factory = self.topLevelOperatorView.ClassifierFactory[:].wait()[0]
        return factory.get_model_state()

    def _added(self, snapshot):
        self.topLevelOperatorView.Checkpoints.setValue(list(snapshot))

    def checkpoints_dirty(self, slot, roi):
        self.checkpoint_mng.setData(slot.value)

    def _initCheckpointActions(self):
        self.checkpoint_widget = CheckpointWidget(
            parent=self,
            add=self.labelingDrawerUi.addCheckpoint,
            remove=self.labelingDrawerUi.removeCheckpoint,
            load=self.labelingDrawerUi.loadCheckpoint,
            view=self.labelingDrawerUi.checkpointList,
        )
        self.topLevelOperatorView.Checkpoints.notifyDirty(self.checkpoints_dirty)
        self.checkpoint_mng = CheckpointManager(
            self.checkpoint_widget,
            self._get_model_state,
            self._load_checkpoint,
            self._added,
            data=self.topLevelOperatorView.Checkpoints.value,
        )

    def __init__(self, parentApplet, topLevelOperatorView, labelingDrawerUiPath=None):
        labelSlots = LabelingGui.LabelingSlots()
        labelSlots.labelInput = topLevelOperatorView.LabelInputs
        labelSlots.labelOutput = topLevelOperatorView.LabelImages
        labelSlots.labelEraserValue = topLevelOperatorView.opLabelPipeline.opLabelArray.eraser
        labelSlots.labelDelete = topLevelOperatorView.opLabelPipeline.DeleteLabel
        labelSlots.labelNames = topLevelOperatorView.LabelNames

        if labelingDrawerUiPath is None:
            localDir = os.path.split(__file__)[0]
            labelingDrawerUiPath = os.path.join(localDir, "nnClassAppletUiTest.ui")

        super(NNClassGui, self).__init__(parentApplet, labelSlots, topLevelOperatorView, labelingDrawerUiPath)

        self._initCheckpointActions()

        self.parentApplet = parentApplet
        self.classifiers = OrderedDict()

        self.liveTraining = False
        self.livePrediction = False

        self.__cleanup_fns = []

        self.labelingDrawerUi.liveTraining.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.labelingDrawerUi.liveTraining.toggled.connect(self.toggleLiveTraining)

        self.labelingDrawerUi.livePrediction.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.set_live_predict_icon(self.livePrediction)
        self.labelingDrawerUi.livePrediction.toggled.connect(self.toggleLivePrediction)

        self.labelingDrawerUi.addModel.clicked.connect(self.addModelClicked)
        self.labelingDrawerUi.closeModel.setIcon(QIcon(ilastikIcons.ProcessStop))
        self.labelingDrawerUi.closeModel.clicked.connect(self.closeModelClicked)
        self.labelingDrawerUi.uploadModel.setIcon(QIcon(ilastikIcons.Upload))
        self.labelingDrawerUi.uploadModel.clicked.connect(self.uploadModelClicked)

        self.initViewerControls()
        self.initViewerControlUi()

        self.labelingDrawerUi.labelListView.support_merges = True
        self.batch_size = self.topLevelOperatorView.Batch_Size.value
        self.labelingDrawerUi.labelListView.allowDelete = False
        self.labelingDrawerUi.AddLabelButton.setEnabled(False)
        self.labelingDrawerUi.AddLabelButton.hide()

        self.topLevelOperatorView.LabelNames.notifyDirty(bind(self.handleLabelSelectionChange))
        self.__cleanup_fns.append(
            partial(self.topLevelOperatorView.LabelNames.unregisterDirty, bind(self.handleLabelSelectionChange))
        )
        self.__cleanup_fns.append(self.topLevelOperatorView.cleanUp)

        self.forceAtLeastTwoLabels(True)

        self.invalidatePredictionsTimer = QTimer()
        self.invalidatePredictionsTimer.timeout.connect(self.updatePredictions)
        self.tiktorchController = parentApplet.tiktorchController
        #self._stateMachine = NNGuiStateMachineBuilder(self.labelingDrawerUi, self.tiktorchController)
        self.tiktorchController.registerListener(self._onModelStateChanged)
        self._progress = PercentProgressDialog(self, title="Uploading model")

    def set_live_training_icon(self, active: bool):
        if active:
            self.labelingDrawerUi.liveTraining.setIcon(QIcon(ilastikIcons.Pause))
            self.labelingDrawerUi.liveTraining.setText("Pause and Download")
            self.labelingDrawerUi.liveTraining.setToolTip("Pause training and download model state")
        else:
            self.labelingDrawerUi.liveTraining.setText("Live Training")
            self.labelingDrawerUi.liveTraining.setToolTip("")
            self.labelingDrawerUi.liveTraining.setIcon(QIcon(ilastikIcons.Play))

    def set_live_predict_icon(self, active: bool):
        if active:
            self.labelingDrawerUi.livePrediction.setIcon(QIcon(ilastikIcons.Pause))
        else:
            self.labelingDrawerUi.livePrediction.setIcon(QIcon(ilastikIcons.Play))

    def updatePredictions(self):
        logger.info("Invalidating predictions")
        self.topLevelOperatorView.FreezePredictions.setValue(False)
        self.topLevelOperatorView.classifier_cache.Output.setDirty()
        # current_classifier = self.topLevelOperatorView.Classifier[:]
        # current_classifier.wait()
        # self.topLevelOperatorView.FreezePredictions.setValue(True)

    def initViewerControls(self):
        """
        initializing viewerControl
        """
        self._viewerControlWidgetStack = QStackedWidget(parent=self)

    def initViewerControlUi(self):
        """
        Load the viewer controls GUI, which appears below the applet bar.
        In our case, the viewer control GUI consists mainly of a layer list.
        """
        localDir = os.path.split(__file__)[0]
        self._viewerControlUi = uic.loadUi(os.path.join(localDir, "viewerControls.ui"))

        def nextCheckState(checkbox):
            """
            sets the checkbox to the next state
            """
            checkbox.setChecked(not checkbox.isChecked())

        self._viewerControlUi.checkShowPredictions.nextCheckState = partial(
            nextCheckState, self._viewerControlUi.checkShowPredictions
        )
        self._viewerControlUi.checkShowPredictions.clicked.connect(self.handleShowPredictionsClicked)

        model = self.editor.layerStack
        self._viewerControlUi.viewerControls.setupConnections(model)

    def setupLayers(self):
        """
        which layers will be shown in the layerviewergui.
        Triggers the prediction by setting the layer on visible
        """

        layers = super(NNClassGui, self).setupLayers()

        labels = self.labelListData

        # validationlayer = AlphaModulatedLayer()

        for channel, predictionSlot in enumerate(self.topLevelOperatorView.PredictionProbabilityChannels):
            logger.info(f"prediction_slot: {predictionSlot}")
            if predictionSlot.ready() and channel < len(labels):
                ref_label = labels[channel]
                predictsrc = LazyflowSource(predictionSlot)
                predictionLayer = AlphaModulatedLayer(
                    predictsrc, tintColor=ref_label.pmapColor(), normalize=(0.0, 1.0)
                )
                predictionLayer.visible = self.labelingDrawerUi.livePrediction.isChecked()
                predictionLayer.opacity = 0.25
                predictionLayer.visibleChanged.connect(self.updateShowPredictionCheckbox)

                def setLayerColor(c, predictLayer_=predictionLayer, initializing=False):
                    if not initializing and predictLayer_ not in self.layerstack:
                        # This layer has been removed from the layerstack already.
                        # Don't touch it.
                        return
                    predictLayer_.tintColor = c

                def setPredLayerName(n, predictLayer_=predictionLayer, initializing=False):
                    """
                    function for setting the names for every Channel
                    """
                    if not initializing and predictLayer_ not in self.layerstack:
                        # This layer has been removed from the layerstack already.
                        # Don't touch it.
                        return
                    newName = "Prediction for %s" % n
                    predictLayer_.name = newName

                setPredLayerName(channel, initializing=True)
                setPredLayerName(ref_label.name, initializing=True)
                ref_label.pmapColorChanged.connect(setLayerColor)
                ref_label.nameChanged.connect(setPredLayerName)
                layers.append(predictionLayer)

        # Add the raw data last (on the bottom)
        inputDataSlot = self.topLevelOperatorView.InputImages
        if inputDataSlot.ready():
            inputLayer = self.createStandardLayerFromSlot(inputDataSlot)
            inputLayer.name = "Input Data"
            inputLayer.visible = True
            inputLayer.opacity = 1.0
            # the flag window_leveling is used to determine if the contrast
            # of the layer is adjustable
            if isinstance(inputLayer, GrayscaleLayer):
                inputLayer.window_leveling = True
            else:
                inputLayer.window_leveling = False

            def toggleTopToBottom():
                index = self.layerstack.layerIndex(inputLayer)
                self.layerstack.selectRow(index)
                if index == 0:
                    self.layerstack.moveSelectedToBottom()
                else:
                    self.layerstack.moveSelectedToTop()

            layers.append(inputLayer)

            # The thresholding button can only be used if the data is displayed as grayscale.
            if inputLayer.window_leveling:
                self.labelingDrawerUi.thresToolButton.show()
            else:
                self.labelingDrawerUi.thresToolButton.hide()

        self.handleLabelSelectionChange()

        return layers

    def toggleLivePrediction(self, checked):
        logger.debug("toggle live prediction mode to %r", checked)
        self.labelingDrawerUi.livePrediction.setEnabled(False)

        # If we're changing modes, enable/disable our controls and other applets accordingly
        if self.livePrediction != checked:
            if checked:
                self.updatePredictions()

            self.livePrediction = checked
            self.labelingDrawerUi.livePrediction.setChecked(checked)
            self.set_live_predict_icon(checked)

        self.topLevelOperatorView.FreezePredictions.setValue(not checked)

        # Auto-set the "show predictions" state according to what the user just clicked.
        if checked:
            self._viewerControlUi.checkShowPredictions.setChecked(True)
            self.handleShowPredictionsClicked()

        # Notify the workflow that some applets may have changed state now.
        # (For example, the downstream pixel classification applet can
        #  be used now that there are features selected)
        self.parentApplet.appletStateUpdateRequested()
        self.labelingDrawerUi.livePrediction.setEnabled(True)

    @property
    def connectionFactory(self) -> tiktorch.IConnectionFactory:
        return self.parentApplet.connectionFactory

    def toggleLiveTraining(self, checked):
        logger.debug("toggle live training, checked: %r", checked)
        if not self.topLevelOperatorView.ClassifierFactory.ready():
            checked = False

        if self.liveTraining != checked:
            self.labelingDrawerUi.liveTraining.setEnabled(False)
            self.liveTraining = checked
            factory = self.topLevelOperatorView.ClassifierFactory[:].wait()[0]
            factory.train_model = checked
            self.set_live_training_icon(checked)
            if checked:
                self.toggleLivePrediction(True)
                factory.resume_training()
                self.invalidatePredictionsTimer.start(60000)  # start updating regularly
            else:
                factory.pause_training()
                self.invalidatePredictionsTimer.stop()
                self.updatePredictions()  # update one last time
                try:
                    model_state = factory.get_model_state()
                    model = self.topLevelOperatorView.model
                    config = model.config
                    config[TRAINING][NUM_ITERATIONS_DONE] = model_state.num_iterations_done
                    config[TRAINING][NUM_ITERATIONS_MAX] = model_state.num_iterations_max
                    self.topLevelOperatorView.Model.disconnect()
                    self.topLevelOperatorView.ModelState.setValue(model_state)
                    self.topLevelOperatorView.Model.setValue(model)
                except Exception as e:
                    logger.warning(f"Could not retrieve updated model state due to {e}")

            self.labelingDrawerUi.liveTraining.setEnabled(True)

        self.parentApplet.appletStateUpdateRequested()

    @pyqtSlot()
    def handleShowPredictionsClicked(self):
        """
        sets the layer visibility when showPredicition is clicked
        """
        checked = self._viewerControlUi.checkShowPredictions.isChecked()
        for layer in self.layerstack:
            if "Prediction" in layer.name:
                layer.visible = checked

    @pyqtSlot()
    def updateShowPredictionCheckbox(self):
        """
        updates the showPrediction Checkbox when Predictions were added to the layers
        """
        predictLayerCount = 0
        visibleCount = 0
        for layer in self.layerstack:
            if "Prediction" in layer.name:
                predictLayerCount += 1
                if layer.visible:
                    visibleCount += 1

        if visibleCount == 0:
            self._viewerControlUi.checkShowPredictions.setCheckState(Qt.Unchecked)
        elif predictLayerCount == visibleCount:
            self._viewerControlUi.checkShowPredictions.setCheckState(Qt.Checked)
        else:
            self._viewerControlUi.checkShowPredictions.setCheckState(Qt.PartiallyChecked)

    def closeModelClicked(self):
        self.tiktorchController.closeModel()

    def cc(self, *args, **kwargs):
        self.cancel_src.cancel()
        print("CANCEL CLICKED", args, kwargs)

    def addModelClicked(self):
        """
        When AddModel button is clicked.
        """
        # open dialog in recent model folder if possible
        folder = preferences.get("DataSelection", "recent model")
        if folder is None:
            folder = os.path.expanduser("~")

        # get folder from user
        filename = self.getModelToOpen(self, folder)

        if filename:
            projectManager = self.parentApplet._StandardApplet__workflow._shell.projectManager
            # save whole project (specifically important here: the labels)
            if not projectManager.currentProjectIsReadOnly:
                projectManager.saveProject()

            cancel_src = self.cancel_src = CancellationTokenSource()
            dialog = PercentProgressDialog(self, title="Uploading model")
            dialog.cancel.connect(cancel_src.cancel)
            dialog.cancel.connect(self.cc)
            progress = self.tiktorchController.loadModel(filename, progress_cb=dialog.updateProgress, cancel_token=cancel_src.token)
            dialog.open()

            preferences.set("DataSelection", "recent model", filename)
            self.parentApplet.appletStateUpdateRequested()

    def uploadModelClicked(self):
        progress = self.tiktorchController.uploadModel()
        #print("PROGReSS", progress)
        #self.openProgressDialog(progress)

    def _onModelStateChanged(self, state):
        self.labelingDrawerUi.liveTraining.setVisible(False)
        self.labelingDrawerUi.checkpoints.setVisible(False)
        print("STATE", state)

        if state == TiktorchController.State.Empty:
            self.labelingDrawerUi.addModel.setText("Load model")
            self.labelingDrawerUi.addModel.setEnabled(True)
            self.labelingDrawerUi.closeModel.setEnabled(False)
            self.labelingDrawerUi.uploadModel.setEnabled(False)
            self.labelingDrawerUi.livePrediction.setEnabled(False)
            self.updateAllLayers()

        elif state == TiktorchController.State.ReadFromProjectFile:
            info = self.tiktorchController.modelInfo

            self.labelingDrawerUi.addModel.setText(f"{info.name}")
            self.labelingDrawerUi.addModel.setEnabled(True)
            self.labelingDrawerUi.closeModel.setEnabled(True)
            self.labelingDrawerUi.uploadModel.setEnabled(True)
            self.labelingDrawerUi.livePrediction.setEnabled(False)

            self.minLabelNumber = info.numClasses
            self.maxLabelNumber = info.numClasses

            self.updateAllLayers()

        elif state == TiktorchController.State.Ready:
            info = self.tiktorchController.modelInfo

            self.labelingDrawerUi.addModel.setText(f"{info.name}")
            self.labelingDrawerUi.addModel.setEnabled(True)
            self.labelingDrawerUi.closeModel.setEnabled(True)
            self.labelingDrawerUi.uploadModel.setEnabled(False)
            self.labelingDrawerUi.livePrediction.setEnabled(True)

            self.minLabelNumber = info.numClasses
            self.maxLabelNumber = info.numClasses
            self.updateAllLayers()
            self._progress.close()

        elif state == TiktorchController.State.Uploading:
            #self.tiktorchController.removeListener(self._onModelStateChanged)
            #self._progress.updateProgress(self.tiktorchController.progress)
            #self.openProgressDialog(self.tiktorchController.progress)
            #self.tiktorchController.registerListener(self._onModelStateChanged)
            pass

        elif state == TiktorchController.State.Error:
            self.labelingDrawerUi.addModel.setEnabled(True)
            self._progress.close()

    def _load_checkpoint(self, model_state: ModelState):
        self.topLevelOperatorView.set_model_state(model_state)


    @classmethod
    def getModelToOpen(cls, parent_window, defaultDirectory):
        """
        opens a QFileDialog for importing files
        """
        return QFileDialog.getOpenFileName(parent_window, "Select Model", defaultDirectory, "Models (*.tmodel *.zip)")[
            0
        ]

    @pyqtSlot()
    @threadRouted
    def handleLabelSelectionChange(self):
        enabled = False
        if self.topLevelOperatorView.LabelNames.ready():
            enabled = True
            enabled &= len(self.topLevelOperatorView.LabelNames.value) >= 2
            enabled &= numpy.all(numpy.asarray(self.topLevelOperatorView.InputImages.meta.shape) > 0)

            self.labelingDrawerUi.livePrediction.setChecked(False)
            self.labelingDrawerUi.livePrediction.setIcon(QIcon(ilastikIcons.Play))
            self._viewerControlUi.checkShowPredictions.setChecked(False)
            self.handleShowPredictionsClicked()

        self._viewerControlUi.checkShowPredictions.setEnabled(enabled)

    def _getNext(self, slot, parentFun, transform=None):
        numLabels = self.labelListData.rowCount()
        value = slot.value
        if numLabels < len(value):
            result = value[numLabels]
            if transform is not None:
                result = transform(result)
            return result
        else:
            return parentFun()

    def _onLabelChanged(self, parentFun, mapf, slot):
        parentFun()
        new = list(map(mapf, self.labelListData))
        old = slot.value
        slot.setValue(_listReplace(old, new))

    def getNextLabelName(self):
        return self._getNext(self.topLevelOperatorView.LabelNames, super(NNClassGui, self).getNextLabelName)

    def getNextLabelColor(self):
        return self._getNext(
            self.topLevelOperatorView.LabelColors, super(NNClassGui, self).getNextLabelColor, lambda x: QColor(*x)
        )

    def getNextPmapColor(self):
        return self._getNext(
            self.topLevelOperatorView.PmapColors, super(NNClassGui, self).getNextPmapColor, lambda x: QColor(*x)
        )

    def onLabelNameChanged(self):
        self._onLabelChanged(
            super(NNClassGui, self).onLabelNameChanged, lambda l: l.name, self.topLevelOperatorView.LabelNames
        )

    def onLabelColorChanged(self):
        self._onLabelChanged(
            super(NNClassGui, self).onLabelColorChanged,
            lambda l: (l.brushColor().red(), l.brushColor().green(), l.brushColor().blue()),
            self.topLevelOperatorView.LabelColors,
        )

    def onPmapColorChanged(self):
        self._onLabelChanged(
            super(NNClassGui, self).onPmapColorChanged,
            lambda l: (l.pmapColor().red(), l.pmapColor().green(), l.pmapColor().blue()),
            self.topLevelOperatorView.PmapColors,
        )

    def _update_rendering(self):
        if not self.render:
            return
        shape = self.topLevelOperatorView.InputImages.meta.shape[1:4]
        if len(shape) != 5:
            # this might be a 2D image, no need for updating any 3D stuff
            return

        time = self.editor.posModel.slicingPos5D[0]
        if not self._renderMgr.ready:
            self._renderMgr.setup(shape)

        layernames = set(layer.name for layer in self.layerstack)
        self._renderedLayers = dict((k, v) for k, v in self._renderedLayers.items() if k in layernames)

        newvolume = numpy.zeros(shape, dtype=numpy.uint8)
        for layer in self.layerstack:
            try:
                label = self._renderedLayers[layer.name]
            except KeyError:
                continue
            for ds in layer.datasources:
                vol = ds.dataSlot.value[time, ..., 0]
                indices = numpy.where(vol != 0)
                newvolume[indices] = label

        self._renderMgr.volume = newvolume
        self._update_colors()
        self._renderMgr.update()

    def _update_colors(self):
        for layer in self.layerstack:
            try:
                label = self._renderedLayers[layer.name]
            except KeyError:
                continue
            color = layer.tintColor
            color = (color.red() / 255.0, color.green() / 255.0, color.blue() / 255.0)
            self._renderMgr.setColor(label, color)
