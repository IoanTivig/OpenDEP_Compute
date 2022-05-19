import numpy as np
from shapely.geometry import LineString

def cross_over(frequencyList, CMfactorList, firstcrossoverentry, secondcrossoverentry, markcrossover, MplCMWidget, MplCMWidget4, listlength):
    zeroList = [0] * listlength
    first_line = LineString(np.column_stack((frequencyList, CMfactorList)))
    second_line = LineString(np.column_stack((frequencyList, zeroList)))
    intersection = first_line.intersection(second_line)

    if intersection.geom_type == 'MultiPoint':
        if LineString(intersection).xy[0][0] > 1000000:
            firstcrossoverentry.setText(str(round((LineString(intersection).xy[0][0] / 1000000), 2)) + " MHz")
        elif LineString(intersection).xy[0][0] > 1000:
            firstcrossoverentry.setText(str(int(LineString(intersection).xy[0][0] / 1000)) + " kHz")
        else:
            firstcrossoverentry.setText(str(int(LineString(intersection).xy[0][0])) + " Hz")

        print(LineString(intersection).xy[0][0])

        if LineString(intersection).xy[0][1] > 1000000:
            secondcrossoverentry.setText(str(round((LineString(intersection).xy[0][1] / 1000000), 2)) + " MHz")
        elif LineString(intersection).xy[0][1] > 1000:
            secondcrossoverentry.setText(str(int(LineString(intersection).xy[0][1] / 1000)) + " kHz")
        else:
            secondcrossoverentry.setText(str(int(LineString(intersection).xy[0][1])) + " Hz")

        print(LineString(intersection).xy[0][1])

    elif intersection.geom_type == 'Point':
        print((intersection.xy[0][0]))
        if intersection.xy[0][0] > 1000000:
            firstcrossoverentry.setText(str(round((intersection.xy[0][0] / 1000000), 2)) + " MHz")
        elif intersection.xy[0][0] > 1000:
            firstcrossoverentry.setText(str(int(intersection.xy[0][0] / 1000)) + " kHz")
        else:
            firstcrossoverentry.setText(str(int(intersection.xy[0][0])) + " Hz")

        secondcrossoverentry.setText('N/A')

    else:
        firstcrossoverentry.setText('N/A')
        secondcrossoverentry.setText('N/A')

    if markcrossover.isChecked():
        if intersection.geom_type == 'MultiPoint':
            MplCMWidget.canvas.axes.plot(*LineString(intersection).xy, 'o')
        elif intersection.geom_type == 'Point':
            MplCMWidget.canvas.axes.plot(*intersection.xy, 'o')

    if markcrossover.isChecked():
        if intersection.geom_type == 'MultiPoint':
            MplCMWidget4.canvas.axes.plot(*LineString(intersection).xy, 'o')
        elif intersection.geom_type == 'Point':
            MplCMWidget4.canvas.axes.plot(*intersection.xy, 'o')
