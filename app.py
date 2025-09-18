from bwpatcher.utils import patch_firmware
from bwpatcher.modules import ALL_MODULES
from io import BytesIO
import os
import streamlit as st
import requests

REPO = "scooterteam00bf/bw-patcher"

commit_sha = os.getenv("STREAMLIT_COMMIT_SHA")

with st.sidebar:
    st.title("BW Firmware Patcher")
    st.image("logo.png")
    st.title("📌 Last Git Commit")

    if commit_sha:
        url = f"https://api.github.com/repos/{REPO}/commits/{commit_sha}"
        r = requests.get(url)
        if r.status_code == 200:
            commit = r.json()["commit"]
            st.write(f"**SHA:** `{commit_sha}`")
            st.write(f"**Message:** {commit['message']}")
            st.write(f"**Author:** {commit['author']['name']}")
            st.write(f"**Date:** {commit['author']['date']}")
            st.write(f"[View on GitHub]({url.replace('api.github.com/repos', 'github.com')})")
        else:
            st.error("Could not fetch commit details from GitHub.")
    else:
        st.warning("Commit SHA not available in this environment.")


st.text("⬇️ Acknowledge disclaimer and scroll down for main app ⬇️")
st.warning("""### Disclaimer of Liability
The patcher provided here ("the Patcher") is offered "as is" without any warranties of any kind, including but not limited to warranties of accuracy, completeness, reliability, merchantability, fitness for a particular purpose, or non-infringement. Users of the Patcher are solely responsible for ensuring that their use complies with all applicable laws, including copyright and intellectual property laws related to third-party proprietary software.

**Notice on Third-Party Software:**  
If the Patcher or its output interacts with or modifies proprietary software owned by third parties, it is the user's responsibility to obtain the necessary permissions or licenses from the respective owners of such proprietary software. The authors and contributors of the Patcher disclaim any liability for legal consequences arising from such use.

### Non-Commercial Use

The Pacher and any outputs generated from its use are provided for non-commercial, educational purposes only. Any commercial use, including but not limited to selling, licensing, or incorporating the Patcher or its outputs into a commercial product, is strictly prohibited.

### Non-Endorsement

The use of the Patcher does not imply any affiliation with, endorsement by, or sponsorship by the owners of any third-party proprietary software with which the Patcher may interact. All trademarks, service marks, and company names are the property of their respective owners and are used solely for identification purposes. The authors and contributors of the Patcher do not claim any rights over the proprietary software owned by third parties.""")



title = "Brightway Firmware Patcher"
# Set the app title in the browser's tab
st.set_page_config(
    page_title=title,
    page_icon="🛴"
)

# App title
st.title(title)

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
scooter_model = st.selectbox('Choose the model of your scooter', ALL_MODULES)

# Choose patches to apply
st.subheader('Select Patches')
patches = []

if st.checkbox('Speed Limit Sport (SLS)'):
    sls_speed = st.slider("Max Speed (SLS)", 1.0, 39.5, 25.5, 0.1)
    patches.append(f'sls={sls_speed}')

if st.checkbox('Speed Limit Drive (SLD)'):
    sld_speed = st.slider("Max Speed (SLD)", 1.0, 39.5, 15.5, 0.1)
    patches.append(f'sld={sld_speed}')

if scooter_model in ['mi4', 'ultra4']:
    if st.checkbox('Dashboard Max Speed (DMS)'):
        dms_speed = st.slider("Max Speed (DMS)", 1.0, 29.6, 22.0, 0.1)
        patches.append(f'dms={dms_speed}')

if scooter_model not in ["mi4pro2nd", "mi5pro"]:
    if st.checkbox('Fake Firmware Version (FDV)'):
        fdv_version = st.text_input("Firmware Version (4 digits)", value="0000", max_chars=4)
        patches.append(f"fdv={fdv_version}")

if st.checkbox('Cruise Control Enable (CCE)'):
    patches.append("cce")

if scooter_model not in ["mi4", "mi4lite"]:
    if st.checkbox('Motor Start Speed (MSS)'):
        mss_speed = st.slider("Motor Start Speed (MSS)", 1.0, 9.0, 5.0, 0.1)
        patches.append(f"mss={mss_speed}")


# Process and download
if uploaded_file is not None and patches:
    if patches[-1] != "chk":
        patches.append("chk")

    # Read the uploaded file into memory
    input_firmware = uploaded_file.read()

    # Apply the selected patches
    patched_firmware = patch_firmware(scooter_model, input_firmware, patches)
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

