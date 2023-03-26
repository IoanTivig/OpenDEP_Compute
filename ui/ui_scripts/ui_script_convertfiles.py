# ------------------------------------------------------
# ----------------- CONVERSION MODULE ------------------
# ------------------------------------------------------

# External imports #
from PyQt5.QtCore import QThread
from PyQt5.QtWidgets import QDialog, QFileDialog
from PyQt5.uic import loadUi
from PyQt5 import QtGui

# Local imports #
from src.conversion import *
from src.threads.workers_convert import ConvertWorker


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
        self.setWindowIcon(QtGui.QIcon("icon.png"))

        self.qtvar_convertImages_closeButton.clicked.connect(self.close)
        self.qtvar_convertImages_convertButton.clicked.connect(self.convert)
        self.qtvar_convertImages_testButton.clicked.connect(self.test_edge_detection)

        self.qtvar_convertImages_inputFolder.setText(os.path.expanduser("~/Desktop"))
        self.qtvar_convertImages_inputEdgesFile.setText(os.path.expanduser("~/Desktop"))
        self.qtvar_convertImages_filename.setText("Centralization")

        self.qtvar_convertImages_inputFolderButton.clicked.connect(
            lambda: self.getFolderPath(self.qtvar_convertImages_inputFolder)
        )
        self.qtvar_convertImages_inputEdgesButton.clicked.connect(
            lambda: self.getEdgesFilePath(self.qtvar_convertImages_inputEdgesFile)
        )

        self.window = window
        self.data = data
        self.success = bool

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
        try:
            convert = Conversion()
            (
                edges_position,
                edges_no,
                average_average_spacing,
                stdev_spaceing,
            ) = convert.detect_edges(
                image_file=self.qtvar_convertImages_inputEdgesFile.text(),
                points_to_remove=self.qtvar_convertImages_pointstoremove.value(),
                min_edge_spacing=self.qtvar_convertImages_minedgespacing.value(),
                no_pixels_shift=self.qtvar_convertImages_pixelstoshift.value(),
                edge_orientation=self.qtvar_convertImages_orientation.currentText(),
                polynomial_deg=self.qtvar_convertImages_polydegree.value(),
            )

            self.qtvar_convertImages_noEdgesLabel.setText(f"{edges_no} edges\ndetected")
            self.qtvar_convertImages_avgSpacingEdge.setText(
                f"{average_average_spacing} +/- {stdev_spaceing}\nedge spacing"
            )

            self.GraphWidget_convert_edges.refresh_UI(
                edges_position=edges_position,
                image_path=self.qtvar_convertImages_inputEdgesFile.text(),
                points_to_remove=self.qtvar_convertImages_pointstoremove.value(),
            )
        except:
            print("[ERROR] [CONVERSION] Test edge detection couldn't compute")
            self.qtvar_convertImages_statusLabel.setText("Failed")

    def convert(self):
        #  Convert images to data #
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
            