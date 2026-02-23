import pandas as pd

# Load the data from the Excel file
file_path = 'MVE Seč - Výkony - 23.xlsx'  # Replace with the actual file path
df = pd.read_excel(file_path)

# Filter the data to only include rows where MW/h > 0
output_above_zero = df[df['MW/h'] > 0]

# Get the unique hours where output was greater than 0
unique_hours = output_above_zero['Hour'].unique()

# Sort the hours for easier reading
unique_hours.sort()

# Print the hours where output was greater than 0
print("Hours with output greater than 0:")
for hour in unique_hours:
    print(f"Hour: {hour}")
