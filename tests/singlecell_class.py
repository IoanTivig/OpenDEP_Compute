import os
import cv2
import numpy as np
import matplotlib.pyplot as plt

class ConversionOpenDEPSC:
    def __init__(self):
        self.bkg_path = '../data/examples/OpenDEP single-cell/data_01/baseline.jpg'
        self.input_path = '../data/examples/OpenDEP single-cell/data_01/input'
        self.output_path = '../data/examples/OpenDEP single-cell/data_01/output'

        self.conversion_factor = 9.610
        self.cells_info = None

    def detect_cells(self, image_path):
        img = cv2.imread(image_path, cv2.IMREAD_COLOR)
        org_img = cv2.imread(image_path, cv2.IMREAD_COLOR)

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray_blurred = cv2.blur(gray, (3, 3))

        detected_cells = cv2.HoughCircles(gray_blurred,
                                            cv2.HOUGH_GRADIENT,
                                            1,
                                            70,
                                            param1=15,
                                            param2=30,
                                            minRadius=10,
                                            maxRadius=200)

        cells_info = {}
        if detected_cells is None:
            status = False
            self.cells_info = cells_info
            return status, cells_info

        elif detected_cells is not None:
            i = 1
            detected_cells = np.uint16(np.around(detected_cells))
            for pt in detected_cells[0, :]:
                y, x, r = pt[0], pt[1], pt[2]
                cells_info[i] = [y, x, r]
                i = i + 1
            status = True
            self.cells_info = cells_info
            return status, cells_info

    def mark_cells_on_image(self, image_path, cell_info, is_bkg=True):
        img = cv2.imread(image_path, cv2.IMREAD_COLOR)

        font = cv2.FONT_HERSHEY_SIMPLEX
        fontScale = 1.5
        color = (4, 219, 253)
        thickness = 3

        for key in cell_info:
            cv2.circle(img, (cell_info[key][0], cell_info[key][1]), cell_info[key][2], (0, 255, 0), 2)
            cv2.circle(img, (cell_info[key][0], cell_info[key][1]), 1, (0, 0, 255), 3)
            if is_bkg:
                cv2.putText(img,
                            str(key),
                            (cell_info[key][0]+ 15, cell_info[key][1] - 15),
                            font,
                            fontScale,
                            color,
                            thickness,
                            cv2.LINE_AA)

        if is_bkg:
            name, ext = os.path.splitext(image_path)
            fullpath =  "{name}_{uid}{ext}".format(name=name, uid='marked', ext=ext)
            cv2.imwrite(fullpath, img)

        return img

    def crop_images_around_cell(self, input_path, output_path, cell_index, cells_info):

        x = cells_info[cell_index][0]
        y = cells_info[cell_index][1]
        radius = cells_info[cell_index][2]
        print(x, y, radius)

        values_list = [[],[],[]]

        # iterate through the names of contents of the folder
        for image_path in os.listdir(input_path):
            instance_path = os.path.join(input_path, image_path)
            image_to_crop = cv2.imread(instance_path)
            crop_img = image_to_crop[y - 100:y + 100, x - 200:x + 200]

            fullpath = os.path.join(output_path, image_path)
            cv2.imwrite(fullpath, crop_img)

            instanced_status, instanced_cells_info = self.detect_cells(fullpath)
            instanced_marked_image = convert.mark_cells_on_image(
                                                                image_path=fullpath,
                                                                cell_info=instanced_cells_info,
                                                                is_bkg=False)

            cv2.imwrite(fullpath, instanced_marked_image)
            values_list[0].append(instanced_cells_info[1][0])
            values_list[1].append(instanced_cells_info[1][1])
            values_list[2].append(instanced_cells_info[1][2])

        avg_radius = np.average(values_list[2])
        stdev_radius = np.std(values_list[2])
        values_list = values_list[0:-1]

        return values_list, avg_radius, stdev_radius

convert = ConversionOpenDEPSC()
status, convert.cells_info = convert.detect_cells(image_path = convert.bkg_path)
if status:
    marked_image = convert.mark_cells_on_image(
                                            image_path = convert.bkg_path,
                                            cell_info = convert.cells_info)

    cv2.imshow("Detected Circle", marked_image)
    cv2.waitKey()
    cell_index = int(input())

    values_list, avg_radius, stdev_radius = convert.crop_images_around_cell(convert.input_path, convert.output_path, cell_index, convert.cells_info)

    for i in range(len(values_list[0])):
        print(values_list[0][i] / convert.conversion_factor, "  --  ",values_list[1][i] / convert.conversion_factor)
    print('Radius is: ', avg_radius / convert.conversion_factor, ' +/- ', stdev_radius  / convert.conversion_factor)

#name, ext = os.path.splitext(image_path)
#fullpath = "{name}_{uid}{ext}".format(name=name, uid='output', ext=ext)


else:
    print("No detected circles!!")