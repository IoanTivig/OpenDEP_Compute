# ------------------------------------------------------
# ---------------- LIVE CAPTURE MODULE -----------------
# ------------------------------------------------------
import os
import time
import numpy as np

from PyQt5.QtCore import QThread
from PyQt5.QtWidgets import QDialog, QFileDialog
from PyQt5.uic import loadUi
from PyQt5 import QtGui

# Local imports #
import src.camera_control as dccp
from src.threads.workers_livecapture import *

"""
LiveCapture UI script:
This file covers all UI related functionality to the live Capture module
All buttons and widgets are connected and run either directly scripts found
in src/conversion module for short running scripts or in a thread (in this case
the thread setup can be found in src/threads/workers_livecapture.py)
"""


class LiveCaptureUI(QDialog):
    def __init__(self):
        QDialog.__init__(self)
        loadUi("ui/live_capture.ui", self)
        self.setWindowTitle("Live Image Capture")
        self.setWindowIcon(QtGui.QIcon("ui/resources/logos/opendep_logo_1.png"))

        self.camera = dccp.Camera()
        self.camera_details_list = self.camera.listCamerasDetails()
        self.single_capture_index = 0
        self.stop_thread = False
        self.pause_thread = False

        self.pyqt5_dynamic_odsc_button_start_capture.clicked.connect(self.start_capture)
        self.pyqt5_dynamic_odsc_button_stop_capture.clicked.connect(self.stop_capture)
        self.pyqt5_dynamic_odsc_button_pause_capture.clicked.connect(self.pause_capture)
        self.pyqt5_dynamic_odsc_button_resume_capture.clicked.connect(self.resume_capture)

        self.pyqt5_dynamic_odsc_button_loadfolder_output.clicked.connect(
            lambda: self.getFolderPath(self.pyqt5_dynamic_odsc_entry_output_path)
        )
        self.pyqt5_dynamic_odsc_button_loadfile_correction.clicked.connect(
            lambda: self.getFilePath(self.pyqt5_dynamic_odsc_entry_correction_path)
        )

        self.pyqt5_dynamic_odsc_button_reload_cameras.clicked.connect(
            self.get_cameras
        )
        self.pyqt5_dynamic_odsc_combo_camera.currentIndexChanged.connect(self.select_camera)
        self.pyqt5_dynamic_odsc_button_single_capture.clicked.connect(
            lambda: self.single_capture('single_capture_' + str(self.single_capture_index))
        )

    def OPEN(self):
        self.get_cameras()
        self.show()

    def getFolderPath(self, entry):
        folder = QFileDialog.getExistingDirectory(self, "Select output folder")
        entry.setText(folder)

    def getFilePath(self, entry):
        file, check = QFileDialog.getOpenFileName(
            None, "Open file", "", "Image files (*.png *.jpg *.jpeg *.tif *.tiff')"
        )
        if check:
            entry.setText(file)

    def get_cameras(self):
        name_list = []
        self.camera_details_list = self.camera.listCamerasDetails()
        self.pyqt5_dynamic_odsc_combo_camera.clear()
        for i in self.camera_details_list:
            name_list.append(i[1])

        if 'error' not in name_list[0]:
            for i in name_list:
                self.pyqt5_dynamic_odsc_combo_camera.addItem(i[1:])
        elif 'error' in name_list[0]:
            self.pyqt5_dynamic_odsc_combo_camera.addItem("No available camera")

        self.select_camera()

    def select_camera(self):
        index = self.pyqt5_dynamic_odsc_combo_camera.currentIndex()
        self.camera.setCamera(self.camera_details_list[index][0])

    def single_capture(self, file_name):
        path = self.pyqt5_dynamic_odsc_entry_output_path.text()
        self.camera.setTransfer("Save_to_PC_only")
        self.camera.capture(os.path.join(path, file_name))
        self.single_capture_index = self.single_capture_index + 1

    def start_capture(self):
        # Live Timed Multi Capture#
        # Step 1: Set some parameters
        self.stop_thread = False
        self.pause_thread = False
        self.pyqt5_dynamic_odsc_button_start_capture.setDisabled(True)
        self.pyqt5_dynamic_odsc_button_stop_capture.setDisabled(False)
        # Step 2: Create a QThread  and worker object
        self.thread = QThread()
        self.worker = LiveCaptureWorker()

        # Setp 3: Set arguments
        self.worker.live_capture_UI = self

        # Step 4: Move worker to the thread
        self.worker.moveToThread(self.thread)
        # Step 5: Connect signals and slots
        self.thread.started.connect(self.worker.multi_capture_process)
        # Step 6: Start the thread
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def stop_capture(self):
        self.pyqt5_dynamic_odsc_button_start_capture.setDisabled(False)
        self.pyqt5_dynamic_odsc_button_stop_capture.setDisabled(True)
        self.pyqt5_dynamic_odsc_label_current_frequency.setText('0 Hz')
        self.pyqt5_dynamic_odsc_label_next_frequency.setText('0 Hz')
        self.pyqt5_dynamic_odsc_label_current_point.setText('0')
        self.pyqt5_dynamic_odsc_label_countdown.setText('0')
        self.pause_thread = False
        self.stop_thread = True

    def pause_capture(self):
        self.pause_thread = True

    def resume_capture(self):
        self.pause_thread = False
