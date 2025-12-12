import streamlit as st
import pandas as pd
import requests
import io
import zipfile

# --- 1. Set up the Web Page Layout ---
st.set_page_config(page_title="Team Photo Downloader", page_icon="📸")
st.title("📸 Bulk Photo Downloader")
st.write("Upload an Excel/CSV file containing image links, and I'll create a ZIP file for you.")

# --- 2. User Inputs ---
uploaded_file = st.file_uploader("Choose your Excel or CSV file", type=['csv', 'xlsx', 'xlsm', 'xlsb'])
column_name = st.text_input("Enter the Column Name containing the links", value="Image Links")

# --- 3. The Logic ---
def load_dataframe(file):
    """Load the uploaded file into a Pandas DataFrame."""
    try:
        if file.name.endswith('.csv'):
            return pd.read_csv(file)
        elif file.name.endswith('.xlsb'):
            return pd.read_excel(file, engine='pyxlsb')
        else:
            return pd.read_excel(file, engine='openpyxl')
    except Exception as e:
        st.error(f"Error reading file: {e}")
        return None

if st.button("Start Download"):
    if uploaded_file is None:
        st.warning("Please upload a file first.")
    else:
        df = load_dataframe(uploaded_file)
        
        if df is not None:
            # Check for column
            # Clean column names for comparison (strip spaces, lowercase)
            cols_clean = [c.strip().lower() for c in df.columns]
            target_clean = column_name.strip().lower()
            
            if target_clean not in cols_clean:
                st.error(f"Column '{column_name}' not found. Available columns: {list(df.columns)}")
            else:
                # Find the exact original column name
                original_col_name = df.columns[cols_clean.index(target_clean)]
                
                # Setup variables for progress bar
                links = df[original_col_name].dropna().tolist()
                total = len(links)
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Prepare a Memory Buffer for the Zip File
                # We build the ZIP in RAM, not on the hard drive
                zip_buffer = io.BytesIO()
                
                valid_count = 0
                error_count = 0

                with zipfile.ZipFile(zip_buffer, "w") as zf:
                    for i, url in enumerate(links):
                        status_text.text(f"Processing {i+1} of {total}: {url}")
                        
                        try:
                            # Basic validation
                            if not isinstance(url, str) or not url.startswith(('http:', 'https:')):
                                continue
                                
                            response = requests.get(url, timeout=10)
                            response.raise_for_status()
                            
                            # Guess filename
                            filename = f"image_{i+1:03d}.jpg" # Default
                            if "png" in response.headers.get("Content-Type", ""):
                                filename = f"image_{i+1:03d}.png"
                            
                            # Write image data into the ZIP file in memory
                            zf.writestr(filename, response.content)
                            valid_count += 1
                            
                        except Exception as e:
                            error_count += 1
                        
                        # Update progress bar
                        progress_bar.progress((i + 1) / total)

                # --- 4. Final Download Button ---
                status_text.text("Done!")
                st.success(f"Processed {total} links. Success: {valid_count}, Errors: {error_count}")
                
                # Reset pointer of the memory buffer to the beginning
                zip_buffer.seek(0)
                
                st.download_button(
                    label="Download ZIP File",
                    data=zip_buffer,
                    file_name="downloaded_photos.zip",
                    mime="application/zip"
                )