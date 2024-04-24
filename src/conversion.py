# ------------------------------------------------------
# ----------------- CONVERSION MODULE ------------------
# ------------------------------------------------------
import numpy as np

# Local imports #
from src.datamanagement import *

# Image processing #
from skimage import io, img_as_float


"""
Conversion module:
This file handles all image to data_01 conversion functionality
It transforms images obtained through microscopic image acquisition
to CM factors vs frequencies. It also handles automatic electrode detection
for the integrated microfluidic chips.
"""


class Conversion:
    def detect_edges(
        self,
        image_file,
        points_to_remove,
        min_edge_spacing,
        no_pixels_shift=0,
        edge_orientation="Vertical",
        polynomial_deg=7,
    ):
        # Transform images into 2D float arrays
        image_float = img_as_float(io.imread(image_file))

        # Obtain averages of all values along selected direction
        if edge_orientation == "Vertical":
            image_averages = np.mean(image_float, 0)
        elif edge_orientation == "Horizontal":
            image_averages = np.mean(image_float, 1)

        # Remove unwanted points from start and end
        image_averages = image_averages[points_to_remove : -1 * points_to_remove]

        # Get the x axis values for polynomial fit
        x_axis = []
        x = 1
        for i in image_averages:
            x_axis.append(x)
            x = x + 1

        # Fit with a polynomial function and extract the fit from data_01
        poly = np.polyfit(x_axis, image_averages, deg=polynomial_deg)
        image_averages = image_averages - np.polyval(poly, x_axis)

        # Get the points where the edge is visible by detecting change of sign
        edges_position = []
        edges_values = []
        for i in range(0, len(image_averages) - 1):
            if np.sign(image_averages[i]) != np.sign(image_averages[i + 1]):
                edges_position.append(i)
                edges_values.append(image_averages[i])

        spacing_list = []
        remove_list = []

        for i in range(0, len(edges_position) - 1):
            spacing = (edges_position[i] - edges_position[i + 1]) * -1
            spacing_list.append(spacing)

            if spacing < min_edge_spacing:
                remove_list.append(i + 1)

        edges_position_filtered = [
            ele for idx, ele in enumerate(edges_position) if idx not in remove_list
        ]
        spacing_list_filtered = [
            ele for idx, ele in enumerate(spacing_list) if idx not in remove_list
        ]

        edges_no = len(edges_position_filtered)
        average_spaceing = np.round(np.average(spacing_list_filtered), 2)
        stdev_spaceing = np.round(np.std(spacing_list_filtered), 2)

        for i in range(0, len(edges_position_filtered)):
            edges_position_filtered[i] = edges_position_filtered[i] + no_pixels_shift

        # get between which edges the electrodes are (the electrodes are the darker zones
        electrodes_positions = [] #This should be a list of tuples with the start and end of the electrodes
        electrode_gaps_positions = [] #This should be a list of tuples with the start and end of the gaps between the electrodes
        for i in range(0, len(edges_position_filtered) - 1):
            # get grayness between the edges
            grayness = np.mean(image_averages[edges_position_filtered[i]:edges_position_filtered[i + 1]])
            if grayness < 0:
                electrodes_positions.append((edges_position_filtered[i], edges_position_filtered[i + 1]))
            else:
                electrode_gaps_positions.append((edges_position_filtered[i], edges_position_filtered[i + 1]))

        #print("Electrode gaps positions: ", electrode_gaps_positions)
        #print("Electrodes positions: ", electrodes_positions)

        # Returns
        return edges_position_filtered, edges_no, average_spaceing, stdev_spaceing, electrodes_positions, electrode_gaps_positions

    def convert_image_to_CM(
        self,
        image,
        background_image,
        edges_position,
        points_to_remove,
        edge_orientation="Vertical",
        edge_width=1,
        bkg_area_width=5,
        grayness_over_brightness=True,
        bkg_separated=False,
    ):
        # Parameters
        # points_to_remove - Number of points to be removed from end and start of image array
        image = io.imread(image)  # The image that needs to be calculated
        if bkg_separated == True:
            _bkg = io.imread(background_image)  # The background image for correction
        edge_orientation = edge_orientation  # Orientation of your electrodes, hence of your electrode edges
        # edges_position - The list with the position of each edge

        # Transform images into 2D float arrays
        image_float = img_as_float(image)
        if bkg_separated == True:
            _bkg_float = img_as_float(_bkg)

        # Obtain averages of all values along selected direction
        _bkg_averages = []
        if edge_orientation == "Vertical":
            image_averages = np.mean(image_float, 0)
            if bkg_separated == True:
                _bkg_averages = np.mean(_bkg_float, 0)
        if edge_orientation == "Horizontal":
            image_averages = np.mean(image_float, 1)
            if bkg_separated == True:
                _bkg_averages = np.mean(_bkg_float, 1)

        # Remove unwanted points from start and end
        image_averages = image_averages[points_to_remove : -1 * points_to_remove]
        if bkg_separated == True:
            _bkg_averages = _bkg_averages[points_to_remove : -1 * points_to_remove]

        # verify the zones

        # create an average gryness from the hole image
        #_bkg_from_itself_averages = np.mean(image_averages)
        # Create an average background from the image itself, in a range between the two edges
        if bkg_separated == False:
            electrode_and_gaps_center = []
            _intermediary_averages = []
            for i in range(len(edges_position)):
                if i == len(edges_position) - 1:
                    break
                center = int(np.mean([edges_position[i], edges_position[i+1]]))
                electrode_and_gaps_center.append(center)
            for i in electrode_and_gaps_center:
                _intermediary_averages.append(np.mean(image_averages[i - int(bkg_area_width/2) : i + int(bkg_area_width/2)]))
            _bkg_from_itself_averages = np.mean(_intermediary_averages)


        # Substracting the background from data_01 points
        norm_image_averages = []
        for i in range(0, len(image_averages)):
            if bkg_separated == True:
                j = image_averages[i] - _bkg_averages[i]
            elif bkg_separated == False:
                j = image_averages[i] - _bkg_from_itself_averages
            norm_image_averages.append(j)

        # Creating a dummy array for the x axis
        x = []
        j = 0
        for i in norm_image_averages:
            x.append(j)
            j = j + 1

        # Get graynass factor on the edges
        selected_image_averages = []
        for i in edges_position:
            selected_image_averages.append(
                np.mean(norm_image_averages[i - edge_width : i + edge_width])
            )
        selected_image_averages = np.array(selected_image_averages)
        brightness_factor = np.mean(selected_image_averages)

        if grayness_over_brightness == True:
            grayness_factor = -1 * brightness_factor
        else:
            grayness_factor = brightness_factor

        grayness_errors = np.std(selected_image_averages)

        # make a _bkg_averages array with only the _bkg_from_itself_averages value
        if bkg_separated == False:
            for i in range(0, len(image_averages)):
                _bkg_averages.append(_bkg_from_itself_averages)

        # Returns
        return (
            x,
            norm_image_averages,
            image_averages,
            _bkg_averages,
            image_float,
            grayness_factor,
            grayness_errors,
        )

    def ConvertOpenDEPPopulation(
        self,
        convertUI,
        mainUI,
        data,
        folder,
        centrfile,
        points_to_remove=0,
        min_edge_spacing=25,
        no_pixels_shift=0,
        edge_orientation="Vertical",
        grayness_over_brightness=True,
        edge_width=1,
        bkg_area_width=5,
        poly_deg=7,
        bkg_separated=False,
    ):
        try:
            # Create the processed images folder
            if not os.path.exists(os.path.join(folder, "_PROCESSED")):
                os.mkdir(os.path.join(folder, "_PROCESSED"))

            # Get the position of electrodes edges
            if convertUI.qtvar_convertImages_edgesRadio_inFolder.isChecked():
                for filename in os.listdir(folder):
                    if filename.lower().endswith(
                        (".png", ".jpg", ".jpeg", ".tif", ".tiff")
                    ) and filename.lower().startswith("edges"):
                        print(filename)
                        file_suffix = re.split("\\.", filename)[-1]
                        image_path = os.path.join(folder + "\\Edges." + file_suffix)
                        break

            elif convertUI.qtvar_convertImages_edgesRadio_selected.isChecked():
                file_path = convertUI.qtvar_convertImages_inputEdgesFile.text()
                if file_path.lower().endswith(
                    (".png", ".jpg", ".jpeg", ".tif", ".tiff")
                ):
                    image_path = file_path

            (
                edges_position,
                edges_no,
                average_spaceing,
                stdev_spaceing,
                electrodes_positions,
                electrode_gaps_positions
            ) = self.detect_edges(
                image_file=image_path,
                points_to_remove=points_to_remove,
                min_edge_spacing=min_edge_spacing,
                no_pixels_shift=no_pixels_shift,
                edge_orientation=edge_orientation,
                polynomial_deg=poly_deg,
            )

            # Verify if the file has the right name, and is indeed a file
            relativeCM_values = []
            relativeCM_errors = []
            frequencies = []

            for filename in os.listdir(folder + "\\_DATA"):
                if filename.lower().endswith(
                    (".png", ".jpg", ".jpeg", ".tif", ".tiff")
                ):
                    image_file = os.path.join(folder + "\\_DATA", filename)
                    bkg_file = os.path.join(folder + "\\_BKG", filename)
                    if os.path.isfile(image_file) and filename.startswith("OpenDEP"):
                        # Get the grayness factor for each image
                        (
                            x,
                            norm_image_averages,
                            image_averages,
                            _bkg_averages,
                            image_float,
                            grayness_factor,
                            grayness_errors,
                        ) = self.convert_image_to_CM(
                            image=image_file,
                            background_image=bkg_file,
                            edges_position=edges_position,
                            points_to_remove=points_to_remove,
                            edge_orientation=edge_orientation,
                            edge_width=edge_width,
                            bkg_area_width=bkg_area_width,
                            grayness_over_brightness=grayness_over_brightness,
                            bkg_separated=bkg_separated,
                        )

                        # Get the associated frequency for each grayness factor
                        frequency = re.split("_|Hz", filename)
                        frequencies.append(float(frequency[1]))
                        relativeCM_values.append(grayness_factor)
                        relativeCM_errors.append(grayness_errors)

                        # Create the plots for the processed images
                        figure, axis = plt.subplots(2, 2, figsize=(13.5, 9))

                        axis[0, 0].imshow(image_float)
                        for i in edges_position:
                            axis[0, 0].axvline(
                                i + points_to_remove,
                                color="black",
                                linestyle="--",
                                linewidth=0.5,
                            )
                        axis[0, 0].set_title("Image")

                        axis[0, 1].plot(_bkg_averages)
                        for i in edges_position:
                            axis[0, 1].axvline(
                                i, color="black", linestyle="--", linewidth=0.5
                            )
                        axis[0, 1].set_title("Background")

                        axis[1, 0].plot(x, image_averages)
                        for i in edges_position:
                            axis[1, 0].axvline(
                                i, color="black", linestyle="--", linewidth=0.5
                            )
                        axis[1, 0].set_title("Raw")

                        axis[1, 1].plot(x, norm_image_averages)
                        for i in edges_position:
                            axis[1, 1].axvline(
                                i, color="black", linestyle="--", linewidth=0.5
                            )
                        axis[1, 1].set_title("Background removed")

                        plt.savefig(
                            os.path.join(folder, "_PROCESSED\\figure-" + filename)
                        )
                        plt.close("all")

            # Sort the frequencies and grayness_factors (called also relative CM values)
            frequencies = np.array(frequencies)
            relativeCM_values = np.array(relativeCM_values)
            relativeCM_errors = np.array(relativeCM_errors)
            sort = frequencies.argsort()
            frequencies = frequencies[sort]
            relativeCM_values = relativeCM_values[sort]
            relativeCM_errors = relativeCM_errors[sort]

            print(frequencies)
            print(relativeCM_values)
            print(relativeCM_errors)

            # Make the xlsx centralization file
            instanced_data = Data()
            wb = Workbook()
            ws = wb.active
            ws["A1"] = "Frequency (Hz)"
            ws["B1"] = "Experimental grayness factor"
            ws["C1"] = "Experimental grayness factor errors"
            instanced_data.autoStretchColumns(ws)
            instanced_data.setBackgroundColor(
                ws, top=1, bottom=1000, left=1, right=100, color="00EBF1DE"
            )
            instanced_data.setBackgroundColor(
                ws, top=1, bottom=1, left=1, right=3, color="00C4D79B"
            )
            instanced_data.setBorder(
                ws,
                top=1,
                bottom=1,
                left=1,
                right=3,
                color="000000",
                border_style="thick",
            )

            x = 1
            for i in range(0, len(frequencies)):
                ws.cell(row=i + 2, column=1).value = frequencies[i]
                ws.cell(row=i + 2, column=2).value = relativeCM_values[i]
                ws.cell(row=i + 2, column=3).value = relativeCM_errors[i]
                x = x + 1

            instanced_data.setBorder(
                ws,
                top=2,
                bottom=len(frequencies) + 1,
                left=1,
                right=3,
                color="000000",
                border_style="double",
            )
            instanced_data.setTabelBackground(
                ws,
                top=2,
                bottom=len(frequencies) + 1,
                left=1,
                right=3,
                color1="00C0C0C0",
                color2="00FFFFFF",
            )

            wb.save(folder + "\\" + centrfile + ".xlsx")

            # Load data_01 to main window
            data.loadExcelData(folder + "\\" + centrfile + ".xlsx")
            mainUI.loadData()

            # Setting status in UI to finished
            convertUI.success = True

        except:
            convertUI.success = False
            print("[ERROR] [CONVERSION] Conversion of sample images could not compute")
