import streamlit as st
import pandas as pd
import pdfplumber
import re
import io
import zipfile

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

# Helper function to build a new filename from extracted data
def build_new_filename(data):
    """
    Returns a sanitized filename in the format:
    TAN_NatureOfPayment_Amount_DateOfPayment.pdf
    Falls back to the original filename if required fields are missing.
    """
    tan = data.get("TAN") or ""
    nature = data.get("Nature of Payment") or ""
    amount = (data.get("Amount (in Rs.)") or "").replace(",", "")
    date = data.get("Date of Deposit") or data.get("Tender Date") or ""

    if tan and nature and amount and date:
        # Sanitize date: "15-Jan-2024" → keep as-is (dashes are fine in filenames)
        new_name = f"{tan}_{nature}_{amount}_{date}.pdf"
        # Remove any characters not safe for filenames
        new_name = re.sub(r'[<>:"/\\|?*]', '_', new_name)
        return new_name

    # If any required field is missing, fall back to original name
    return data.get("Filename", "unknown.pdf")


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
    file_bytes_map = {}  # original filename → bytes, for ZIP creation
    # Progress bar for user feedback
    progress_bar = st.progress(0, text="Processing files, please wait...")

    for i, uploaded_file in enumerate(uploaded_files):
        with st.spinner(f"Processing: `{uploaded_file.name}`..."):
            file_bytes = uploaded_file.read()
            file_bytes_map[uploaded_file.name] = file_bytes
            # Reset pointer so pdfplumber can read the file
            uploaded_file.seek(0)
            data = extract_data_from_pdf(uploaded_file)
            all_data.append(data)
        progress_bar.progress((i + 1) / len(uploaded_files), text=f"Processed: {uploaded_file.name}")

    progress_bar.empty() # Clear the progress bar after completion

    if all_data:
        st.success(f"✅ **Successfully processed {len(all_data)} files!**")

        # Compute suggested new filenames
        for data in all_data:
            data["Suggested Filename"] = build_new_filename(data)

        # Create a DataFrame from the extracted data
        df = pd.DataFrame(all_data)

        # Reorder columns: Filename, Suggested Filename, then all extracted fields
        field_keys = ["Filename", "Suggested Filename"] + list(patterns.keys())
        df = df[field_keys]

        # Display the extracted data in an interactive table
        st.subheader("📊 Extracted Data")
        st.dataframe(df)

        col1, col2 = st.columns(2)

        # CSV download
        csv_data = convert_df_to_csv(df)
        with col1:
            st.download_button(
                label="📥 Download Data as CSV",
                data=csv_data,
                file_name="extracted_challan_details.csv",
                mime="text/csv",
            )

        # ZIP download with renamed PDFs
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for data in all_data:
                original_name = data["Filename"]
                new_name = data["Suggested Filename"]
                if original_name in file_bytes_map:
                    zf.writestr(new_name, file_bytes_map[original_name])
        zip_buffer.seek(0)

        with col2:
            st.download_button(
                label="📦 Download Renamed PDFs as ZIP",
                data=zip_buffer,
                file_name="renamed_challans.zip",
                mime="application/zip",
            )
else:
    st.info("Upload PDF files to begin the extraction process.")
