#Marek Bistricky, Nano Energies
#March 2023
#This code serves as an evaluation tool of certification measurements for ancillary services @ Nano Energies

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import math
import statistics as stc
import openpyxl
from openpyxl import load_workbook
from pandas import DataFrame
import random

#NECESSARY INPUT------------------------------------------------------------------

#enter !EXCEL LINE! where the 2nd command took place - t2 limit vertical line - 2nd command, DOWN for mFRR+ and UP for mFRR-
#ramp_second_command_t2 = 1995; #B
#ramp_second_command_t2 = 2072; #A
#ramp_second_command_t2 = 2102
#ramp_second_command_t2 = 2032
ramp_second_command_t2 = 2012
#ramp_second_command_t2 = 1562 #mFRR5
excel_name = 'DES_data_DES_ČEPS CERT_CEPS_aFRRn_2025-10-25_Meryden_Stonava.xlsx'
battery = 0
#excel_name = ('DES_AB1_BESS_20_MW.xlsx')

#tolerance_coef = 0.14 #old tolerance coefficient not valid since 1.1.2023
tolerance_coef = 0.15

#----------------------------------------------------------------------------------

excel_source = pd.read_excel(excel_name)
support_excel_load = load_workbook(excel_name, data_only=True)

#print(excel_source.shape)
#print(excel_source.columns)

P_skut = excel_source['PSKUT_AB (MW)']
exact_date_time = excel_source['Date']
P_cil = excel_source['aFRRZADDA± (MW)']
P_lim_minus = excel_source['Lower limit (MW)']
P_lim_plus = excel_source['Upper limit (MW)']
if battery == 1:
    Soc = excel_source['SoC (%)']

# Define the ramp parameters
upper_intercept = 0.1
upper_slope = 0.05
lower_intercept = -0.1
lower_slope = -0.05

'''
upper_limit = P_lim_plus
lower_limit = P_lim_minus

# Calculate the limits using the ramp function
for x in range(1, excel_source.shape[0]):
    upper_limit[x] = upper_intercept + (upper_slope * P_cil[x])
    lower_limit[x] = lower_intercept + (lower_slope * P_cil[x])
    print(x)

# Add the calculated limits to the DataFrame
P_lim_minus = upper_limit
P_lim_plus = lower_limit
'''

fig, ax = plt.subplots()

plt.plot(P_skut, color = 'b', linewidth = '2', label =r'$ P_{SKUT,AB}\ (MW) $')
plt.plot(P_cil, color = 'r', label = r'$ aFRR_{zad}\ (MW) $', linewidth = '2')
plt.plot(P_lim_minus, label = r'$ lim- $')
plt.plot(P_lim_plus, label = r'$ lim+ $')
plt.xlim(0, excel_source.shape[0]+100)
plt.ylim(min(P_lim_minus)-0.4, max(P_lim_plus)+0.4)

#plt.yticks(np.arange(round( min(P_lim_minus)-0.4, 0), round(max(P_lim_plus)+0.4, 0), step=0.1))

ax.legend(loc='upper center', bbox_to_anchor=(0.5, 0.1), fancybox=True, shadow=True, ncol=5)
#plt.title('Test $ aFRR+ $ = 10 (MW)')
plt.title(r'$ Průběh\ testu\ aFRR+\ -\ grafy:\ P_{cíl}\ =\ P_{DG}\ ±\ aFRR_{ZAD}\ =\ f(t);\ PSKUT\ =\ f(t) $')
plt.xlabel(r'$ Čas\ [s]$')
plt.ylabel(r'$Výkon\ [MW]$')

plt.show()

font_size = 15
font = {'family': 'DejaVu Sans',
        'weight': 'bold',
        'size': font_size}

font2 = {'family': 'DejaVu Sans',
         'weight': 'normal',
         'size': font_size}

font3 = {'family' : 'DejaVu Sans',
        'weight' : 'normal',
        'size'   : font_size-5}

if battery==1:
    fig, ax = plt.subplots()
    plt.xlabel('Čas [s]', **font2)
    plt.ylabel('SoC [%]', **font2)

    plt.xlim(0, excel_source.shape[0]+100)
    plt.ylim(-10, 110)

    plt.plot(Soc, color = 'b', linewidth = '2', label ='SoC (%)')
    plt.hlines(y=10, xmin=0, xmax=11800, color='#000000')
    plt.text(50,11, 'SoC_D', **font3)
    plt.hlines(y=90, xmin=0, xmax=11800, color='#000000')
    plt.text(50,91, 'SoC_H', **font3)
    plt.title('SoC = f(t)')

    # Shrink current axis's height by 10% on the bottom
    box = ax.get_position()
    ax.set_position([box.x0, box.y0 + box.height * 0.05, box.width, box.height * 0.95])

    # Put a legend below current axis
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1), fancybox=True, shadow=True, ncol=5)

    plt.xticks(np.arange(0, excel_source.shape[0]+100, step=600), **font2)
    plt.yticks(np.arange(-10, 110, step=5), **font2)

    plt.rc('font', **font)

    plt.show()


#df = DataFrame({'P_skut':P_skut})

#df.to_excel('pskut_new.xlsx', sheet_name='Sheet1', header=True, index=False)

#P_dg = excel_source['PDG_AB (MW)'][1]
#G_av = excel_source['GV_AB']

#print("P_cil+P_dg=",P_cil+P_dg)
#print("P_skut=",round(P_skut[804],2))


#P_dov = min(5, tolerance_coef * P_cil)
#t2_plus_12_5 = ramp_second_command_t2 + ramp_length

#beginning_t0 = next((x + 1 for x in range(excel_source.shape[0] - 1) if not math.isnan(P_skut[x]) and not math.isnan(P_skut[x + 1]) and test_time[x] == 1), None)

#prifazovani = next((x + 1 for x in range(excel_source.shape[0] - 1) if not math.isnan(P_skut[x]) and not math.isnan(P_skut[x + 1]) and x > 2 and abs(P_skut[x] - P_skut[x - 1]) > 0 and abs(G_av[x] - G_av[x - 1]) > 0), 1000)

#reached_P_cil_t1 = next((x + 1 for x in range(excel_source.shape[0] - 1) if not math.isnan(P_skut[x]) and not math.isnan(P_skut[x + 1]) and round(P_skut[x], 2) == round(P_dg + P_cil, 2) and test_time[x] <= ramp_length + 60), ramp_length + 61)

#t0_plus_12_5 = next((x + 1 for x in range(excel_source.shape[0] - 1) if not math.isnan(P_skut[x]) and not math.isnan(P_skut[x + 1]) and test_time[x] == ramp_length + 1), None)

#trial_time = next((x + 1 for x in range(excel_source.shape[0] - 1) if not math.isnan(P_skut[x]) and not math.isnan(P_skut[x + 1]) and first_column[x].fill.start_color.index == 'FFFF0000'), None)

#if P_dg == 0:
 #   reached_P_dg_t3 = next((x + 1 for x in range(excel_source.shape[0] - 1) if not math.isnan(P_skut[x]) and not math.isnan(P_skut[x + 1]) and test_time[x] > ramp_second_command_t2 and P_skut[x] == P_dg and abs(G_av[x] - G_av[x - 1]) > 0), None)
#elif P_dg < 0:
#    reached_P_dg_t3 = next((x + 1 for x in range(excel_source.shape[0] - 1) if not math.isnan(P_skut[x]) and not math.isnan(P_skut[x + 1]) and test_time[x] > ramp_second_command_t2 and P_skut[x] <= P_dg), None)
#else:
 #   reached_P_dg_t3 = next((x + 1 for x in range(excel_source.shape[0] - 1) if not math.isnan(P_skut[x]) and not math.isnan(P_skut[x + 1]) and ramp_second_command_t2 < test_time[x] < ramp_second_command_t2 + ramp_length + 1 and round(P_skut[x], 2) == P_dg), ramp_second_command_t2 + ramp_length)

#t4 = t2_plus_12_5 + (20 * 60) if P_dg != 0 else "Not relevant for Test A"

#t_akt = reached_P_cil_t1 - beginning_t0
#t_deakt = reached_P_dg_t3 - ramp_second_command_t2


