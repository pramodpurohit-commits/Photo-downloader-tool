import streamlit as st
import pandas as pd
import requests
import io
import zipfile
from datetime import datetime
from PIL import Image, ImageFilter

# --- 1. Set up the Web Page Layout ---
st.set_page_config(page_title="Team Photo Downloader", page_icon="📸", layout="centered")
st.title("📸 Bulk Photo Tools")

# --- 2. Shared Image Processing Logic ---
def process_image(image_bytes):
    """
    Opens image bytes, checks size, upscales using Lanczos, applies sharpening, 
    and saves with max quality settings.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
        
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        width, height = img.size
        min_dimension = 1000

        if width < min_dimension or height < min_dimension:
            scale_factor = min_dimension / min(width, height)
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)
            
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=150))
        
        output_buffer = io.BytesIO()
        img.save(output_buffer, format="JPEG", quality=100, subsampling=0)
        return output_buffer.getvalue()

    except Exception as e:
        return image_bytes

def load_dataframe(file):
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

# --- 3. Create Tabs for the UI ---
tab1, tab2 = st.tabs(["📥 Download from Excel Links", "🖥️ Enlarge Local Photos"])

# ==========================================
# TAB 1: EXISTING EXCEL DOWNLOADER
# ==========================================
with tab1:
    st.write("Upload an Excel/CSV file. Images smaller than 1000px will be sharpened and enlarged.")
    uploaded_file = st.file_uploader("Choose your Excel or CSV file", type=['csv', 'xlsx', 'xlsm', 'xlsb'], key="excel_uploader")
    column_name = st.text_input("Enter the Column Name containing the links", value="Image Links")

    if st.button("Start Link Download", key="btn_links"):
        if uploaded_file is None:
            st.warning("Please upload an Excel/CSV file first.")
        else:
            df = load_dataframe(uploaded_file)
            if df is not None:
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
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    
                    st.download_button(
                        label="Download ZIP File",
                        data=zip_buffer,
                        file_name=f"Downloaded_Photos_{timestamp}.zip",
                        mime="application/zip",
                        key="dl_links"
                    )

# ==========================================
# TAB 2: NEW LOCAL PHOTO ENLARGER
# ==========================================
with tab2:
    st.write("Select multiple photos from your computer. They will be enlarged to at least 1000px and sharpened.")
    
    # Accept multiple files
    local_photos = st.file_uploader("Select photos to enlarge", type=['jpg', 'jpeg', 'png', 'webp'], accept_multiple_files=True, key="photo_uploader")
    
    if st.button("Process Local Photos", key="btn_local"):
        if not local_photos:
            st.warning("Please select at least one photo.")
        else:
            total = len(local_photos)
            progress_bar = st.progress(0)
            status_text = st.empty()
            zip_buffer = io.BytesIO()
            
            success_count = 0
            
            with zipfile.ZipFile(zip_buffer, "w") as zf:
                for i, photo_file in enumerate(local_photos):
                    status_text.text(f"Processing {i+1} of {total}: {photo_file.name}")
                    
                    # Read the bytes of the uploaded file
                    photo_bytes = photo_file.getvalue()
                    
                    # Run it through our shared upscale/sharpen logic
                    processed_bytes = process_image(photo_bytes)
                    
                    # Keep original filename, force .jpg extension since we save as JPEG
                    base_name = photo_file.name.rsplit('.', 1)[0]
                    new_filename = f"{base_name}_enlarged.jpg"
                    
                    zf.writestr(new_filename, processed_bytes)
                    success_count += 1
                    
                    progress_bar.progress((i + 1) / total)
            
            status_text.text("Processing Complete!")
            st.success(f"Successfully enlarged {success_count} photos.")
            
            zip_buffer.seek(0)
            
            # Generate the dynamic folder name you requested
            current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            zip_filename = f"Enlarged Photos - {current_time}.zip"
            
            st.download_button(
                label="Download Enlarged Photos (ZIP)",
                data=zip_buffer,
                file_name=zip_filename,
                mime="application/zip",
                key="dl_local"
            )
