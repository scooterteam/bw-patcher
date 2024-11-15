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

st.markdown("""### Disclaimer of Liability
The patcher provided here ("the Patcher") is offered "as is" without any warranties of any kind, including but not limited to warranties of accuracy, completeness, reliability, merchantability, fitness for a particular purpose, or non-infringement. Users of the Patcher are solely responsible for ensuring that their use complies with all applicable laws, including copyright and intellectual property laws related to third-party proprietary software.

**Notice on Third-Party Software:**  
If the Patcher or its output interacts with or modifies proprietary software owned by third parties, it is the user's responsibility to obtain the necessary permissions or licenses from the respective owners of such proprietary software. The authors and contributors of the Patcher disclaim any liability for legal consequences arising from such use.

### Non-Commercial Use

The Pacher and any outputs generated from its use are provided for non-commercial, educational purposes only. Any commercial use, including but not limited to selling, licensing, or incorporating the Patcher or its outputs into a commercial product, is strictly prohibited.

### Non-Endorsement

The use of the Patcher does not imply any affiliation with, endorsement by, or sponsorship by the owners of any third-party proprietary software with which the Patcher may interact. All trademarks, service marks, and company names are the property of their respective owners and are used solely for identification purposes. The authors and contributors of the Patcher do not claim any rights over the proprietary software owned by third parties.""")
