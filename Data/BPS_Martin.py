import pandas as pd
import matplotlib.pyplot as plt
import locale
import numpy as np

# Optional: set Czech locale for month names
try:
    locale.setlocale(locale.LC_TIME, 'cs_CZ.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_TIME, 'czech')
    except:
        print("Czech locale not available. Using default.")

# Load the Excel file
df = pd.read_excel("power_data.xlsx")

# Inspect column headers (for debugging)
print("Original columns:", df.columns)

# Select only the relevant columns (assumes Datetime is first, Power_kW is second)
df = df.iloc[:, :2]
df.columns = ['Datetime', 'Power_kW']

# Convert datetime column
df['Datetime'] = pd.to_datetime(df['Datetime'], format='%d.%m.%Y %H:%M')

# Single combined plot for all data
plt.figure(figsize=(18, 6))

# Bar plot
plt.bar(df['Datetime'], df['Power_kW'], width=0.03, align='center')

# Add red dashed line at 2500 kW
plt.axhline(y=2500, color='red', linestyle='--', linewidth=1.5, label='Pmax = 2500 kW')

# Plot formatting
plt.title("Biovatas Power Output", fontsize=16)
plt.xlabel("Date and Time")
plt.ylabel("Power [kW]")

# Y-axis ticks every 100 kW
min_y = max(0, int(df['Power_kW'].min() // 100) * 100)
max_y = int(df['Power_kW'].max() // 100 + 2) * 100
plt.yticks(np.arange(min_y, max_y + 1, 100))

plt.xticks(rotation=90)
plt.grid(axis='y')
plt.legend()
plt.tight_layout()
plt.show()
