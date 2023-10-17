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


class GraphWidgetLiveCapture(QWidget):

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)

        self.figure = plt.figure()
        self.figure.subplots_adjust(left=-0,
                                    right=1.0,
                                    bottom=-0.00,
                                    top=1.00)
        self.canvas = FigureCanvas(self.figure)

        layout = QVBoxLayout()
        layout.addWidget(self.canvas)

        self.canvas.axes = self.canvas.figure.add_subplot(111)
        self.canvas.axes.set_axis_off()
        self.canvas.axes.get_xaxis().set_visible(False)
        self.canvas.axes.get_yaxis().set_visible(False)

        self.setLayout(layout)

    def refresh_UI(self, image):
        self.canvas.axes.clear()
        image_float = img_as_float(image)

        self.canvas.axes.imshow(image_float, interpolation='nearest', aspect='auto')
        self.canvas.draw()
