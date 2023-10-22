# ------------------------------------------------------
# ----------------- CONVERSION MODULE ------------------
# ------------------------------------------------------

# External imports #
import os
import time

import cv2
import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal

# Local imports #
from src.camera_control import *

"""
Live Capture workers script:
This file covers all thread functionality to the Live Capture module
This is specific for the long-running functions available in Live Capture module
"""

class LiveCaptureWorker(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(int)

    live_capture_UI = None

    def multi_capture_process(self):
        # Multiple timed image capture method
        # Create the a logarithmic list with all frequencies
        # that will be calculated depending on the input parameters
        points_no = int(self.live_capture_UI.pyqt5_dynamic_odsc_entry_points_no.text())
        min_frequency = (
            float(self.live_capture_UI.pyqt5_dynamic_odsc_entry_min_frequency.text())
            * 1000
            ** self.live_capture_UI.pyqt5_dynamic_odsc_combo_min_frequency.currentIndex()
        )

        max_frequency = (
            float(self.live_capture_UI.pyqt5_dynamic_odsc_entry_max_frequency.text())
            * 1000
            ** self.live_capture_UI.pyqt5_dynamic_odsc_combo_max_frequency.currentIndex()
        )

        frequency_list = np.geomspace(min_frequency, max_frequency, points_no)

        # Capture the baseline image
        self.live_capture_UI.capture('baseline')

        # Start function generator output
        if self.live_capture_UI.pyqt5_dynamic_odsc_checkbox_use_generator.isChecked():
            self.live_capture_UI.generator.start_output()

        # Start to loop through each frequency from the computed list
        for i in range(len(frequency_list)):
            # Set the current_frequency for Function generator
            if self.live_capture_UI.pyqt5_dynamic_odsc_checkbox_use_generator.isChecked():
                self.live_capture_UI.generator.set_frequency(frequency_list[i])

            # Update all UI labels for each capture
            current_frequency = self.frequency_text_format(frequency_list[i])
            if i + 1 < len(frequency_list):
                next_frequency = self.frequency_text_format(frequency_list[i + 1])
            else:
                next_frequency = "N/A"

            self.live_capture_UI.pyqt5_dynamic_odsc_label_current_frequency.setText(
                current_frequency
            )
            self.live_capture_UI.pyqt5_dynamic_odsc_label_next_frequency.setText(
                next_frequency
            )
            self.live_capture_UI.pyqt5_dynamic_odsc_label_current_point.setText(
                str(i + 1)
            )

            # Update all UI labels for each second that passed
            for j in range(
                int(self.live_capture_UI.pyqt5_dynamic_odsc_entry_delay.text())
            ):
                max_point = (
                    int(self.live_capture_UI.pyqt5_dynamic_odsc_entry_delay.text()) - j
                )
                self.live_capture_UI.pyqt5_dynamic_odsc_label_countdown.setText(
                    str(max_point)
                )

                # Verify every 0.2 seconds if the stop / pause flags are up
                for z in range(5):
                    time.sleep(0.2)
                    if self.live_capture_UI.stop_thread == True:
                        break
                    while self.live_capture_UI.pause_thread:
                        time.sleep(0.2)
                if self.live_capture_UI.stop_thread == True:
                    break

            # Capture the image and name it accordingly to the frequency
            if self.live_capture_UI.pyqt5_dynamic_odsc_checkbox_use_generator.isChecked():
                filename = 'OpenDEP_' + str(int(frequency_list[i])) + 'Hz'
            else:
                filename = 'OpenDEP_' + str(self.frequency_int_format(frequency_list[i], 2)) + 'Hz'

            try:
                self.live_capture_UI.capture(filename)
            except:
                print("Data point skipped")

            if self.live_capture_UI.stop_thread:
                break

        # Stop capture
        time.sleep(1)
        self.live_capture_UI.stop_capture()
        self.finished.emit()

    def frequency_text_format(self, value):
        if int(value) < 1000:
            frequency = str(self.frequency_int_format(value, 2)) + " Hz"
        elif int(value) < 1000000:
            frequency = str(self.frequency_int_format(value, 2) / 1000) + " kHz"
        elif int(value) < 1000000000:
            frequency = str(self.frequency_int_format(value, 2) / 1000000) + " MHz"

        return frequency

    def frequency_int_format(self, value, no_digits):
        length = len(str(int(value)))
        new_value = int(round(value/10**(length - no_digits), 0) * 10**(length - no_digits))

        return new_value
