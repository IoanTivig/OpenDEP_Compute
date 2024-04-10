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
                            grayness_over_brightness=convertUI.qtvar_convertImages_radio_population_brightfieldmc.isChecked(),
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
                    grayness_over_brightness=convertUI.qtvar_convertImages_radio_population_brightfieldmc.isChecked(),
                    edge_width=convertUI.qtvar_convertImages_pixelsperedge.value(),
                    poly_deg=convertUI.qtvar_convertImages_polydegree.value(),
                )

        elif convertUI.qtvar_convertImages_convertTabs.currentIndex() == 1:
            convertUI.refresh_opendep_single_ui()
            baseline_path = convertUI.pyqt5_dynamic_odsc_entry_baseline_path.text()
            input_path = convertUI.pyqt5_dynamic_odsc_entry_input_path.text()
            output_path = convertUI.pyqt5_dynamic_odsc_entry_output_path.text()
            cell_index = int(convertUI.pyqt5_dynamic_odsc_entry_cell_index.text())

            cropped_image, frequencies, cm_factors, cell_radius = convertUI.convert_opendep_single.convert_single_cell(
                input_path=input_path,
                output_path=output_path,
                baseline_path=baseline_path,
                cell_index=cell_index)

            convertUI.MPWidgetConvertDetectCells.refresh_UI(
                image=cropped_image
            )

            data.frequency_list = frequencies
            data.CMfactor_list = cm_factors
            data.CMfactor_errors_list = []
            window.fitting_sish_particle_radius_value_entry.setText(str(cell_radius))

            window.loadData()

        self.finished.emit()
