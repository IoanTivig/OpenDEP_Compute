# ------------------------------------------------------
# -------------------- mplwidget.py --------------------
# ------------------------------------------------------

### START IMPORTS ###
## PyQt5 imports ##
from PyQt5.QtWidgets import *
from skimage import io
from skimage.util import img_as_float

## Matplotlib imports ##
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvas
from matplotlib.ticker import StrMethodFormatter
from matplotlib.patches import Rectangle
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
        self.canvas.axes.get_xaxis().set_visible(False)
        self.canvas.axes.get_yaxis().set_visible(False)

        self.setLayout(layout)

    def refresh_UI(self, edges_position, image_path, points_to_remove, electrodes_positions):
        self.canvas.axes.clear()
        image = io.imread(image_path)
        image_float = img_as_float(image)
        image_height = image.shape[0]

        self.canvas.axes.imshow(image_float, interpolation='nearest', aspect='auto')
        for i in edges_position:
            self.canvas.axes.axvline(i + points_to_remove, color='black', linestyle='--', linewidth=0.5)

        # Highlight the electrodes by etching the electrode area
        for i in electrodes_positions:
            print(i)
            rect = Rectangle((i[0] + points_to_remove, 0), i[1] - i[0], image_height,  facecolor='none',
                             edgecolor=(0, 0, 0, 0.25), hatch='o', linewidth=0)
            self.canvas.axes.add_patch(rect)

        self.canvas.draw()