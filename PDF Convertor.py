import pypandoc
import os
import glob

os.chdir("C:\Users\MetodejCerny\Downloads")

def pdf_to_word(pdf_file_name):
    # Check if the file exists
    if not os.path.isfile(pdf_file_name):
        print(f"The file '{pdf_file_name}' does not exist.")
        return

    # Define the output file name
    word_file_name = pdf_file_name.replace(".pdf", ".docx")

    try:
        # Convert PDF to Word
        output = pypandoc.convert_file(pdf_file_name, 'docx', outputfile=word_file_name)
        print(f"Conversion successful! '{pdf_file_name}' has been converted to '{word_file_name}'.")
    except Exception as e:
        print(f"An error occurred during conversion: {e}")


if __name__ == "__main__":
    # Define part of the file name to search for
    partial_file_name = 'Technical_Report_AB01_afrr_SUSICE (2).pdf'

    # Search for PDF files matching the partial name
    matching_files = glob.glob(f"*{partial_file_name}*.pdf")

    if matching_files:
        pdf_file_name = matching_files[0]  # Use the first match found
        print(f"Found PDF file: {pdf_file_name}")
        pdf_to_word(pdf_file_name)
    else:
        print(f"No PDF file found with name containing '{partial_file_name}'.")
