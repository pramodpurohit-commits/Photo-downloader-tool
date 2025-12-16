import streamlit as st
import pandas as pd
import requests
import io
import zipfile
from PIL import Image, ImageFilter

# --- 1. Set up the Web Page Layout ---
st.set_page_config(page_title="Team Photo Downloader", page_icon="📸")
st.title("📸 Bulk Photo Downloader (High-Quality Upscale)")
st.write("Upload an Excel/CSV file. Images smaller than 1000px will be sharpened and enlarged.")

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

def process_image(image_bytes):
    """
    Opens image bytes, checks size, upscales using Lanczos, applies sharpening, 
    and saves with max quality settings.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
        
        # Convert to RGB to handle transparency/PNGs correctly for JPEG conversion
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        width, height = img.size
        min_dimension = 1000

        # Check if resizing is needed
        if width < min_dimension or height < min_dimension:
            # Calculate scale factor to make the SMALLEST side at least 1000
            scale_factor = min_dimension / min(width, height)
            
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)
            
            # 1. Resize using LANCZOS (Highest Quality Downsampling/Upsampling filter)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # 2. Apply Sharpening to combat the blur from upscaling
            # Radius=2, Percent=150 is a good starting point for upscaled web images
            img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=150))
        
        # Save back to bytes
        output_buffer = io.BytesIO()
        
        # 3. Save with Maximum Quality Settings
        # quality=100: Minimal compression
        # subsampling=0: Keeps all color information (4:4:4)
        img.save(output_buffer, format="JPEG", quality=100, subsampling=0)
        
        return output_buffer.getvalue()

    except Exception as e:
        # If processing fails, return original bytes as fallback
        return image_bytes

if st.button("Start Download"):
    if uploaded_file is None:
        st.warning("Please upload a file first.")
    else:
        df = load_dataframe(uploaded_file)
        
        if df is not None:
            # Clean column names for comparison
            cols_clean = [c.strip().lower() for c in df.columns]
            target_clean = column_name.strip().lower()
            
            if target_clean not in cols_clean:
                st.error(f"Column '{column_name}' not found. Available columns: {list(df.columns)}")
            else:
                original_col_name = df.columns[cols_clean.index(target_clean)]
                
                links = df[original_col_name].dropna().tolist()
                total = len(links)
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                zip_buffer = io.BytesIO()
                
                valid_count = 0
                error_count = 0

                with zipfile.ZipFile(zip_buffer, "w") as zf:
                    for i, url in enumerate(links):
                        status_text.text(f"Processing {i+1} of {total}: {url}")
                        
                        try:
                            if not isinstance(url, str) or not url.startswith(('http:', 'https:')):
                                continue
                                
                            response = requests.get(url, timeout=10)
                            response.raise_for_status()
                            
                            # Process the image (Upscale + Sharpen)
                            final_image_data = process_image(response.content)

                            filename = f"image_{i+1:03d}.jpg"
                            zf.writestr(filename, final_image_data)
                            valid_count += 1
                            
                        except Exception as e:
                            error_count += 1
                        
                        progress_bar.progress((i + 1) / total)

                status_text.text("Processing Complete!")
                st.success(f"Processed {total} links. Success: {valid_count}, Errors: {error_count}")
                
                zip_buffer.seek(0)
                
                st.download_button(
                    label="Download ZIP File",
                    data=zip_buffer,
                    file_name="enhanced_photos.zip",
                    mime="application/zip"
                )
