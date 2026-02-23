from datetime import datetime, timedelta
import openpyxl
import os

def generate_dates_in_excel_format(start_date, end_date, output_file):
    # Convert start_date and end_date strings to datetime objects
    start = datetime.strptime(start_date, "%d.%m.%Y %H:%M:%S")
    end = datetime.strptime(end_date, "%d.%m.%Y %H:%M:%S")

    # Create a new workbook and select the active worksheet
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "DateTime"

    # Add a header
    sheet.append(["DateTime (dd.MM.yyyy HH:mm:ss)"])

    # Generate date and time for each second from start to end
    current = start
    while current <= end:
        # Append each timestamp to the Excel sheet
        sheet.append([current.strftime("%d.%m.%Y %H:%M:%S")])
        current += timedelta(seconds=1)

    # Save the workbook to the specified file
    workbook.save(output_file)
    # Open the file automatically
    os.startfile(output_file)


# Define your minimum and maximum date
start_date = ("06.08.2025 12:43:50")
end_date = ("06.08.2025 15:43:50")

# Specify the output Excel file name
output_file = "GeneratedDates.xlsx"

# Generate and save the dates to the Excel file
generate_dates_in_excel_format(start_date, end_date, output_file)
