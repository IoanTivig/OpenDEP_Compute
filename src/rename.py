# ------------------------------------------------------
# ------------------- RENAME MODULE --------------------
# ------------------------------------------------------

# External imports #
import os
import re


"""
Rename functions:
Functions which renames and arranges microscopically acquired images.
Those will further be converted to CM factor values vs frequencies
"""


def auto_rename(folder, freq_list):
    count = 0
    file_list = os.listdir(folder)
    if len(file_list) == len(freq_list):
        for filename in file_list:
            if filename.lower().endswith((".png", ".jpg", ".jpeg", ".tif", "tiff")):
                suffix = re.split("\.", filename)
                src = os.path.join(folder + "/" + filename)
                new_name = f"OpenDEP_{int(freq_list[count])}Hz.{suffix[1]}"
                dst = dst = os.path.join(folder + "/" + new_name)

                if new_name not in file_list:
                    os.rename(src, dst)
                    count = count + 1
                else:
                    print("Files allready renamed")
                    break

    else:
        print("Frequencies count doesn't match image count")