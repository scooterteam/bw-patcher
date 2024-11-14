import streamlit as st
from bwpatcher.utils import SignatureException
from io import BytesIO
from importlib import import_module

# App title
st.title('Brightway Firmware Patcher')

# Description
st.markdown("""
This app allows you to patch the firmware for Brightway scooters.
You can apply several patches, such as removing the speed limit in Sport mode or changing the maximum speed on the dashboard.
""")

# Upload firmware file
st.subheader('Upload Firmware File')
uploaded_file = st.file_uploader("Choose a firmware file...", type=["bin"])

# Select scooter model
st.subheader('Select Scooter Model')
scooter_model = st.selectbox('Choose the model of your scooter', ['mi4', 'mi4pro2nd', 'ultra4'])

patch_map = {
    "rsls": lambda patcher: patcher.remove_speed_limit_sport,
    "dms": lambda patcher: patcher.dashboard_max_speed,
    "sld": lambda patcher: patcher.speed_limit_drive,
    "rfm": lambda patcher: patcher.region_free,
    "chk": lambda patcher: patcher.fix_checksum,
}

# Choose patches to apply
st.subheader('Select Patches')
patches = []

if scooter_model in ['mi4', 'mi4pro2nd']:
    if st.checkbox('Remove Speed Limit Sport (RSLS)'):
        patches.append('rsls')

if scooter_model in ['mi4', 'ultra4']:
    if st.checkbox('Dashboard Max Speed (DMS)'):
        dms_speed = st.slider("Max Speed (DMS)", 1.0, 29.6, 22.0)
        patches.append(f'dms={dms_speed}')

if scooter_model in ['mi4']:
    if st.checkbox('Speed Limit Drive (SLD)'):
        sld_speed = st.slider("Max Speed (SLD)", 1.0, 25.5, 25.5)
        patches.append(f'sld={sld_speed}')

if scooter_model in ['mi4pro2nd']:
    if st.checkbox('Region-Free (RFM)'):
        patches.append('rfm')

# Function to apply patches directly using bwpatcher
def apply_patch(model, infile, patches):
    if scooter_model == 'mi4pro2nd':
        patches.append('chk')  # always include checksum fix for 4pro2nd

    module = import_module(f"bwpatcher.modules.{model}")
    patcher_class = getattr(module, f"{model.capitalize()}Patcher")
    patcher = patcher_class(infile)

    for patch in patches:
        res = None
        try:
            if '=' in patch:
                patch, value = patch.split('=')
                value = float(value)

                res = patch_map[patch](patcher)(value)
            else:
                res = patch_map[patch](patcher)()
            print(res)
        except SignatureException:
            print(f"{patch.upper()} can't be applied")
        output = patcher.data
    return None, output  # No error, return the patched firmware data

# Process and download
if uploaded_file is not None and patches:
    # Read the uploaded file into memory
    input_firmware = uploaded_file.read()

    # Apply the selected patches
    error_message, patched_firmware = apply_patch(scooter_model, input_firmware, patches)

    # Display success or error message
    if error_message:
        st.error(f"Error: {error_message}")
    else:
        st.success("Patching complete!")

        # Provide the user with a link to download the patched firmware
        st.download_button(
            label="Download Patched Firmware",
            data=BytesIO(patched_firmware),
            file_name="patched_firmware.bin",
            mime="application/octet-stream"
        )

elif uploaded_file is None:
    st.warning("Please upload a firmware file.")

elif not patches:
    st.warning("Please select at least one patch to apply.")
