import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import random


def add_plot(data_frame, ax, shift=0):
    try:
        color = data_frame.iat[1, 1 + shift]
        res = tuple(map(int, color.split(', ')))
        res = list(res)
        for i in range(0, len(res)):
            res[i] = 1 / 244 * res[i]
        color = tuple(res)

    except:
        color = (random.uniform(0.1, 1), random.uniform(0.1, 1), random.uniform(0.1, 1))

    name = data_frame.iat[0, 1 + shift]

    x_exp = []
    ymin_exp = []
    ymax_exp = []

    x_fit = []
    y_fit = []

    status = "Experimental"
    for row in data_frame.itertuples():
        try:
            if row[1] == "End Experimental":
                status = "Fitted"
            elif row[1] == "End Fitted":
                status = "Finished"
            elif pd.isna(row[1 + shift]):
                continue
            elif status == "Experimental":
                x_exp.append(float(row[1 + shift]))
                ymin_exp.append(float(row[2 + shift]) - float(row[3 + shift]))
                ymax_exp.append(float(row[2 + shift]) + float(row[3 + shift]))
            elif status == "Fitted":
                x_fit.append(float(row[1 + shift]))
                y_fit.append(float(row[2 + shift]))
            elif status == "Finished":
                break

        except:
            continue

    print('========')
    print(x_exp)
    print(ymin_exp)
    print(ymax_exp)
    print('========')
    print(x_fit)
    print(y_fit)

    ax.set_xscale("log")


    ax.plot(x_fit, y_fit, color=color + (1,), label=name, linewidth=3)
    ax.fill(np.append(x_exp, x_exp[::-1]), np.append(ymin_exp, ymax_exp[::-1]), color=color + (0.25,))


df = pd.read_excel("Data.xlsx")
fig, ax = plt.subplots(figsize=(6.8,5))


sample_no = int(np.floor(len(df.columns)/3))
print(sample_no)
for i in range(0, sample_no):
    shift = i * 3
    add_plot(df, ax, shift=shift)

#ax.set_title('DC3F 800 microS/cm', size=14, y=1.025)
#plt.legend(fontsize=16)
#plt.xlabel('Frequency (Hz)', fontsize=16)
#plt.ylabel('CM factor', fontsize=16)
plt.grid(color='lightgrey', linestyle='--', linewidth=1.5)
plt.xticks(fontsize=14, weight='bold')
plt.yticks([-1, -0.5, 0, 0.5, 1], fontsize=16, weight='bold')


plt.savefig('Basic.png', dpi=300)
plt.show()
