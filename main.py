'''
OpenDEP
    Copyright (C) 2022  Ioan Cristian Tivig

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.

    You can contact the developer/owner of OpenDEP at "ioan.tivig@gmail.com".
'''

### START IMPORTS ###
### Local imports ###
import src.sphcm as sphcm
import src.sscm as sscm
import src.conversion as conversion
import src.functions as functions
import src.datamanagement as datamanagement

from src.sphcm import *
from src.sscm import *
from src.conversion import *
from src.functions import *
from src.datamanagement import *

from ui.ui_scripts.ui_script_renamefiles import *
from ui.ui_scripts.ui_script_convertfiles import *

### PyQt5 imports ###
from PyQt5 import QtGui
from PyQt5 import QtCore
from PyQt5.QtWidgets import *
from PyQt5.uic import loadUi
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QObject, QThread, pyqtSignal
### END IMPORTS ###


### Parameters UI setting ###
class PropertiesUI(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        loadUi("ui/parameters.ui", self)
        self.setWindowTitle("Parameter settings")
        self.setWindowIcon(QtGui.QIcon("icon.png"))

        self.closeHopaParameters.clicked.connect(self.close)
        self.saveHopaParameters.clicked.connect(self.saveHopaParametersButton)
        self.loadHopaParameters.clicked.connect(self.loadHopaParametersButton)

        self.closeSishParameters.clicked.connect(self.close)
        self.saveSishParameters.clicked.connect(self.saveSishParametersButton)
        self.loadSishParameters.clicked.connect(self.loadSishParametersButton)

        self.fitting_sish_electricalmodel_ParametersUI_toggle.toggled.connect(lambda:window.fitting_sish_electricalmodel_MainUI_toggle.setChecked(True))
        self.fitting_sish_classicalmodel_ParametersUI_toggle.toggled.connect(lambda:window.fitting_sish_classicalmodel_MainUI_toggle.setChecked(True))

        self.fitting_sish_membrane_cond_min_entry.editingFinished.connect(lambda:sish_params.changeClassicalToElectrical(self.fitting_sish_membrane_cond_min_entry, self.fitting_sish_membrane_conductance_min_entry, 'conductance', window))
        self.fitting_sish_membrane_cond_max_entry.editingFinished.connect(lambda:sish_params.changeClassicalToElectrical(self.fitting_sish_membrane_cond_max_entry, self.fitting_sish_membrane_conductance_max_entry, 'conductance', window))
        self.fitting_sish_membrane_perm_min_entry.editingFinished.connect(lambda:sish_params.changeClassicalToElectrical(self.fitting_sish_membrane_perm_min_entry, self.fitting_sish_membrane_capacitance_min_entry, 'capacitance', window))
        self.fitting_sish_membrane_perm_max_entry.editingFinished.connect(lambda:sish_params.changeClassicalToElectrical(self.fitting_sish_membrane_perm_max_entry, self.fitting_sish_membrane_capacitance_max_entry, 'capacitance', window))

        self.fitting_sish_membrane_conductance_min_entry.editingFinished.connect(lambda:sish_params.changeElectricalToClassical(self.fitting_sish_membrane_conductance_min_entry, self.fitting_sish_membrane_cond_min_entry, 'conductivity', window))
        self.fitting_sish_membrane_conductance_max_entry.editingFinished.connect(lambda:sish_params.changeElectricalToClassical(self.fitting_sish_membrane_conductance_max_entry, self.fitting_sish_membrane_cond_max_entry, 'conductivity', window))
        self.fitting_sish_membrane_capacitance_min_entry.editingFinished.connect(lambda:sish_params.changeElectricalToClassical(self.fitting_sish_membrane_capacitance_min_entry, self.fitting_sish_membrane_perm_min_entry, 'permitivity', window))
        self.fitting_sish_membrane_capacitance_max_entry.editingFinished.connect(lambda:sish_params.changeElectricalToClassical(self.fitting_sish_membrane_capacitance_max_entry, self.fitting_sish_membrane_perm_max_entry, 'permitivity', window))


    def OPEN(self):
        self.show()


    def saveHopaParametersButton(self):
        try:
            hopa_params.refreshFromGUIFittingParameters(paramsUI, window, 'hopa')
            file = QFileDialog.getSaveFileName(self, filter="Homogenous particle save file (*.hopa)")[0]
            hopa_params.saveParameters(file)
        except:
            print('Folder not selected')


    def loadHopaParametersButton(self):
        try:
            file = QFileDialog.getOpenFileName(self, filter="Homogenous particle save file (*.hopa)")[0]
            hopa_params.loadParameters(file)
            hopa_params.changeGUIFittingParameters(paramsUI, window, 'hopa')
        except:
            print('File not selected')


    def saveSishParametersButton(self):
        try:
            sish_params.refreshFromGUIFittingParameters(paramsUI, window, 'sish')
            file = QFileDialog.getSaveFileName(self, filter="Single shell save file (*.sish)")[0]
            sish_params.saveParameters(file)
        except:
            print('Folder not selected')


    def loadSishParametersButton(self):
        try:
            file = QFileDialog.getOpenFileName(self, filter="Single shell save file (*.sish)")[0]
            sish_params.loadParameters(file)
            sish_params.changeGUIFittingParameters(paramsUI, window, 'sish')
        except:
            print('File not selected')


### Auto Process Dialog setting ###
class AutoWorker(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(int)

    def autoProcess(self):
        """Long-running task."""

        autoProcessLoadandFit(autoProcessUI, datapointsUI, paramsUI, window)
        self.finished.emit()


class AutoProcessUI(QDialog):
    def __init__(self):
        QDialog.__init__(self)
        loadUi("ui/auto_process.ui", self)
        self.setWindowTitle("Auto process settings")
        self.setWindowIcon(QtGui.QIcon("icon.png"))

        self.closeAutoProcess.clicked.connect(self.close)

        self.fromFolderButton.clicked.connect(lambda:self.getPathway(self.fromFolderEntry))
        self.toFolderButton.clicked.connect(lambda: self.getPathway(self.toFolderEntry))
        self.autoProcessStartButton.clicked.connect(self.autoProcessButton)

        self.outliersThresholdSlider.valueChanged.connect(self.outliersThresholdChanging)
        self.rsquareThresholdSlider.valueChanged.connect(self.rsquareThresholdChanging)

    def outliersThresholdChanging(self):
        thresholdValue = float(self.outliersThresholdSlider.value())/10.0
        self.outliersThresholdEntry.setText(str(thresholdValue))

    def rsquareThresholdChanging(self):
        thresholdValue = float(self.rsquareThresholdSlider.value()) / 100.0
        self.rsquareThresholdEntry.setText(str(thresholdValue))

    def OPEN(self):
        desktop = os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop')
        self.fromFolderEntry.setText(desktop)
        self.toFolderEntry.setText(desktop)
        self.statusLabel.setText('...')
        self.show()

    def getPathway(self, entry):
        folder = QFileDialog.getExistingDirectory(self, 'Select a folder')
        entry.setText(folder)

    def autoProcessButton(self):
        ##  Load, fit and save processed data_01 ##
        # Step 1: Create a QThread  and worker object
        self.thread = QThread()
        self.worker = AutoWorker()
        # Step 2: Move worker to the thread
        self.worker.moveToThread(self.thread)
        # Step 3: Connect signals and slots
        self.thread.started.connect(self.worker.autoProcess)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        # Step 4: Start the thread
        self.thread.start()


### Data Points Dialog setting ###
class DataPointsUI(QDialog):
    def __init__(self):
        QDialog.__init__(self)
        loadUi("ui/data_points.ui", self)
        self.setWindowTitle("Data points settings")
        self.setWindowIcon(QtGui.QIcon("icon.png"))

        self.data_points_table.itemDoubleClicked.connect(self.changeStatus)
        self.data_points_table.setEditTriggers(self.data_points_table.NoEditTriggers)
        self.closeDataPoints.clicked.connect(self.closeWindow)
        self.enableAllDataPoints.clicked.connect(self.enableAllPoints)
        self.detectOutliers.clicked.connect(self.detectOutliersWow)
        self.disableOutliersButton.clicked.connect(self.disableOutliers)
        self.thresholdSlider.valueChanged.connect(self.thresholdChanging)

    def thresholdChanging(self):
        thresholdValue = float(self.thresholdSlider.value())/10.0
        self.thresholdEntry.setText(str(thresholdValue))

    def OPEN(self):
        try:
            self.data_points_table.setRowCount(len(data.frequency_list))
            for i in data.frequency_list:
                j = data.frequency_list.index(i)
                self.data_points_table.setItem(j, 0,QTableWidgetItem(str(data.frequency_list[j])))
                if len(data.CMfactor_list) > 2:
                    self.data_points_table.setItem(j, 1, QTableWidgetItem(str(data.CMfactor_list[j])))
                if len(data.DEPforce_list) > 2:
                    self.data_points_table.setItem(j, 2, QTableWidgetItem(str(data.DEPforce_list[j])))
                self.data_points_table.setItem(j, 1, QTableWidgetItem(str(data.CMfactor_list[j])))

                try:
                    self.data_points_table.setItem(j, 4, QTableWidgetItem(data.dataStatus_list[j]))
                except:
                    self.data_points_table.setItem(j, 4, QTableWidgetItem("Enabled"))
                try:
                    self.data_points_table.setItem(j, 3, QTableWidgetItem(data.dataValidation_list[j]))
                except:
                    self.data_points_table.setItem(j, 3, QTableWidgetItem("Normal"))

                self.data_points_table.resizeColumnsToContents()

            self.show()
        except:
            print("[ERROR] [Main] [DataPointsUI] OPEN method could not run")


    def changeStatus(self):
        try:
            row = self.data_points_table.currentRow()
            if self.data_points_table.item(row, 4).text() == 'Enabled':
                self.data_points_table.setItem(row, 4, QTableWidgetItem('Disabled'))
            elif self.data_points_table.item(row, 4).text() == 'Disabled':
                self.data_points_table.setItem(row, 4, QTableWidgetItem('Enabled'))
        except:
            print("[ERROR] [Main] [DataPointsUI] changeStatus method could not run")


    def enableAllPoints(self):
        for i in data.frequency_list:
            j = data.frequency_list.index(i)
            self.data_points_table.setItem(j, 4, QTableWidgetItem("Enabled"))


    def detectOutliersWow(self):
        fitOutliers = MyFittings()
        print("Hello")
        instancedValidation_list = fitOutliers.returnOutliers(data.frequency_list, data.CMfactor_list, data.DEPforce_list, float(self.thresholdEntry.text()))
        print(self.thresholdEntry.text())
        print(instancedValidation_list)
        for i in range(len(instancedValidation_list)):
            self.data_points_table.setItem(i, 3, QTableWidgetItem(instancedValidation_list[i]))


    def disableOutliers(self):
        for i in range(len(data.frequency_list)):
            if self.data_points_table.item(i, 3).text() == 'Outlier':
                self.data_points_table.setItem(i, 4, QTableWidgetItem("Disabled"))


    def closeWindow(self):
        data.dataStatus_list = []
        data.dataValidation_list = []

        for i in data.frequency_list:
            j = data.frequency_list.index(i)
            data.dataStatus_list.append(self.data_points_table.item(j, 4).text())
            data.dataValidation_list.append(self.data_points_table.item(j, 3).text())

        #print(data_01.dataStatus_list, data_01.dataValidation_list)
        #print(data_01.frequency_list, data_01.CMfactor_list)

        window.loadData()
        self.close()


### Main UI setting ###
class MainUI(QMainWindow):

#Initiation of GUI
    def __init__(self):
        QMainWindow.__init__(self)
        loadUi("ui/main.ui", self)
        self.setWindowTitle("OpenDEP")
        self.setWindowIcon(QtGui.QIcon("icon.png"))

        self.selectWhatToFit(self.fitting_CMfactor_selector_button, self.fitting_DEPforcer_selector_button, 'CMfactor')
        self.method = 'powell'

# Activating buttons #
    # Generate Model Buttons #
        self.ModelSphericalGenerateButton.clicked.connect(self.GenerateSphModel)
        self.ModelSphericalAddplotButton.clicked.connect(self.AddSphModel)

        self.ModelSingleshellGenerateButton.clicked.connect(self.GenerateSSModel)
        self.ModelSingleshellAddplotButton.clicked.connect(self.AddSSModel)

        self.model_hopa_exit_button.clicked.connect(self.exitButton)
        self.model_sish_exit_button.clicked.connect(self.exitButton)

        self.model_sish_membrane_cond_value_entry.editingFinished.connect(lambda:sish_params.changeClassicalToElectrical(self.model_sish_membrane_cond_value_entry, self.model_sish_membrane_conductance_value_entry, 'conductance', window))
        self.model_sish_membrane_perm_value_entry.editingFinished.connect(lambda:sish_params.changeClassicalToElectrical(self.model_sish_membrane_perm_value_entry, self.model_sish_membrane_capacitance_value_entry, 'capacitance', window))

        self.model_sish_membrane_conductance_value_entry.editingFinished.connect(lambda:sish_params.changeElectricalToClassical(self.model_sish_membrane_conductance_value_entry, self.model_sish_membrane_cond_value_entry, 'conductivity', window))
        self.model_sish_membrane_capacitance_value_entry.editingFinished.connect(lambda:sish_params.changeElectricalToClassical(self.model_sish_membrane_capacitance_value_entry, self.model_sish_membrane_perm_value_entry, 'permitivity', window))

        self.saveexcel.clicked.connect(self.saveExcel)

    # Fitting Buttons #
        self.fitting_hopa_exit_button.clicked.connect(self.exitButton)
        self.menu_quit.triggered.connect(self.exitButton)
        self.fitting_hopa_loaddata_button.clicked.connect(self.loadDataButton)
        self.fitting_hopa_fitdata_button.clicked.connect(self.fitHopa)
        self.fitting_hopa_savedata_button.clicked.connect(self.saveDataButton)

        self.fitting_sish_exit_button.clicked.connect(self.exitButton)
        self.fitting_sish_loaddata_button.clicked.connect(self.loadDataButton)
        self.fitting_sish_fitdata_button.clicked.connect(self.fitSish)
        self.fitting_sish_savedata_button.clicked.connect(self.saveDataButton)

        self.fitting_sish_electricalmodel_MainUI_toggle.clicked.connect(lambda:paramsUI.fitting_sish_electricalmodel_ParametersUI_toggle.setChecked(True))
        self.fitting_sish_electricalmodel_MainUI_toggle.toggled.connect(lambda:window.fitting_sish_membrane_thickness_vary.setCurrentText('Fixed'))
        self.fitting_sish_classicalmodel_MainUI_toggle.clicked.connect(lambda:paramsUI.fitting_sish_classicalmodel_ParametersUI_toggle.setChecked(True))

        self.fitting_sish_membrane_cond_value_entry.editingFinished.connect(lambda:sish_params.changeClassicalToElectrical(self.fitting_sish_membrane_cond_value_entry, self.fitting_sish_membrane_conductance_value_entry, 'conductance', window))
        self.fitting_sish_membrane_perm_value_entry.editingFinished.connect(lambda:sish_params.changeClassicalToElectrical(self.fitting_sish_membrane_perm_value_entry, self.fitting_sish_membrane_capacitance_value_entry, 'capacitance', window))

        self.fitting_sish_membrane_conductance_value_entry.editingFinished.connect(lambda:sish_params.changeElectricalToClassical(self.fitting_sish_membrane_conductance_value_entry, self.fitting_sish_membrane_cond_value_entry, 'conductivity', window))
        self.fitting_sish_membrane_capacitance_value_entry.editingFinished.connect(lambda:sish_params.changeElectricalToClassical(self.fitting_sish_membrane_capacitance_value_entry, self.fitting_sish_membrane_perm_value_entry, 'permitivity', window))

        self.fitting_CMfactor_selector_button.clicked.connect(lambda:self.selectWhatToFit( self.fitting_CMfactor_selector_button,self.fitting_DEPforcer_selector_button, 'CMfactor'))
        self.fitting_DEPforcer_selector_button.clicked.connect(lambda:self.selectWhatToFit( self.fitting_DEPforcer_selector_button,self.fitting_CMfactor_selector_button, 'DEPforce'))

        self.fitting_method_selector_comboBox.currentTextChanged.connect(self.updatingFittingMethod)
        self.fitting_gen_fieldgrad_comboBox.currentTextChanged.connect(self.updatingElectricField)

        self.menu_convert3DEP.triggered.connect(self.convert3DEPButton)
        self.menu_convert3DEPfolder.triggered.connect(self.convertFolder3DEPButton)

    def updatingElectricField(self):
        if self.fitting_gen_fieldgrad_comboBox.currentText() == 'Specified':
            self.fitting_gen_fieldgrad_value_entry.setEnabled(True)

            #set gradiant to fixed
            hopa_params.changeParameter('fitting_gen_fieldgrad', 'vary', False)
            sish_params.changeParameter('fitting_gen_fieldgrad', 'vary', False)

            self.fitting_CMfactor_selector_button.setEnabled(True)
            self.fitting_DEPforcer_selector_button.setEnabled(True)


        elif self.fitting_gen_fieldgrad_comboBox.currentText() == 'Unspecified':
            self.fitting_gen_fieldgrad_value_entry.setDisabled(True)
            self.fitting_gen_fieldgrad_value_entry.setText('1.0')

            #set gradiant to vary
            hopa_params.changeParameter('fitting_gen_fieldgrad', 'vary', True)
            sish_params.changeParameter('fitting_gen_fieldgrad', 'vary', True)

            self.selectWhatToFit(self.fitting_CMfactor_selector_button, self.fitting_DEPforcer_selector_button, 'CMfactor')
            self.fitting_CMfactor_selector_button.setDisabled(True)
            self.fitting_DEPforcer_selector_button.setDisabled(True)

    def updatingFittingMethod(self):
        if self.fitting_method_selector_comboBox.currentText() == "Powell's conjugate direction":
            self.method = 'powell'
            print(self.method)
        elif self.fitting_method_selector_comboBox.currentText() == "Levenberg-Marquardt":
            self.method = 'leastsq'
            print(self.method)
        elif self.fitting_method_selector_comboBox.currentText() == "Trust Region Reflective":
            self.method = 'least_squares'
            print(self.method)

    def selectWhatToFit(self, what_to_fit, what_to_not_fit, what_to_fit_string):
        what_to_fit.setStyleSheet('background-color : white;'' border :2px solid')
        what_to_not_fit.setStyleSheet('background-color : lightgrey;'' border :0.5px solid;''border-color: grey')
        self.what_to_fit = what_to_fit_string

# Convert 3DEP to this program type of file #
    def convert3DEPButton(self):
        try:
            file = QFileDialog.getOpenFileName(self, filter="CSV Workbook(*.csv)")[0]
            load3DEP(file, None)
        except:
            print("[ERROR] [Main] [window] Convert3DEPButton method could not run")

    def convertFolder3DEPButton(self):
        try:
            folder = QFileDialog.getExistingDirectory(self, 'Select a folder with all the data_01 that you want to convert')
            load3DEPloop(folder)
        except:
            print("[ERROR] [Main] [window] convertFolder3DEPButton method could not run")

# Exiting the program #
    def exitButton(self):
        hopa_params.refreshFromGUIFittingParameters(paramsUI, window, 'hopa')
        sish_params.refreshFromGUIFittingParameters(paramsUI, window, 'sish')
        hopa_params.saveParameters('saves/default_hopa_parameters')
        sish_params.saveParameters('saves/default_sish_parameters')
        app.exit()

# Loads data_01 from an excel file and plots on a matplotlib graph #
    def loadDataButton(self):

    # Data loading #
        try:
            file = QFileDialog.getOpenFileName(self, filter="Excel Workbook(*.xlsx);; Excel 97-2003 Workbook(*.xls)")[0]
            data.loadExcelData(file)
            self.loadData()
        except:
            print("================= [Warrning] =========================")
            print("[Main] [MainUI] loadDataButton method could not run: No folder selected / No data_01 to load")


    def loadData(self):
    # Data ploting #
        self.MplCMWidget1.canvas.axes.clear()
        if len(data.CMfactor_list) > 1:
            try:
                self.MplCMWidget1.canvas.axes.errorbar(data.removeSelectedPoints(data.frequency_list), data.removeSelectedPoints(data.CMfactor_list), yerr=data.removeSelectedPoints(data.CMfactor_errors_list), fmt='o', ecolor='black', elinewidth=0.5, capsize=1)
            except:
                self.MplCMWidget1.canvas.axes.errorbar(data.removeSelectedPoints(data.frequency_list), data.removeSelectedPoints(data.CMfactor_list), fmt='o', ecolor='black', elinewidth=0.5, capsize=1)

        self.MplCMWidget1.canvas.axes.grid(which='major', axis='both', color='lightgrey', linestyle='--')
        self.MplCMWidget1.canvas.axes.yaxis.set_major_formatter(StrMethodFormatter('{x:,.3f}'))
        self.MplCMWidget1.canvas.axes.set_xlabel('Frequency (Hz)', labelpad=5)
        self.MplCMWidget1.canvas.axes.set_ylabel('CM factor', labelpad=5)
        self.MplCMWidget1.canvas.axes.set_xscale("log")
        self.MplCMWidget1.canvas.axes.tick_params(labelsize='small')

        if self.fitting_zerohline_CMfactor_checkbox.isChecked():
            self.MplCMWidget1.canvas.axes.axhline(0, color='black', linestyle='--', lw=1)

        self.MplCMWidget1.canvas.draw()

        self.MplCMWidget3.canvas.axes.clear()
        if len(data.DEPforce_list) > 1:
            try:
                self.MplCMWidget3.canvas.axes.errorbar(data.removeSelectedPoints(data.frequency_list), data.removeSelectedPoints(data.DEPforce_list), yerr=data.removeSelectedPoints(data.DEPforce_errors_list), fmt='o', ecolor='black', elinewidth=0.5, capsize=1)
            except:
                self.MplCMWidget3.canvas.axes.errorbar(data.removeSelectedPoints(data.frequency_list), data.removeSelectedPoints(data.DEPforce_list), fmt='o', ecolor='black', elinewidth=0.5, capsize=1)

        self.MplCMWidget3.canvas.axes.grid(which='major', axis='both', color='lightgrey', linestyle='--')
        self.MplCMWidget3.canvas.axes.yaxis.set_major_formatter(StrMethodFormatter('{x:,.3f}'))
        self.MplCMWidget3.canvas.axes.set_xlabel('Frequency (Hz)', labelpad=5)
        self.MplCMWidget3.canvas.axes.set_ylabel('DEP force', labelpad=5)
        self.MplCMWidget3.canvas.axes.set_xscale("log")
        self.MplCMWidget3.canvas.axes.tick_params(labelsize='small')

        if self.fitting_zerohline_CMfactor_checkbox.isChecked():
            self.MplCMWidget3.canvas.axes.axhline(0, color='black', linestyle='--', lw=1)

        self.MplCMWidget3.canvas.draw()


# Fits the loded/ploted data_01 with the model selected #
    def fitHopa(self):
        try:
            self.model = 'hopa'
            self.fitDataButton(self.model, hopa_params)
            print('Hopa fit done')
        except:
            print('Fit failed')

    def fitSish(self):
        try:
            self.model = 'sish'
            self.fitDataButton(self.model, sish_params)
        except:
            print('Fit failed')

    def fitDataButton(self, model, params):
    # Parameters refresh #
        params.refreshFromGUIFittingParameters(paramsUI, window, model)

    # Data fiting #
        print(f'Fitting Step 0: {model}')
        self.result = fit.fit(data.removeSelectedPoints(data.frequency_list), data.removeSelectedPoints(data.CMfactor_list), data.removeSelectedPoints(data.DEPforce_list), params.parameters, model=model, what_to_fit=self.what_to_fit, trei_DEP = self.fitting_gen_fieldgrad_comboBox.currentText(), method=self.method)
        print('Fitting Step 1')
        data.fittedFrequency_list, data.fittedCMfactor_list, data.fittedDEPforce_list = fit.returnFittedValues2(self.result, model,self.what_to_fit, 50, data.removeSelectedPoints(data.frequency_list), params)
        print('Fitting Step 2')
        if self.fitting_gen_fieldgrad_comboBox.currentText() == 'Unspecified':
            instanced_list = []
            for i in data.CMfactor_list:
                instanced_list.append(i / float(fit.returnFittedParamtersVar2(self.result, 'fitting_gen_fieldgrad')[0]))

            instanced_errors_list = []
            for j in data.CMfactor_errors_list:
                instanced_errors_list.append(j / float(fit.returnFittedParamtersVar2(self.result, 'fitting_gen_fieldgrad')[0]))

            data.CMfactor_list = instanced_list
            data.CMfactor_errors_list = instanced_errors_list
            self.loadData()


    # Parameters refresh with new fitted values #
        fit.returnFittedParameters(self.result, window, model)
        fit.printFit(self.result)

    # Data Ploting on graph or in Entries#
        self.fitting_CMfactor_Rsquare.setText(str(round(fit.returnFitRsquare(self.result),4)))
        fit.cross_over(data.fittedFrequency_list, data.fittedCMfactor_list, self.fitting_CMfactor_firstCOfreq, self.fitting_CMfactor_secondCOfreq, self.fitting_zerohline_markCO_checkbox, self.MplCMWidget1)

        self.MplCMWidget1.canvas.axes.plot(data.fittedFrequency_list, data.fittedCMfactor_list)
        self.MplCMWidget1.canvas.draw()

    # DEP force plotting #

        self.MplCMWidget3.canvas.axes.plot(data.fittedFrequency_list, data.fittedDEPforce_list)
        self.MplCMWidget3.canvas.draw()

    # Residuals plotting #
        self.MplCMWidget2.canvas.axes.clear()
        self.MplCMWidget2.canvas.axes.grid(which='major', axis='both', color='lightgrey', linestyle='--')
        self.MplCMWidget2.canvas.axes.yaxis.set_major_formatter(StrMethodFormatter('{x:,.3f}'))
        self.MplCMWidget2.canvas.axes.set_ylabel('Residuals', labelpad=5)
        self.MplCMWidget2.canvas.axes.set_xscale("log")
        self.MplCMWidget2.canvas.axes.tick_params(labelsize='small')
        self.MplCMWidget2.canvas.axes.axhline(0, color='black', linestyle='--', lw=1)

        if self.what_to_fit == 'CMfactor':
            residual_error_list = data.removeSelectedPoints(data.CMfactor_errors_list)
        elif self.what_to_fit == 'DEPforce':
            residual_error_list = data.removeSelectedPoints(data.DEPforce_errors_list)

        try:
            self.MplCMWidget2.canvas.axes.errorbar(data.removeSelectedPoints(data.frequency_list), fit.returnFittedResiduals(self.result),yerr=residual_error_list, fmt='o', ecolor='black', elinewidth=0.5, capsize=1)
        except:
            self.MplCMWidget2.canvas.axes.errorbar(data.removeSelectedPoints(data.frequency_list), fit.returnFittedResiduals(self.result), fmt='o', ecolor='black', elinewidth=0.5, capsize=1)

        self.MplCMWidget2.canvas.draw()

    def saveDataButton(self):
        try:
            data.saveExcelData(QFileDialog.getSaveFileName(self, filter="Excel file (*.xlsx)")[0], self.model, window, data, fit)
        except:
            print("================= [Warrning] =========================")
            print("[Main] [MainUI] saveDataButton method could not run: No folder selected / No data_01 to save")


    def saveExcel(self):
        try:
            self.wb.save(filename=QFileDialog.getSaveFileName(self, filter="Excel file (*.xlsx)")[0])
        except:
            print("================= [Warrning] =========================")
            print("[Main] [MainUI] saveExcel method could not run: No data_01 to save / Excel contextmenu closed")


    def GenerateSphModel(self):
        params_list = [float(self.model_gen_fieldgrad_value_entry.text()), float(self.model_hopa_particle_radius_value_entry.text()), float(self.model_hopa_particle_perm_value_entry.text()), float(self.model_hopa_particle_cond_value_entry.text()), float(self.model_gen_buffer_perm_value_entry.text()), float(self.model_gen_buffer_cond_value_entry.text())]

        model_frequency_list = np.logspace(np.log10(frequencyConvertor(self.model_gen_startFrequency_value_entry, self.model_gen_startFrequency_division)), np.log10(frequencyConvertor(self.model_gen_stopFrequency_value_entry, self.model_gen_stopFrequency_division)), num=int(self.model_gen_numberOfPoints_value_entry.text()), base=10)
        model_CMfactor_list = model_hopa_CMfactor(model_frequency_list, params_list[2], params_list[3], params_list[4], params_list[5])
        model_DEPforce_list = model_hopa_DEPforce(model_frequency_list, params_list[0], params_list[1], params_list[2], params_list[3], params_list[4], params_list[5])


        self.MplCMWidget.canvas.axes.clear()
        self.MplCMWidget.canvas.axes.plot(model_frequency_list, model_CMfactor_list)
        self.MplCMWidget.canvas.axes.set_xlabel('Frequency (Hz)',labelpad=5)
        self.MplCMWidget.canvas.axes.set_ylabel('CM factor',labelpad=5)
        self.MplCMWidget.canvas.axes.set_xscale("log")
        self.MplCMWidget.canvas.axes.tick_params(labelsize='small')
        if self.ZeroHlineEntry.isChecked():
            self.MplCMWidget.canvas.axes.axhline(0, color='black', linestyle='--', lw=1)
        self.MplCMWidget.canvas.axes.grid(which='major', axis='both', color='lightgrey', linestyle='--')

        self.MplCMWidget4.canvas.axes.clear()
        self.MplCMWidget4.canvas.axes.plot(model_frequency_list, model_DEPforce_list)
        self.MplCMWidget4.canvas.axes.set_xlabel('Frequency (Hz)',labelpad=5)
        self.MplCMWidget4.canvas.axes.set_ylabel('DEP force',labelpad=5)
        self.MplCMWidget4.canvas.axes.set_xscale("log")
        self.MplCMWidget4.canvas.axes.tick_params(labelsize='small')
        if self.ZeroHlineEntry.isChecked():
            self.MplCMWidget4.canvas.axes.axhline(0, color='black', linestyle='--', lw=1)
        self.MplCMWidget4.canvas.axes.grid(which='major', axis='both', color='lightgrey', linestyle='--')

        cross_over(model_frequency_list, model_CMfactor_list, self.firstcrossoverentry, self.secondcrossoverentry,
                   self.markcrossover, self.MplCMWidget, self.MplCMWidget4, int(self.model_gen_numberOfPoints_value_entry.text()))

        model_CMfactor_list_withNoise = awgnNoise(np.array(model_CMfactor_list), float(self.model_add_noise_value_entry.text()), L=1)
        model_DEPforce_list_withNoise = awgnNoise(np.array(model_DEPforce_list), float(self.model_add_noise_value_entry.text()), L=1)
        if self.model_add_noise_checkBox.isChecked():
            self.MplCMWidget.canvas.axes.plot(model_frequency_list, model_CMfactor_list_withNoise, color = 'orange', linewidth=1, linestyle='-.')
            self.MplCMWidget4.canvas.axes.plot(model_frequency_list, model_DEPforce_list_withNoise, color = 'orange', linewidth=1, linestyle='-.')
            with_noise = True
        else:
            with_noise = False

        self.MplCMWidget.canvas.draw()
        self.MplCMWidget4.canvas.draw()

        self.wb = Workbook()
        self.colnumb = 1
        addExcel(self.wb, self.colnumb, model_frequency_list, model_CMfactor_list, model_CMfactor_list_withNoise, model_DEPforce_list, model_DEPforce_list_withNoise, params_list, 'hopa', with_noise)

        if self.model_add_noise_checkBox.isChecked():
            self.colnumb = self.colnumb + 6
        else:
            self.colnumb = self.colnumb + 4

    def AddSphModel(self):
        params_list = [float(self.model_gen_fieldgrad_value_entry.text()), float(self.model_hopa_particle_radius_value_entry.text()), float(self.model_hopa_particle_perm_value_entry.text()), float(self.model_hopa_particle_cond_value_entry.text()), float(self.model_gen_buffer_perm_value_entry.text()), float(self.model_gen_buffer_cond_value_entry.text())]

        model_frequency_list = np.logspace(np.log10(frequencyConvertor(self.model_gen_startFrequency_value_entry, self.model_gen_startFrequency_division)), np.log10(frequencyConvertor(self.model_gen_stopFrequency_value_entry, self.model_gen_stopFrequency_division)), num=int(self.model_gen_numberOfPoints_value_entry.text()), base=10)
        model_CMfactor_list = model_hopa_CMfactor(model_frequency_list, params_list[2], params_list[3], params_list[4], params_list[5])
        model_DEPforce_list = model_hopa_DEPforce(model_frequency_list, params_list[0], params_list[1], params_list[2], params_list[3], params_list[4], params_list[5])

        self.MplCMWidget.canvas.axes.plot(model_frequency_list, model_CMfactor_list)
        self.MplCMWidget4.canvas.axes.plot(model_frequency_list, model_DEPforce_list)
        cross_over(model_frequency_list, model_CMfactor_list, self.firstcrossoverentry, self.secondcrossoverentry,
                   self.markcrossover, self.MplCMWidget, self.MplCMWidget4, int(self.model_gen_numberOfPoints_value_entry.text()))

        model_CMfactor_list_withNoise = awgnNoise(np.array(model_CMfactor_list), float(self.model_add_noise_value_entry.text()), L=1)
        model_DEPforce_list_withNoise = awgnNoise(np.array(model_DEPforce_list), float(self.model_add_noise_value_entry.text()), L=1)
        if self.model_add_noise_checkBox.isChecked():
            self.MplCMWidget.canvas.axes.plot(model_frequency_list, model_CMfactor_list_withNoise, color = 'orange', linewidth=1, linestyle='-.')
            self.MplCMWidget4.canvas.axes.plot(model_frequency_list, model_DEPforce_list_withNoise, color = 'orange', linewidth=1, linestyle='-.')
            with_noise = True
        else:
            with_noise = False

        self.MplCMWidget.canvas.draw()
        self.MplCMWidget4.canvas.draw()

        addExcel(self.wb, self.colnumb, model_frequency_list, model_CMfactor_list, model_CMfactor_list_withNoise, model_DEPforce_list, model_DEPforce_list_withNoise, params_list, 'hopa', with_noise)
        if self.model_add_noise_checkBox.isChecked():
            self.colnumb = self.colnumb + 6
        else:
            self.colnumb = self.colnumb + 4

    def GenerateSSModel(self):
        params_list = [float(self.model_gen_fieldgrad_value_entry.text()),
                            float(self.model_sish_particle_radius_value_entry.text()), float(self.model_sish_membrane_thickness_value_entry.text()),
                            float(self.model_sish_membrane_perm_value_entry.text()), float(self.model_sish_membrane_cond_value_entry.text()),
                            float(self.model_sish_cytoplasm_perm_value_entry.text()), float(self.model_sish_cytoplasm_cond_value_entry.text()),
                            float(self.model_gen_buffer_perm_value_entry.text()), float(self.model_gen_buffer_cond_value_entry.text())]

        model_frequency_list = np.logspace(np.log10(frequencyConvertor(self.model_gen_startFrequency_value_entry, self.model_gen_startFrequency_division)), np.log10(frequencyConvertor(self.model_gen_stopFrequency_value_entry, self.model_gen_stopFrequency_division)), num=int(self.model_gen_numberOfPoints_value_entry.text()), base=10)

        model_CMfactor_list = model_sish_CMfactor(model_frequency_list, params_list[1], params_list[2], params_list[3], params_list[4], params_list[5], params_list[6], params_list[7], params_list[8])
        model_DEPforce_list = model_sish_DEPforce(model_frequency_list, params_list[0], params_list[1], params_list[2], params_list[3], params_list[4], params_list[5], params_list[6], params_list[7], params_list[8])

        self.MplCMWidget.canvas.axes.clear()
        self.MplCMWidget.canvas.axes.plot(model_frequency_list, model_CMfactor_list)
        self.MplCMWidget.canvas.axes.set_xlabel('Frequency (Hz)',labelpad=5)
        self.MplCMWidget.canvas.axes.set_ylabel('CM factor',labelpad=5)
        self.MplCMWidget.canvas.axes.set_xscale("log")
        self.MplCMWidget.canvas.axes.tick_params(labelsize='small')
        if self.ZeroHlineEntry.isChecked():
            self.MplCMWidget.canvas.axes.axhline(0, color='black', linestyle='--', lw=1)
        self.MplCMWidget.canvas.axes.grid(which='major', axis='both', color='lightgrey', linestyle='--')

        self.MplCMWidget4.canvas.axes.clear()
        self.MplCMWidget4.canvas.axes.plot(model_frequency_list, model_DEPforce_list)
        self.MplCMWidget4.canvas.axes.set_xlabel('Frequency (Hz)',labelpad=5)
        self.MplCMWidget4.canvas.axes.set_ylabel('DEP force',labelpad=5)
        self.MplCMWidget4.canvas.axes.set_xscale("log")
        self.MplCMWidget4.canvas.axes.tick_params(labelsize='small')
        if self.ZeroHlineEntry.isChecked():
            self.MplCMWidget4.canvas.axes.axhline(0, color='black', linestyle='--', lw=1)
        self.MplCMWidget4.canvas.axes.grid(which='major', axis='both', color='lightgrey', linestyle='--')

        cross_over(model_frequency_list, model_CMfactor_list, self.firstcrossoverentry, self.secondcrossoverentry,
                   self.markcrossover, self.MplCMWidget, self.MplCMWidget4, int(self.model_gen_numberOfPoints_value_entry.text()))

        model_CMfactor_list_withNoise = awgnNoise(np.array(model_CMfactor_list), float(self.model_add_noise_value_entry.text()), L=1)
        model_DEPforce_list_withNoise = awgnNoise(np.array(model_DEPforce_list), float(self.model_add_noise_value_entry.text()), L=1)
        if self.model_add_noise_checkBox.isChecked():
            self.MplCMWidget.canvas.axes.plot(model_frequency_list, model_CMfactor_list_withNoise, color = 'orange', linewidth=1, linestyle='-.')
            self.MplCMWidget4.canvas.axes.plot(model_frequency_list, model_DEPforce_list_withNoise, color = 'orange', linewidth=1, linestyle='-.')
            with_noise = True
        else:
            with_noise = False

        self.MplCMWidget.canvas.draw()
        self.MplCMWidget4.canvas.draw()

        self.wb = Workbook()
        self.colnumb = 1
        addExcel(self.wb, self.colnumb, model_frequency_list, model_CMfactor_list, model_CMfactor_list_withNoise, model_DEPforce_list, model_DEPforce_list_withNoise, params_list, 'sish', with_noise)

        if self.model_add_noise_checkBox.isChecked():
            self.colnumb = self.colnumb + 6
        else:
            self.colnumb = self.colnumb + 4

    def AddSSModel(self):
        params_list = [float(self.model_gen_fieldgrad_value_entry.text()),
                            float(self.model_sish_particle_radius_value_entry.text()), float(self.model_sish_membrane_thickness_value_entry.text()),
                            float(self.model_sish_membrane_perm_value_entry.text()), float(self.model_sish_membrane_cond_value_entry.text()),
                            float(self.model_sish_cytoplasm_perm_value_entry.text()), float(self.model_sish_cytoplasm_cond_value_entry.text()),
                            float(self.model_gen_buffer_perm_value_entry.text()), float(self.model_gen_buffer_cond_value_entry.text())]

        model_frequency_list = np.logspace(np.log10(frequencyConvertor(self.model_gen_startFrequency_value_entry, self.model_gen_startFrequency_division)), np.log10(frequencyConvertor(self.model_gen_stopFrequency_value_entry, self.model_gen_stopFrequency_division)), num=int(self.model_gen_numberOfPoints_value_entry.text()), base=10)

        model_CMfactor_list = model_sish_CMfactor(model_frequency_list, params_list[1], params_list[2], params_list[3], params_list[4], params_list[5], params_list[6], params_list[7], params_list[8])
        model_DEPforce_list = model_sish_DEPforce(model_frequency_list, params_list[0], params_list[1], params_list[2], params_list[3], params_list[4], params_list[5], params_list[6], params_list[7], params_list[8])

        self.MplCMWidget.canvas.axes.plot(model_frequency_list, model_CMfactor_list)
        self.MplCMWidget4.canvas.axes.plot(model_frequency_list, model_DEPforce_list)
        cross_over(model_frequency_list, model_CMfactor_list, self.firstcrossoverentry, self.secondcrossoverentry,
                   self.markcrossover, self.MplCMWidget, self.MplCMWidget4, int(self.model_gen_numberOfPoints_value_entry.text()))

        model_CMfactor_list_withNoise = awgnNoise(np.array(model_CMfactor_list), float(self.model_add_noise_value_entry.text()), L=1)
        model_DEPforce_list_withNoise = awgnNoise(np.array(model_DEPforce_list), float(self.model_add_noise_value_entry.text()), L=1)
        if self.model_add_noise_checkBox.isChecked():
            self.MplCMWidget.canvas.axes.plot(model_frequency_list, model_CMfactor_list_withNoise, color = 'orange', linewidth=1, linestyle='-.')
            self.MplCMWidget4.canvas.axes.plot(model_frequency_list, model_DEPforce_list_withNoise, color = 'orange', linewidth=1, linestyle='-.')
            with_noise = True
        else:
            with_noise = False

        self.MplCMWidget.canvas.draw()
        self.MplCMWidget4.canvas.draw()

        addExcel(self.wb, self.colnumb, model_frequency_list, model_CMfactor_list, model_CMfactor_list_withNoise, model_DEPforce_list, model_DEPforce_list_withNoise, params_list, 'sish', with_noise)
        if self.model_add_noise_checkBox.isChecked():
            self.colnumb = self.colnumb + 6
        else:
            self.colnumb = self.colnumb + 4

#Setting startup parameters

data = Data()
fit = MyFittings()


app = QApplication([])
window = MainUI()
paramsUI = PropertiesUI()
datapointsUI = DataPointsUI()
autoProcessUI = AutoProcessUI()
convertUI = ConvertUI(window, data)
renameUI = RenameUI()

window.qtvar_main_sish_convertButton.clicked.connect(convertUI.OPEN)
window.qtvar_main_hopa_convertButton.clicked.connect(convertUI.OPEN)
window.fitting_hopa_settings_button.clicked.connect(paramsUI.OPEN)

window.menu_parameters_settings.triggered.connect(paramsUI.OPEN)
window.menu_datapoints_settings.triggered.connect(datapointsUI.OPEN)
window.menu_autoProcessFolder.triggered.connect(autoProcessUI.OPEN)


window.actionAutoRename.triggered.connect(renameUI.OPEN)

app.setAttribute(QtCore.Qt.AA_DisableHighDpiScaling)



hopa_params = MyParameters()
hopa_params.startupParameters('saves/default_hopa_parameters')
hopa_params.changeGUIFittingParameters(paramsUI, window, 'hopa')

sish_params = MyParameters()
sish_params.startupParameters('saves/default_sish_parameters')
sish_params.changeGUIFittingParameters(paramsUI, window, 'sish')

trayIcon = QSystemTrayIcon()
trayIcon.setIcon(QIcon("icon.png"))
trayIcon.setVisible(True)

window.show()

print('''
OpenDEP  Copyright (C) 2022  Ioan Cristian Tivig
This program comes with ABSOLUTELY NO WARRANTY
This is free software, and you are welcome to redistribute it
under certain conditions; See LICENSE file in root folder for more info
You can contact the developer/owner of OpenDEP at "ioan.tivig@gmail.com".
'''
    )

app.exec_()

