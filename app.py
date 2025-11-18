from bwpatcher.utils import patch_firmware
from bwpatcher.modules import ALL_MODULES
from io import BytesIO
import streamlit as st


title = "Brightway Firmware Patcher"
st.set_page_config(
    page_title=title,
    page_icon="🛴",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom CSS for cleaner styling
st.markdown("""
<style>
    /* Hide default Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Better spacing */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 800px;
    }

    /* Streamlined headers */
    h1 {
        text-align: center;
        margin-bottom: 0.5rem;
    }

    h2, h3 {
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# MANDATORY DISCLAIMER - Must be accepted before using the tool
if 'disclaimer_accepted' not in st.session_state:
    st.session_state.disclaimer_accepted = False

if not st.session_state.disclaimer_accepted:
    st.title("⚠️ LEGAL DISCLAIMER - READ CAREFULLY")

    st.error("**You must read and accept this disclaimer before using this tool.**")

    st.markdown("""
    ## Educational and Research Use Only

    **This tool is for EDUCATIONAL and RESEARCH purposes only.**

    ### 🔓 Our Principles

    **You own what you buy.** This tool helps you understand and modify devices you own.
    However, modifications may be dangerous and illegal.

    ### ⚠️ Safety Warnings

    **Modifying device firmware:**
    - May void your warranty
    - May violate local laws and regulations
    - Can bypass manufacturer safety features - **serious injury risk**
    - Modified devices may be illegal to operate
    - **YOU assume ALL liability** for injuries, accidents, and legal consequences

    ### 🚫 No Commercial Use

    - This software is **CC-BY-NC-SA licensed**
    - Commercial use is **strictly prohibited**
    - You may NOT sell modified firmware, patching services, or derivative tools

    ### 📋 No Warranty

    - Provided **AS-IS** with no guarantees
    - Authors accept **NO LIABILITY** for any consequences
    - You are solely responsible for compliance with all laws

    ### 📄 Full Terms

    See [LEGAL_DISCLAIMER.md](https://github.com/scooterteam/bw-flasher/blob/main/bw-patcher/LEGAL_DISCLAIMER.md)
    and [PRINCIPLES.md](https://github.com/scooterteam/bw-flasher/blob/main/bw-patcher/PRINCIPLES.md) for complete terms.

    ---

    **By clicking "I Understand & Accept All Risks", you acknowledge:**
    - You have read and understood this disclaimer
    - You accept all risks and responsibilities
    - You will use this tool legally and responsibly
    - You will not use this tool for commercial purposes
    """)

    col1, col2 = st.columns(2)

    with col1:
        if st.button("❌ I Do Not Accept - Exit", use_container_width=True, type="secondary"):
            st.error("You must accept the disclaimer to use this tool.")
            st.stop()

    with col2:
        if st.button("✅ I Understand & Accept All Risks", use_container_width=True, type="primary"):
            st.session_state.disclaimer_accepted = True
            st.rerun()

    st.stop()

# Header (only shown after disclaimer is accepted)
st.title("🛴 Brightway Firmware Patcher")
st.caption("Research tool for firmware analysis")

# Collapsible reference to full disclaimer
with st.expander("⚖️ View Legal Disclaimer Again"):
    st.markdown("""
    See [LEGAL_DISCLAIMER.md](https://github.com/scooterteam/bw-flasher/blob/main/bw-patcher/LEGAL_DISCLAIMER.md)
    for complete legal terms. By using this tool, you accept all risks and responsibilities.
    """)

st.divider()

# Single column layout
st.subheader("📁 Upload Firmware")
uploaded_file = st.file_uploader(
    "Choose your .bin firmware file",
    type=["bin"]
)

st.subheader("🛴 Scooter Model")
scooter_model = st.selectbox(
    "Select your model",
    ALL_MODULES
)

if uploaded_file and scooter_model:
    st.success(f"Ready to configure patches for {scooter_model}")

st.divider()

# Patches section
st.subheader("🔧 Configure Patches")

patches = []

# Speed limit patches
if st.checkbox('Speed Limit Sport (SLS)'):
    sls_speed = st.slider("Max Speed (SLS)", 1.0, 35.0, 25.0, 0.1)
    patches.append(f'sls={sls_speed}')

if st.checkbox('Speed Limit Drive (SLD)'):
    sld_speed = st.slider("Max Speed (SLD)", 1.0, 35.0, 15.0, 0.1)
    patches.append(f'sld={sld_speed}')

if scooter_model in ['mi5elite']:
    if st.checkbox('Speed Limit Pedestrian (SLP)'):
        slp_speed = st.slider("Max Speed (SLP)", 1.0, 35.0, 6.0, 0.1)
        patches.append(f'slp={slp_speed}')

if scooter_model in ['mi4', 'ultra4']:
    if st.checkbox('Dashboard Max Speed (DMS)'):
        dms_speed = st.slider("Max Speed (DMS)", 1.0, 29.6, 22.0, 0.1)
        patches.append(f'dms={dms_speed}')

if scooter_model not in ["mi4pro2nd", "mi5pro", "mi5elite"]:
    if st.checkbox('Fake Firmware Version (FDV)'):
        fdv_version = st.text_input("Firmware Version (4 digits)", value="0000", max_chars=4)
        if len(fdv_version) == 4 and fdv_version.isdigit():
            patches.append(f"fdv={fdv_version}")

if scooter_model not in ["mi5elite"]:
    if st.checkbox('Cruise Control Enable (CCE)'):
        patches.append("cce")

if scooter_model not in ["mi4", "mi4lite"]:
    if st.checkbox('Motor Start Speed (MSS)'):
        mss_speed = st.slider("Motor Start Speed (MSS)", 1.0, 9.0, 5.0, 0.1)
        patches.append(f"mss={mss_speed}")


# Summary and action section
st.divider()

if patches:
    st.info(f"{len(patches)} patch(es) selected")
else:
    st.info("No patches selected")

if uploaded_file is not None and patches:
    if patches[-1] != "chk":
        patches.append("chk")

    # Process button
    if st.button("Apply Patches", type="primary", use_container_width=True):
        with st.spinner("Applying patches..."):
            # Read the uploaded file into memory
            input_firmware = uploaded_file.read()

            # Apply the selected patches
            try:
                patched_firmware = patch_firmware(scooter_model, input_firmware, patches)
                st.success("Patching complete!")

                # Provide download button
                st.download_button(
                    label="Download Patched Firmware",
                    data=BytesIO(patched_firmware),
                    file_name=f"patched_{scooter_model}_firmware.bin",
                    mime="application/octet-stream",
                    type="primary",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"Patching failed: {str(e)}")

elif uploaded_file is None:
    st.warning("Please upload a firmware file")
elif not patches:
    st.warning("Please select at least one patch")

# Footer
st.divider()
st.caption("For educational and research purposes only • CC-BY-NC-SA 4.0 • See LEGAL_DISCLAIMER.md")
