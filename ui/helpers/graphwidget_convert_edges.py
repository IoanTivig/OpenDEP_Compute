# ------------------------------------------------------
# -------------------- mplwidget.py --------------------
# ------------------------------------------------------

### START IMPORTS ###
## PyQt5 imports ##
from PyQt5.QtWidgets import *
from skimage import io, img_as_float

## Matplotlib imports ##
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvas
from matplotlib.ticker import StrMethodFormatter
### END IMPORTS ###


class GraphWidget_convert_edges(QWidget):


    def __init__(self, parent=None):
        QWidget.__init__(self, parent)

        self.figure = plt.figure()
        self.figure.subplots_adjust(left=-0,right=1.0,bottom=-0.00,top=1.00)
        self.canvas = FigureCanvas(self.figure)

        layout = QVBoxLayout()
        layout.addWidget(self.canvas)

        self.canvas.axes = self.canvas.figure.add_subplot(111)
        self.canvas.axes.set_axis_off()

        self.setLayout(layout)

    def refresh_UI(self, edges_position, image_path, points_to_remove):
        self.canvas.axes.clear()
        image = io.imread(image_path)
        image_float = img_as_float(image)

        self.canvas.axes.imshow(image_float)
        for i in edges_position:
            self.canvas.axes.axvline(i + points_to_remove, color='black', linestyle='--', linewidth=0.5)

        self.canvas.draw()