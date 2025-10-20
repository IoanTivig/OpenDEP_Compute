# ------------------------------------------------------
# ----------------- CONVERSION MODULE ------------------
# ------------------------------------------------------
import cv2
import numpy as np
# External imports #
from PyQt5.QtCore import QThread
from PyQt5.QtGui import QIntValidator, QDoubleValidator
from PyQt5.QtWidgets import QDialog, QFileDialog
from PyQt5.uic import loadUi
from PyQt5 import QtGui

# Local imports #
from src.conversion import *
from src.conversion_opendep_single import ConversionOpenDEPSC
from src.threads.workers_convert import ConvertWorker
from ui.resources.graphical_resources import *

"""
Conversion UI script:
This file covers all UI related functionality to the convert module
All buttons and widgets are connected and run either directly scripts found
in src/conversion module for short running scripts or in a thread (in this case
the thread setup can be found in src/threads/workers_convert.py)
"""


class ConvertUI(QDialog):
    def __init__(self, window, data):
        QDialog.__init__(self)
        loadUi("ui/convert.ui", self)
        self.setWindowTitle("Convert")
        self.setWindowIcon(QtGui.QIcon("ui/resources/logos/opendep_logo_1.png"))

        self.qtvar_convertImages_closeButton.clicked.connect(self.close)
        self.qtvar_convertImages_convertButton.clicked.connect(self.convert)
        self.qtvar_convertImages_testButton.clicked.connect(self.test_edge_detection)
        self.pyqt5_dynamic_odsc_button_detect_cells.clicked.connect(self.detect_cells)

        self.qtvar_convertImages_inputFolder.setText(os.path.expanduser("~/Desktop"))
        self.qtvar_convertImages_inputEdgesFile.setText(os.path.expanduser("~/Desktop"))
        self.qtvar_convertImages_filename.setText("Centralization")

        self.qtvar_convertImages_inputFolderButton.clicked.connect(
            lambda: self.getFolderPath(self.qtvar_convertImages_inputFolder)
        )
        self.qtvar_convertImages_inputEdgesButton.clicked.connect(
            lambda: self.getEdgesFilePath(self.qtvar_convertImages_inputEdgesFile)
        )

        self.pyqt5_dynamic_odsc_button_loadfolder_input.clicked.connect(
            lambda: self.getFolderPath(self.pyqt5_dynamic_odsc_entry_input_path)
        )

        self.pyqt5_dynamic_odsc_button_loadfolder_output.clicked.connect(
            lambda: self.getFolderPath(self.pyqt5_dynamic_odsc_entry_output_path)
        )

        self.pyqt5_dynamic_odsc_button_loadfile_baseline.clicked.connect(
            lambda: self.getEdgesFilePath(self.pyqt5_dynamic_odsc_entry_baseline_path)
        )

        self.qtvar_convertImages_convertTabs.currentChanged.connect(self.tab_change)

        float_validator = QDoubleValidator(0, 100, 2)
        self.pyqt5_dynamic_odsc_entry_min_radius.setValidator(float_validator)
        self.pyqt5_dynamic_odsc_entry_max_radius.setValidator(float_validator)
        self.pyqt5_dynamic_odsc_entry_particle_distance.setValidator(float_validator)
        self.pyqt5_dynamic_odsc_entry_scale_factor.setValidator(float_validator)
        int_validator = QIntValidator(0, 999)
        self.pyqt5_dynamic_odsc_entry_edge_value.setValidator(int_validator)
        self.pyqt5_dynamic_odsc_entry_output_acum_threshold.setValidator(int_validator)

        self.window = window
        self.data = data
        self.success = bool

        self.convert_opendep_single = ConversionOpenDEPSC()
        #self.bkg_convert_opendep_single = ConversionOpenDEPSC()
        self.refresh_opendep_single_ui()

    def tab_change(self):
        if self.qtvar_convertImages_convertTabs.currentIndex() == 0:
            self.qtvar_convertImages_multiSampleCheckbox.setEnabled(True)
            self.qtvar_convertImages_convertButton.setEnabled(True)
        elif self.qtvar_convertImages_convertTabs.currentIndex() == 1:
            self.qtvar_convertImages_multiSampleCheckbox.setCheckState(False)
            self.qtvar_convertImages_multiSampleCheckbox.setEnabled(False)
            self.qtvar_convertImages_convertButton.setEnabled(True)
        else:
            self.qtvar_convertImages_multiSampleCheckbox.setEnabled(False)
            self.qtvar_convertImages_convertButton.setEnabled(False)

    def getFolderPath(self, entry):
        folder = QFileDialog.getExistingDirectory(self, "Select a folder")
        entry.setText(folder)

    def getEdgesFilePath(self, entry):
        file, check = QFileDialog.getOpenFileName(
            None, "Open file", "", "Image files (*.png *.jpg *.jpeg *.tif *.tiff')"
        )
        if check:
            entry.setText(file)

    def OPEN(self):
        self.qtvar_convertImages_statusLabel.setText("...")
        self.show()

    def test_edge_detection(self):
        #try:
        print("Checkpoint 0")
        convert = Conversion()
        print("Checkpoint 1")
        (
            edges_position,
            edges_no,
            average_average_spacing,
            stdev_spaceing,
            electrode_positions,
            electrode_gaps_positions,
        ) = convert.detect_edges(
            image_file=self.qtvar_convertImages_inputEdgesFile.text(),
            points_to_remove=self.qtvar_convertImages_pointstoremove.value(),
            min_edge_spacing=self.qtvar_convertImages_minedgespacing.value(),
            no_pixels_shift=self.qtvar_convertImages_pixelstoshift.value(),
            edge_orientation=self.qtvar_convertImages_orientation.currentText(),
            polynomial_deg=self.qtvar_convertImages_polydegree.value(),
        )
        print("Checkpoint 2")
        self.qtvar_convertImages_noEdgesLabel.setText(f"{edges_no}\nedges\ndetected")
        self.qtvar_convertImages_avgSpacingEdge.setText(
            f"{average_average_spacing} \n+/-\n {stdev_spaceing}\nedge\nspacing"
        )
        print("Checkpoint 3")
        self.GraphWidget_convert_edges.refresh_UI(
            edges_position=edges_position,
            image_path=self.qtvar_convertImages_inputEdgesFile.text(),
            points_to_remove=self.qtvar_convertImages_pointstoremove.value(),
            electrodes_positions=electrode_positions,
        )
        print("Checkpoint 4")
        #except:
            #print("[ERROR] [CONVERSION] Test edge detection couldn't compute")
            #self.qtvar_convertImages_statusLabel.setText("Failed")

    def convert(self):
        #  Convert images to data_01 #
        # Step 1: Create a QThread  and worker object
        self.thread = QThread()
        self.worker = ConvertWorker()
        # Step 2: Move worker to the thread
        self.worker.moveToThread(self.thread)
        # Step 3: Connect signals and slots
        self.thread.started.connect(
            lambda: self.worker.convertProcess(
                convertUI=self, window=self.window, data=self.data
            )
        )
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        # Step 4: Start the thread
        self.thread.start()

        self.qtvar_convertImages_convertButton.setEnabled(False)
        self.qtvar_convertImages_closeButton.setEnabled(False)
        self.qtvar_convertImages_statusLabel.setText("Computing...")

        self.thread.finished.connect(
            lambda: self.qtvar_convertImages_convertButton.setEnabled(True)
        )
        self.thread.finished.connect(
            lambda: self.qtvar_convertImages_closeButton.setEnabled(True)
        )

        if self.success:
            self.thread.finished.connect(
                lambda: self.qtvar_convertImages_statusLabel.setText("Finished")
            )
        else:
            self.thread.finished.connect(
                lambda: self.qtvar_convertImages_statusLabel.setText("Failed")
            )

    def refresh_opendep_single_ui(self):
        self.convert_opendep_single.parm1 = int(self.pyqt5_dynamic_odsc_entry_edge_value.text())
        self.convert_opendep_single.parm2 = int(self.pyqt5_dynamic_odsc_entry_output_acum_threshold.text())
        self.convert_opendep_single.conversion_factor = float(self.pyqt5_dynamic_odsc_entry_scale_factor.text())
        self.convert_opendep_single.min_radius = int(self.convert_opendep_single.conversion_factor *
                                                     float(self.pyqt5_dynamic_odsc_entry_min_radius.text()))
        self.convert_opendep_single.max_radius = int(self.convert_opendep_single.conversion_factor *
                                                     float(self.pyqt5_dynamic_odsc_entry_max_radius.text()))
        self.convert_opendep_single.cells_distance = int(self.convert_opendep_single.conversion_factor *
                                                         float(self.pyqt5_dynamic_odsc_entry_particle_distance.text()))
        self.convert_opendep_single.y_crop = int(self.pyqt5_dynamic_odsc_entry_vertical_crop.text())
        self.convert_opendep_single.x_crop = int(self.pyqt5_dynamic_odsc_entry_horizontal_crop.text())
        self.convert_opendep_single.cell_index = int(self.pyqt5_dynamic_odsc_entry_cell_index.text())
        self.convert_opendep_single.movement_direction = self.pyqt5_dynamic_odsc_combo_movement_direction.currentText()

    def detect_cells(self):
        self.refresh_opendep_single_ui()
        baseline_path = self.pyqt5_dynamic_odsc_entry_baseline_path.text()

        status, self.convert_opendep_single.cells_info = self.convert_opendep_single.detect_cells(
            image_path=baseline_path)

        if status:
            marked_image = self.convert_opendep_single.mark_cells_on_image(
                image_path=self.pyqt5_dynamic_odsc_entry_baseline_path.text(),
                cell_info=self.convert_opendep_single.cells_info)

            self.MPWidgetConvertDetectCells.refresh_UI(
                image=marked_image
            )

        print(self.convert_opendep_single.cells_info)
        cells_info = self.convert_opendep_single.cells_info
        size_list = []
        for i in self.convert_opendep_single.cells_info:
            size_list.append(cells_info[i][2])
        size_avg = str(round(np.average(size_list) / self.convert_opendep_single.conversion_factor, 2))
        size_std = str(round(np.std(size_list) / self.convert_opendep_single.conversion_factor, 2))

        print(size_avg, size_std)

        self.pyqt5_dynamic_odsc_label_avgsize.setText(size_avg + "\n-/+\n" + size_std)
        #self.pyqt5_dynamic_odsc_label_stdsize.setText(size_std)
