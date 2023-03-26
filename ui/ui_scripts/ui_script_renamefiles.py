# ------------------------------------------------------
# ------------------- RENAME MODULE --------------------
# ------------------------------------------------------

# External imports #
from PyQt5 import QtGui
from PyQt5.QtWidgets import QDialog, QHeaderView, QFileDialog, QTableWidgetItem
from PyQt5.uic import loadUi

# Local imports #
from src.rename import *


"""
Rename UI script:
This file covers all UI related functionality to the rename module,
which renames and arranges microscopically acquired images which 
will further be converted to CM factor values vs frequencies
All buttons and widgets are connected and run scripts found
in src/rename module. It also handles load and save settings.
"""


class RenameUI(QDialog):
    def __init__(self):
        QDialog.__init__(self)
        loadUi("ui/rename_files.ui", self)
        self.setWindowTitle("Auto-rename")
        self.setWindowIcon(QtGui.QIcon("icon.png"))

        # Start-up parameters #
        desktop = os.path.join(os.path.join(os.environ["USERPROFILE"]), "Desktop")
        self.qtvar_renameImages_inputFolder.setText(desktop)
        self.qtvar_renameImages_inputFrequency.setText("1000")

        header = self.qtvar_renameImages_frequencyTable.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)

        self.qtvar_renameImages_closeButton.clicked.connect(self.close)
        self.qtvar_renameImages_renameButton.clicked.connect(self.rename)
        self.qtvar_renameImages_addButton.clicked.connect(self.add)
        self.qtvar_renameImages_removeButton.clicked.connect(self.remove_row)
        self.qtvar_renameImages_upButton.clicked.connect(self.switch_up)
        self.qtvar_renameImages_downButton.clicked.connect(self.switch_down)
        self.qtvar_renameImages_saveButton.clicked.connect(self.save_button)
        self.qtvar_renameImages_loadButton.clicked.connect(self.load_button)

        self.qtvar_renameImages_inputFolderButton.clicked.connect(
            lambda: self.getPathway(self.qtvar_renameImages_inputFolder)
        )

    def OPEN(self):
        self.show()

    def getPathway(self, entry):
        folder = QFileDialog.getExistingDirectory(self, "Select a folder")
        entry.setText(folder)

    def add(self):
        rowPosition = self.qtvar_renameImages_frequencyTable.rowCount()
        self.qtvar_renameImages_frequencyTable.insertRow(rowPosition)

        self.qtvar_renameImages_frequencyTable.setItem(
            rowPosition,
            0,
            QTableWidgetItem(self.qtvar_renameImages_inputFrequency.text()),
        )
        self.qtvar_renameImages_frequencyTable.setItem(
            rowPosition,
            1,
            QTableWidgetItem(self.qtvar_renameImages_comboFrequency.currentText()),
        )

    def remove_row(self):
        current_row = self.qtvar_renameImages_frequencyTable.currentRow()
        self.qtvar_renameImages_frequencyTable.removeRow(current_row)

    def switch_up(self):
        current_row = self.qtvar_renameImages_frequencyTable.currentRow()

        if current_row > 0:
            switch_row = self.qtvar_renameImages_frequencyTable.currentRow() - 1

            current_value = self.qtvar_renameImages_frequencyTable.item(
                current_row, 0
            ).text()
            current_unit = self.qtvar_renameImages_frequencyTable.item(
                current_row, 1
            ).text()

            switch_value = self.qtvar_renameImages_frequencyTable.item(
                current_row - 1, 0
            ).text()
            switch_unit = self.qtvar_renameImages_frequencyTable.item(
                current_row - 1, 1
            ).text()

            self.qtvar_renameImages_frequencyTable.setItem(
                current_row, 0, QTableWidgetItem(switch_value)
            )
            self.qtvar_renameImages_frequencyTable.setItem(
                current_row, 1, QTableWidgetItem(switch_unit)
            )

            self.qtvar_renameImages_frequencyTable.setItem(
                current_row - 1, 0, QTableWidgetItem(current_value)
            )
            self.qtvar_renameImages_frequencyTable.setItem(
                current_row - 1, 1, QTableWidgetItem(current_unit)
            )

            self.qtvar_renameImages_frequencyTable.setCurrentCell(switch_row, 0)

    def switch_down(self):
        current_row = self.qtvar_renameImages_frequencyTable.currentRow()

        if current_row < self.qtvar_renameImages_frequencyTable.rowCount() - 1:
            switch_row = self.qtvar_renameImages_frequencyTable.currentRow() + 1

            current_value = self.qtvar_renameImages_frequencyTable.item(
                current_row, 0
            ).text()
            current_unit = self.qtvar_renameImages_frequencyTable.item(
                current_row, 1
            ).text()

            switch_value = self.qtvar_renameImages_frequencyTable.item(
                current_row + 1, 0
            ).text()
            switch_unit = self.qtvar_renameImages_frequencyTable.item(
                current_row + 1, 1
            ).text()

            self.qtvar_renameImages_frequencyTable.setItem(
                current_row, 0, QTableWidgetItem(switch_value)
            )
            self.qtvar_renameImages_frequencyTable.setItem(
                current_row, 1, QTableWidgetItem(switch_unit)
            )

            self.qtvar_renameImages_frequencyTable.setItem(
                current_row + 1, 0, QTableWidgetItem(current_value)
            )
            self.qtvar_renameImages_frequencyTable.setItem(
                current_row + 1, 1, QTableWidgetItem(current_unit)
            )

            self.qtvar_renameImages_frequencyTable.setCurrentCell(switch_row, 0)

    def save(self, file_path):
        table = self.qtvar_renameImages_frequencyTable
        columnCount = table.columnCount()
        rowCount = table.rowCount()
        # print(columnCount, rowCount)

        list = []
        for row in range(rowCount):
            value = table.item(row, 0).text()
            unit = table.item(row, 1).text()
            list.append([value, unit])

        with open(file_path, "w") as fp:
            for item in list:
                # write each item on a new line
                fp.write(f"{item[0]}--{item[1]}\n")
            # print('Done')

    def save_button(self):
        file, check = QFileDialog.getSaveFileName(
            None, "Save rename settings", "", "Rename save format (*.sren)"
        )
        if check:
            self.save(file)

    def load(self, file_path):
        while self.qtvar_renameImages_frequencyTable.rowCount() > 0:
            self.qtvar_renameImages_frequencyTable.removeRow(0)

        with open(file_path, "r") as fp:
            for line in fp:
                x = line[:-1]
                y = x.split("--")
                # print(y[0], y[1])

                rowPosition = self.qtvar_renameImages_frequencyTable.rowCount()
                self.qtvar_renameImages_frequencyTable.insertRow(rowPosition)

                self.qtvar_renameImages_frequencyTable.setItem(
                    rowPosition, 0, QTableWidgetItem(y[0])
                )
                self.qtvar_renameImages_frequencyTable.setItem(
                    rowPosition, 1, QTableWidgetItem(y[1])
                )

    def load_button(self):
        file, check = QFileDialog.getOpenFileName(
            None, "Save rename settings", "", "Rename save format (*.sren)"
        )
        if check:
            self.load(file)

    def rename(self):
        table = self.qtvar_renameImages_frequencyTable
        columnCount = table.columnCount()
        rowCount = table.rowCount()

        list = []
        for row in range(rowCount):
            unit = table.item(row, 1).text()
            if unit == "Hz":
                value = float(table.item(row, 0).text())
            elif unit == "KHz":
                value = float(table.item(row, 0).text()) * 1000
            elif unit == "MHz":
                value = float(table.item(row, 0).text()) * 1000000
            list.append(value)

        auto_rename(self.qtvar_renameImages_inputFolder.text(), list)