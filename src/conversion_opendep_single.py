import os
import re

import cv2
import numpy as np
import matplotlib.pyplot as plt


class ConversionOpenDEPSC:
    def __init__(self):
        self.bkg_path = 'data_01/baseline.jpg'
        self.input_path = 'data_01/input'
        self.output_path = 'data_01/output'

        self.conversion_factor = 9.610
        self.parm1 = 15
        self.parm2 = 30
        self.cells_distance = 70
        self.min_radius = 10
        self.max_radius = 200

        self.y_crop = 100
        self.x_crop = 200
        self.crop_coord = []
        self.cell_index = 1
        self.movement_direction = 'Horizontal'

        self.baseline_coord = []
        self.radius_list = []
        self.cells_info = None

    def detect_cells(self, image_path):
        img = cv2.imread(image_path, cv2.IMREAD_COLOR)
        org_img = cv2.imread(image_path, cv2.IMREAD_COLOR)

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray_blurred = cv2.blur(gray, (3, 3))

        detected_cells = cv2.HoughCircles(gray_blurred,
                                          cv2.HOUGH_GRADIENT,
                                          1,
                                          self.cells_distance,
                                          param1=self.parm1,
                                          param2=self.parm2,
                                          minRadius=self.min_radius,
                                          maxRadius=self.max_radius)

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
        font_scale = 1.5
        color = (4, 219, 253)
        thickness = 3

        for key in cell_info:
            cv2.circle(img, (cell_info[key][0], cell_info[key][1]), cell_info[key][2], (0, 255, 0), 2)
            cv2.circle(img, (cell_info[key][0], cell_info[key][1]), 1, (0, 0, 255), 3)
            if is_bkg:
                cv2.putText(img,
                            str(key),
                            (cell_info[key][0] + 15, cell_info[key][1] - 15),
                            font,
                            font_scale,
                            color,
                            thickness,
                            cv2.LINE_AA)

        if is_bkg:
            name, ext = os.path.splitext(image_path)
            fullpath = "{name}_{uid}{ext}".format(name=name, uid='marked', ext=ext)
            cv2.imwrite(fullpath, img)

        return img

    def get_sample_data(self, input_path, output_path):

        x = self.crop_coord[1]
        y = self.crop_coord[0]
        print(x, y)
        values_list = [[], [], []]

        # iterate through the names of contents of the folder
        for image_path in os.listdir(input_path):
            frequency = re.split("OpenDEP_|Hz", image_path)
            values_list[2].append(float(frequency[1]))

            instance_path = os.path.join(input_path, image_path)
            image_to_crop = cv2.imread(instance_path)
            crop_img = image_to_crop[y - self.y_crop:y + self.y_crop, x - self.x_crop:x + self.x_crop]

            fullpath = os.path.join(output_path, image_path)
            cv2.imwrite(fullpath, crop_img)

            instanced_status, instanced_cells_info = self.detect_cells(fullpath)
            instanced_marked_image = self.mark_cells_on_image(
                image_path=fullpath,
                cell_info=instanced_cells_info,
                is_bkg=False)

            cv2.imwrite(fullpath, instanced_marked_image)
            values_list[0].append(instanced_cells_info[1][1])
            values_list[1].append(instanced_cells_info[1][0])
            self.radius_list.append(instanced_cells_info[1][2])

        avg_radius = round(np.average(self.radius_list) / self.conversion_factor, 3)
        stdev_radius = round(np.std(self.radius_list) / self.conversion_factor, 3)

        for i in range(len(values_list[0])):
            values_list[0][i] = (round((float(values_list[0][i]) - float(self.baseline_coord[0])) / self.conversion_factor, 3) * -1)
        for i in range(len(values_list[1])):
            values_list[1][i] = (round((float(values_list[1][i]) - float(self.baseline_coord[1])) / self.conversion_factor, 3) * -1)

        if self.movement_direction == 'Horizontal':
            values_list = [values_list[1], values_list[2]]
        else:
            values_list = [values_list[0], values_list[2]]

        values_list[0] = np.array(values_list[0])
        values_list[1] = np.array(values_list[1])
        sort = values_list[1].argsort()
        values_list[0] = list(values_list[0][sort])
        values_list[1] = list(values_list[1][sort])

        return values_list, avg_radius, stdev_radius

    def get_baseline_data(self, baseline_path, cell_index):
        status, cells_info = self.detect_cells(
            image_path=baseline_path)

        crop_x = cells_info[cell_index][0]
        crop_y = cells_info[cell_index][1]
        self.crop_coord = [crop_y, crop_x]
        radius = cells_info[cell_index][2]
        self.radius_list = [radius]

        image_to_crop = cv2.imread(baseline_path)
        crop_img = image_to_crop[self.crop_coord[0] - self.y_crop:self.crop_coord[0] + self.y_crop, self.crop_coord[1] - self.x_crop:self.crop_coord[1] + self.x_crop]

        name, ext = os.path.splitext(baseline_path)
        fullpath = "{name}_{uid}{ext}".format(name=name, uid='cropped', ext=ext)
        cv2.imwrite(fullpath, crop_img)

        status, cells_info = self.detect_cells(
            image_path=fullpath)

        marked_image = self.mark_cells_on_image(
            image_path=fullpath,
            cell_info=cells_info,
            is_bkg=False)

        cv2.imwrite(fullpath, marked_image)

        print(cells_info)
        baseline_x = cells_info[1][0]
        baseline_y = cells_info[1][1]
        self.baseline_coord = [baseline_y, baseline_x]
        baseline_radius = cells_info[1][2]
        self.radius_list.append(baseline_radius)

        # return crop_img, crop_x, crop_y, baseline_x, baseline_y
        print(self.baseline_coord, self.crop_coord, self.radius_list)
        return marked_image

    def convert_single_cell(self, input_path, output_path, baseline_path, cell_index):
        marked_image = self.get_baseline_data(baseline_path, cell_index)
        values_list, avg_radius, stdev_radius = self.get_sample_data(input_path, output_path)
        print(values_list, avg_radius, stdev_radius)

        cell_radius = round(float(avg_radius), 3)
        frequencies = values_list[1]
        cm_factors = values_list[0]

        return marked_image, frequencies, cm_factors, cell_radius


def random_thing():
    convert = ConversionOpenDEPSC()
    status, convert.cells_info = convert.detect_cells(image_path=convert.bkg_path)
    if status:
        marked_image = convert.mark_cells_on_image(
            image_path=convert.bkg_path,
            cell_info=convert.cells_info)

        cv2.imshow("Detected Circle", marked_image)
        cv2.waitKey()
        cell_index = int(input())

        values_list, avg_radius, stdev_radius = convert.get_sample_data(convert.input_path, convert.output_path,
                                                                        cell_index, convert.cells_info)

        for i in range(len(values_list[0])):
            print(values_list[0][i] / convert.conversion_factor, "  --  ",
                  values_list[1][i] / convert.conversion_factor)
        print('Radius is: ', avg_radius / convert.conversion_factor, ' +/- ', stdev_radius / convert.conversion_factor)

    # name, ext = os.path.splitext(image_path)
    # fullpath = "{name}_{uid}{ext}".format(name=name, uid='output', ext=ext)

    else:
        print("No detected circles!!")
