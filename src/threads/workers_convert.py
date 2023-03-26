# ------------------------------------------------------
# ----------------- CONVERSION MODULE ------------------
# ------------------------------------------------------

# External imports #
import os
from PyQt5.QtCore import QObject, pyqtSignal

# Local imports #
from src.conversion import Conversion

"""
Conversion workers script:
This file covers all thread functionality to the convert module
This is specific for the long-running functions available in conversion module
"""


class ConvertWorker(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(int)

    def convertProcess(self, convertUI, window, data):
        """Long-running task."""
        if convertUI.qtvar_convertImages_convertTabs.currentIndex() == 0:
            if convertUI.qtvar_convertImages_multiSampleCheckbox.isChecked():
                for folder in os.listdir(
                    convertUI.qtvar_convertImages_inputFolder.text()
                ):
                    folder_full = os.path.join(
                        convertUI.qtvar_convertImages_inputFolder.text(), folder
                    )
                    print(folder_full)
                    if os.path.isdir(folder_full):
                        print("yay")
                        convert = Conversion()
                        convert.ConvertOpenDEPPopulation(
                            convertUI=convertUI,
                            mainUI=window,
                            data=data,
                            folder=folder_full,
                            centrfile=convertUI.qtvar_convertImages_filename.text(),
                            points_to_remove=convertUI.qtvar_convertImages_pointstoremove.value(),
                            min_edge_spacing=convertUI.qtvar_convertImages_minedgespacing.value(),
                            no_pixels_shift=convertUI.qtvar_convertImages_pixelstoshift.value(),
                            edge_orientation=convertUI.qtvar_convertImages_orientation.currentText(),
                            edge_width=convertUI.qtvar_convertImages_pixelsperedge.value(),
                            poly_deg=convertUI.qtvar_convertImages_polydegree.value(),
                        )

            else:
                convert = Conversion()
                convert.ConvertOpenDEPPopulation(
                    convertUI=convertUI,
                    mainUI=window,
                    data=data,
                    folder=convertUI.qtvar_convertImages_inputFolder.text(),
                    centrfile=convertUI.qtvar_convertImages_filename.text(),
                    points_to_remove=convertUI.qtvar_convertImages_pointstoremove.value(),
                    min_edge_spacing=convertUI.qtvar_convertImages_minedgespacing.value(),
                    no_pixels_shift=convertUI.qtvar_convertImages_pixelstoshift.value(),
                    edge_orientation=convertUI.qtvar_convertImages_orientation.currentText(),
                    edge_width=convertUI.qtvar_convertImages_pixelsperedge.value(),
                    poly_deg=convertUI.qtvar_convertImages_polydegree.value(),
                )
        self.finished.emit()