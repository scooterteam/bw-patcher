from bwpatcher.utils import patch_firmware
from bwpatcher.modules import ALL_MODULES
from bwpatcher import __version__
from io import BytesIO
import streamlit as st
from streamlit_scroll_to_top import scroll_to_here


LEQI_MODELS = ["mi5elite", "mi6", "mi6lite", "mi5plus"]
EXPERIMENTAL_MODELS = ["mi6", "mi6lite", "ultra4", "mi5plus"]

STABLE_MODULES = [m for m in ALL_MODULES if m not in EXPERIMENTAL_MODELS]

st.set_page_config(
    page_title="Brightway Firmware Patcher",
    page_icon="🛴",
    layout="centered",
    initial_sidebar_state="collapsed",
)

if st.session_state.get("scroll_to_top", False):
    st.session_state.scroll_to_top = False
    scroll_to_here(0, key="top")

st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=Space+Grotesk:wght@500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: "IBM Plex Sans", sans-serif;
    }

    #MainMenu, footer, header {visibility: hidden;}

    .stApp {
        background:
            radial-gradient(1100px 480px at 8% -8%, rgba(45, 140, 150, 0.16), transparent 55%),
            radial-gradient(800px 400px at 100% 0%, rgba(200, 120, 50, 0.08), transparent 50%),
            linear-gradient(180deg, #0e1110 0%, #121615 40%, #0f1312 100%);
        color: #e4e8e5;
    }

    .block-container {
        padding-top: 1.75rem;
        padding-bottom: 3rem;
        max-width: 720px;
    }

    h1, h2, h3 {
        font-family: "Space Grotesk", sans-serif !important;
        letter-spacing: -0.02em;
        color: #f2f5f3 !important;
    }

    h1 {
        font-size: 2.15rem !important;
        font-weight: 700 !important;
        margin-bottom: 0.25rem !important;
        line-height: 1.15 !important;
    }

    p, label, span, .stMarkdown, .stCaption {
        color: #c5ccc7;
    }

    .bw-brand {
        font-family: "Space Grotesk", sans-serif;
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        color: #6eb8b4;
        margin-bottom: 0.35rem;
    }

    .bw-sub {
        color: #9aa39c;
        font-size: 0.98rem;
        margin: 0 0 1.4rem 0;
        line-height: 1.45;
    }

    .bw-section {
        font-family: "Space Grotesk", sans-serif;
        font-size: 0.8rem;
        font-weight: 600;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #a8b2ab;
        margin: 1.6rem 0 0.55rem 0;
        padding-bottom: 0.35rem;
        border-bottom: 1px solid rgba(180, 200, 190, 0.12);
    }

    .bw-meta {
        display: flex;
        gap: 0.55rem;
        flex-wrap: wrap;
        align-items: center;
        margin: 1rem 0 0.75rem;
        font-size: 0.85rem;
    }

    .bw-chip {
        display: inline-block;
        padding: 0.18rem 0.55rem;
        border-radius: 999px;
        background: rgba(110, 184, 180, 0.14);
        color: #9fd4d0;
        font-size: 0.78rem;
        font-weight: 500;
    }

    .bw-foot {
        text-align: center;
        color: #6f7872;
        font-size: 0.82rem;
        margin-top: 2rem;
    }

    div[data-testid="stFileUploader"] section {
        border: 1.5px dashed rgba(140, 180, 170, 0.28) !important;
        background: rgba(255, 255, 255, 0.03) !important;
        border-radius: 12px !important;
    }

    .stButton > button[kind="primary"],
    .stDownloadButton > button[kind="primary"] {
        background: #2d7a76 !important;
        border: none !important;
        color: #f5f7f6 !important;
        font-family: "Space Grotesk", sans-serif !important;
        font-weight: 600 !important;
        letter-spacing: 0.01em;
        border-radius: 10px !important;
        padding: 0.55rem 1rem !important;
    }

    .stButton > button[kind="primary"]:hover,
    .stDownloadButton > button[kind="primary"]:hover {
        background: #3a9691 !important;
        color: #fff !important;
    }

    .stButton > button[kind="secondary"] {
        border-radius: 10px !important;
        border-color: rgba(180, 200, 190, 0.22) !important;
        background: rgba(255, 255, 255, 0.04) !important;
        color: #d5ddd7 !important;
    }

    div[data-testid="stExpander"] {
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(180, 200, 190, 0.1);
        border-radius: 12px;
    }

    .stAlert {
        border-radius: 10px !important;
    }

    /* Streamlit widgets on dark bg */
    [data-baseweb="select"] > div,
    .stTextInput input,
    .stNumberInput input {
        background-color: rgba(255, 255, 255, 0.05) !important;
        color: #e8ece9 !important;
    }

    .stSlider [data-baseweb="slider"] div[role="slider"] {
        background-color: #6eb8b4 !important;
    }
</style>
""",
    unsafe_allow_html=True,
)

if "disclaimer_accepted" not in st.session_state:
    st.session_state.disclaimer_accepted = False

if not st.session_state.disclaimer_accepted:
    st.markdown('<div class="bw-brand">Brightway</div>', unsafe_allow_html=True)
    st.title("Legal disclaimer")
    st.markdown(
        '<p class="bw-sub">Read and accept before using the firmware patcher.</p>',
        unsafe_allow_html=True,
    )

    st.error("You must accept this disclaimer before using this tool.")

    st.markdown(
        """
**Educational and research use only.** This tool helps you understand devices you own.
Modifications can be dangerous and illegal.

**Safety**
- May void warranty and violate local law
- Can bypass safety features — serious injury risk
- Modified devices may be illegal to operate
- You assume all liability

**License** — CC-BY-NC-SA 4.0 · commercial use prohibited

**Warranty** — provided as-is; authors accept no liability

Full terms: [LEGAL_DISCLAIMER.md](https://github.com/scooterteam/bw-flasher/blob/main/LEGAL_DISCLAIMER.md)
· [PRINCIPLES.md](https://github.com/scooterteam/bw-flasher/blob/main/bw-patcher/PRINCIPLES.md)
"""
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("I do not accept", use_container_width=True, type="secondary"):
            st.error("You must accept the disclaimer to use this tool.")
            st.stop()
    with col2:
        if st.button("I understand & accept all risks", use_container_width=True, type="primary"):
            st.session_state.disclaimer_accepted = True
            st.session_state.scroll_to_top = True
            st.rerun()

    st.markdown(f'<p class="bw-foot">v{__version__}</p>', unsafe_allow_html=True)
    st.stop()

st.markdown('<div class="bw-brand">Brightway</div>', unsafe_allow_html=True)
st.title("Firmware Patcher")
st.markdown(
    '<p class="bw-sub">Configure research patches for Brightway-based controllers.</p>',
    unsafe_allow_html=True,
)

with st.expander("Legal disclaimer"):
    st.markdown(
        """
See [LEGAL_DISCLAIMER.md](https://github.com/scooterteam/bw-flasher/blob/main/LEGAL_DISCLAIMER.md)
for complete terms. By using this tool, you accept all risks and responsibilities.
"""
    )

st.markdown('<p class="bw-section">Firmware & model</p>', unsafe_allow_html=True)

uploaded_file = st.file_uploader("Firmware file (.bin)", type=["bin"])

col_model, col_adv = st.columns([2, 1])
with col_model:
    experimental_mode = str(st.query_params.get("experimental", "")).lower() in (
        "1",
        "true",
        "yes",
    )
    available_models = list(STABLE_MODULES)
    if experimental_mode:
        available_models = sorted(set(available_models) | set(EXPERIMENTAL_MODELS))

    scooter_model = st.selectbox("Scooter model", available_models)
with col_adv:
    st.write("")
    st.write("")
    advanced_mode = st.checkbox(
        "Full dump",
        help="Patch a full memory dump, not DFU firmware.",
    )

if experimental_mode and scooter_model in EXPERIMENTAL_MODELS:
    st.warning(
        "Experimental model — patches may be incomplete or untested. Flashing can brick the scooter."
    )

st.markdown('<p class="bw-section">Speed limits</p>', unsafe_allow_html=True)

patches = []
n_speed = 3 if scooter_model in LEQI_MODELS else 2
speed_cols = st.columns(n_speed)

with speed_cols[0]:
    enable_sls = st.checkbox("Sport (SLS)")
    sls_speed = st.slider(
        "SLS km/h", 1.0, 35.0, 25.0, 0.1, disabled=not enable_sls, key="sls_val"
    )
    if enable_sls:
        patches.append(f"sls={sls_speed}")

with speed_cols[1]:
    enable_sld = st.checkbox("Drive (SLD)")
    sld_speed = st.slider(
        "SLD km/h", 1.0, 35.0, 15.0, 0.1, disabled=not enable_sld, key="sld_val"
    )
    if enable_sld:
        patches.append(f"sld={sld_speed}")

if scooter_model in LEQI_MODELS:
    with speed_cols[2]:
        enable_slp = st.checkbox("Walk (SLP)")
        slp_speed = st.slider(
            "SLP km/h", 1.0, 35.0, 6.0, 0.1, disabled=not enable_slp, key="slp_val"
        )
        if enable_slp:
            patches.append(f"slp={slp_speed}")

st.markdown('<p class="bw-section">Other patches</p>', unsafe_allow_html=True)

opt_a, opt_b = st.columns(2)

with opt_a:
    if scooter_model in ["mi4", "ultra4"]:
        enable_dms = st.checkbox("Dashboard max (DMS)")
        dms_speed = st.slider(
            "DMS km/h", 1.0, 29.6, 22.0, 0.1, disabled=not enable_dms, key="dms_val"
        )
        if enable_dms:
            patches.append(f"dms={dms_speed}")

    if scooter_model not in ["mi4pro2nd", "mi5pro", *LEQI_MODELS]:
        enable_fdv = st.checkbox("Fake firmware version (FDV)")
        fdv_version = st.text_input(
            "Version (4 digits)",
            value="0000",
            max_chars=4,
            disabled=not enable_fdv,
            key="fdv_val",
        )
        if enable_fdv and len(fdv_version) == 4 and fdv_version.isdigit():
            patches.append(f"fdv={fdv_version}")

with opt_b:
    if scooter_model not in LEQI_MODELS:
        if st.checkbox("Cruise control (CCE)"):
            patches.append("cce")

    if scooter_model not in ["mi4", "mi4lite", "mi6", "mi6lite", "mi5plus"]:
        enable_mss = st.checkbox("Motor start speed (MSS)")
        mss_speed = st.slider(
            "MSS", 1.0, 9.0, 5.0, 0.1, disabled=not enable_mss, key="mss_val"
        )
        if enable_mss:
            patches.append(f"mss={mss_speed}")

status_bits = []
if uploaded_file:
    status_bits.append(f'<span class="bw-chip">{uploaded_file.name}</span>')
status_bits.append(f'<span class="bw-chip">{scooter_model}</span>')
status_bits.append(
    f'<span class="bw-chip">{len(patches)} patch{"es" if len(patches) != 1 else ""}</span>'
)
st.markdown(f'<div class="bw-meta">{"".join(status_bits)}</div>', unsafe_allow_html=True)

can_patch = uploaded_file is not None and bool(patches)

if can_patch:
    if not advanced_mode and patches[-1] != "chk":
        patches.append("chk")
    if scooter_model in LEQI_MODELS:
        patches.append("img")

    if st.button("Apply patches", type="primary", use_container_width=True):
        with st.spinner("Patching…"):
            input_firmware = uploaded_file.read()
            try:
                patched_firmware = patch_firmware(scooter_model, input_firmware, patches)
                st.success("Patching complete.")
                st.download_button(
                    label="Download patched firmware",
                    data=BytesIO(patched_firmware),
                    file_name=f"patched_{scooter_model}_firmware.bin",
                    mime="application/octet-stream",
                    type="primary",
                    use_container_width=True,
                )
            except Exception as e:
                st.error(f"Patching failed: {e}")
elif uploaded_file is None:
    st.caption("Upload a firmware file to continue.")
elif not patches:
    st.caption("Select at least one patch.")

st.markdown(
    f'<p class="bw-foot">Educational / research only · CC-BY-NC-SA 4.0 · v{__version__}</p>',
    unsafe_allow_html=True,
)
