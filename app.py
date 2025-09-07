import streamlit as st
import pandas as pd
import pdfplumber
import re
import io

# --- App Configuration ---
st.set_page_config(
    page_title="Tax Challan Extractor",
    page_icon="🧾",
    layout="wide",
)

# --- Core Extraction Logic (from your original script) ---
# This part remains mostly unchanged, as the logic is solid.

# Define regex patterns for each field
patterns = {
    "ITNS No.": r"ITNS No\. : (\d+)",
    "TAN": r"TAN : (\w+)",
    "Name": r"Name : (.+)",
    "Assessment Year": r"Assessment Year : (\d{4}-\d{2})",
    "Financial Year": r"Financial Year : (\d{4}-\d{2})",
    "Major Head": r"Major Head : (.+)",
    "Minor Head": r"Minor Head : (.+)",
    "Nature of Payment": r"Nature of Payment : ([\dA-Z]+)",
    "Amount (in Rs.)": r"Amount \(in Rs\.\) : ₹ ([\d,]+)",
    "Amount (in words)": r"Amount \(in words\) : (.+)",
    "CIN": r"CIN : (\w+)",
    "Mode of Payment": r"Mode of Payment : (.+)",
    "Bank Name": r"Bank Name : (.+)",
    "Bank Reference Number": r"Bank Reference Number : (\w+)",
    "Date of Deposit": r"Date of Deposit : (\d{2}-[A-Za-z]{3}-\d{4})",
    "BSR code": r"BSR code : (\d+)",
    "Challan No": r"Challan No : (\d+)",
    "Tender Date": r"Tender Date : (\d{2}/\d{2}/\d{4})",
    "Tax": r"A Tax ₹ ([\d,]+)",
    "Surcharge": r"B Surcharge ₹ ([\d,]+)",
    "Cess": r"C Cess ₹ ([\d,]+)",
    "Interest": r"D Interest ₹ ([\d,]+)",
    "Penalty": r"E Penalty ₹ ([\d,]+)",
    "Fee under section 234E": r"F Fee under section 234E ₹ ([\d,]+)",
    "Total": r"Total \(A\+B\+C\+D\+E\+F\) ₹ ([\d,]+)"
}

# Function to extract data from an uploaded PDF file object
def extract_data_from_pdf(uploaded_file):
    """
    Extracts data from a single uploaded PDF file using pdfplumber and regex.
    """
    data = {"Filename": uploaded_file.name} # Add filename for reference
    try:
        with pdfplumber.open(uploaded_file) as pdf:
            text = "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())
            for key, pattern in patterns.items():
                match = re.search(pattern, text)
                # Clean up the extracted value
                value = match.group(1).strip() if match else None
                data[key] = value
    except Exception as e:
        st.error(f"Error processing {uploaded_file.name}: {e}")
        # Fill the rest of the keys with an error message for this file
        for key in patterns.keys():
            if key not in data:
                data[key] = "Error"
    return data

# Helper function to convert DataFrame to CSV in memory for download
@st.cache_data
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')


# --- Streamlit User Interface ---

# Title and Description
st.title("🧾 Tax Challan Data Extractor")
st.markdown("""
Upload one or more tax challan PDFs (Form 280, 281, etc.) to automatically extract key details into a downloadable CSV file.
This tool helps streamline data entry and reconciliation.
""")
st.markdown("---")


# Sidebar for instructions and information
with st.sidebar:
    st.header("How to Use")
    st.info(
        """
        1. **Drag and drop** or click to upload your PDF challan files.
        2. The app will **automatically process** them.
        3. **Review** the extracted data in the table.
        4. Click the **Download CSV** button to get your results.
        """
    )
    st.warning("⚠️ **Note:** This tool works best with standard, text-based PDF challans. Scanned image-based PDFs may not work.")


# File Uploader
uploaded_files = st.file_uploader(
    "**Choose your challan PDF files**",
    type="pdf",
    accept_multiple_files=True,
    help="You can upload multiple files at once."
)

if uploaded_files:
    all_data = []
    # Progress bar for user feedback
    progress_bar = st.progress(0, text="Processing files, please wait...")

    for i, uploaded_file in enumerate(uploaded_files):
        with st.spinner(f"Processing: `{uploaded_file.name}`..."):
            data = extract_data_from_pdf(uploaded_file)
            all_data.append(data)
        progress_bar.progress((i + 1) / len(uploaded_files), text=f"Processed: {uploaded_file.name}")

    progress_bar.empty() # Clear the progress bar after completion

    if all_data:
        st.success(f"✅ **Successfully processed {len(all_data)} files!**")
        
        # Create a DataFrame from the extracted data
        df = pd.DataFrame(all_data)

        # Reorder columns to have Filename first
        field_keys = ["Filename"] + list(patterns.keys())
        df = df[field_keys]

        # Display the extracted data in an interactive table
        st.subheader("📊 Extracted Data")
        st.dataframe(df)

        # Provide a download button for the CSV
        csv_data = convert_df_to_csv(df)
        
        st.download_button(
            label="📥 Download Data as CSV",
            data=csv_data,
            file_name="extracted_challan_details.csv",
            mime="text/csv",
        )
else:
    st.info("Upload PDF files to begin the extraction process.")