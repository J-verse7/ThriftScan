import streamlit as st
import google.generativeai as genai
from PIL import Image
import io

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ThriftScan AI",
    page_icon="👕",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Secure token load ──────────────────────────────────────────────────────────
if "GEMINI_API_KEY" not in st.secrets:
    st.error("GEMINI_API_KEY missing in Streamlit Secrets.")
    st.stop()

# Configure the API
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@300;400;600;700&family=DM+Sans:wght@300;400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: #0a0a0a;
    color: #e8e2d9;
}

.thrift-header {
    background: linear-gradient(160deg, #0a0a0a 0%, #141410 40%, #1a1a12 100%);
    border-bottom: 1px solid #2a2618;
    padding: 48px 0 36px;
    text-align: center;
    margin-bottom: 40px;
    position: relative;
}
.thrift-wordmark {
    font-family: 'Cormorant Garamond', serif;
    font-size: 3.4em;
    font-weight: 300;
    letter-spacing: 0.18em;
    color: #e8e2d9;
    text-transform: uppercase;
    margin: 0;
}
.thrift-wordmark span { color: #c4a454; }
.panel {
    background: #0f0f0c;
    border: 1px solid #1e1d16;
    border-radius: 4px;
    padding: 28px;
}
.section-label {
    font-size: 0.68em;
    letter-spacing: 0.3em;
    text-transform: uppercase;
    color: #6b6454;
    margin-bottom: 16px;
    padding-bottom: 10px;
    border-bottom: 1px solid #1e1d16;
}
.result-row {
    display: flex;
    border-bottom: 1px solid #1a1910;
    padding: 12px 0;
    align-items: baseline;
}
.result-key {
    font-size: 0.68em;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: #6b6454;
    min-width: 140px;
}
.result-val { font-size: 0.9em; color: #d4cec5; }
.result-val.gold { color: #c4a454; font-weight: 500; }

.verdict-card { border-radius: 4px; padding: 24px 28px; margin-top: 20px; display: flex; align-items: center; gap: 20px; }
.verdict-buy { background: #0a1a0e; border: 1px solid #1e4028; }
.verdict-pass { background: #1a0a0a; border: 1px solid #40201e; }
.verdict-negotiate { background: #141008; border: 1px solid #3d2c10; }
.verdict-label { font-family: 'Cormorant Garamond', serif; font-size: 1.9em; font-weight: 600; }
.verdict-buy .verdict-label { color: #4caf72; }
.verdict-pass .verdict-label { color: #c4504a; }
.verdict-negotiate .verdict-label { color: #c49440; }
.step-indicator { font-size: 0.72em; letter-spacing: 0.18em; text-transform: uppercase; color: #6b6454; }
.err-box { background: #150a0a; border: 1px solid #3a1a18; padding: 16px 20px; color: #c47070; }
</style>
""", unsafe_allow_html=True)

# ── Helper functions ──────────────────────────────────────────────────────────

def _map_error(err: str) -> str:
    e = str(err).lower()
    if "404" in e:
        return "Model connection error. Please ensure google-generativeai is updated in requirements.txt."
    if "api_key" in e:
        return "Invalid Gemini API Key. Please check your Streamlit Secrets."
    return f"Error: {err}"

def _build_prompt(price: float, mode: str) -> str:
    base = (
        f"You are an expert thrift store analyst in India. "
        f"Analyze this clothing item. The price is ₹{price:.0f}.\n\n"
    )
    if mode == "Quick Verdict":
        base += "Format:\nITEM: name\nCONDITION: Excellent/Good/Fair/Poor\nFAIR VALUE: ₹[low]-₹[high]\nVERDICT: BUY/PASS/NEGOTIATE\nREASON: 1 sentence"
    elif mode == "Outfit Ideas":
        base += "Format:\nITEM: name\nOUTFIT 1 (Occasion): combo\nOUTFIT 2 (Occasion): combo\nOUTFIT 3 (Occasion): combo\nOUTFIT 4 (Occasion): combo"
    else:
        base += "Format:\nITEM: name\nMATERIAL: fabric\nCONDITION: level\nERA / STYLE: vibe\nFAIR VALUE: ₹[low]-₹[high]\nRESALE: High/Med/Low\nOUTFIT 1: combo\nOUTFIT 2: combo\nSUSTAINABILITY: benefit\nVERDICT: BUY/PASS/NEGOTIATE\nREASON: 2 sentences"
    return base

def _render_results(raw: str, price: float, mode: str):
    lines = {}
    for line in raw.splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            lines[key.strip().upper()] = val.strip()

    row_keys = {
        "Full Analysis": ["ITEM", "MATERIAL", "CONDITION", "ERA / STYLE", "FAIR VALUE", "RESALE"],
        "Quick Verdict": ["ITEM", "CONDITION", "FAIR VALUE"],
        "Outfit Ideas": ["ITEM"],
    }

    display_rows = row_keys.get(mode, [])
    rows_html = "".join([f'<div class="result-row"><div class="result-key">{k.title()}</div><div class="result-val {"gold" if k in ["FAIR VALUE", "RESALE"] else ""}">{lines.get(k, "N/A")}</div></div>' for k in display_rows])
    
    outfits_html = "".join([f'<div class="result-row"><div class="result-key">Outfit {i}</div><div class="result-val">{lines.get(f"OUTFIT {i}", "")}</div></div>' for i in range(1, 5) if f"OUTFIT {i}" in lines])

    st.markdown(f'<div class="panel">{rows_html}{outfits_html}</div>', unsafe_allow_html=True)

    if mode != "Outfit Ideas":
        verdict = lines.get("VERDICT", "").upper()
        v_class = "verdict-buy" if "BUY" in verdict else "verdict-pass" if "PASS" in verdict else "verdict-negotiate"
        v_label = "Buy" if "BUY" in verdict else "Pass" if "PASS" in verdict else "Negotiate"
        
        st.markdown(f'<div class="verdict-card {v_class}"><div class="verdict-label">{v_label}</div><div class="verdict-divider"></div><div class="verdict-reason">{lines.get("REASON", "N/A")}</div></div>', unsafe_allow_html=True)
        if v_label == "Buy": st.balloons()

# ── Main UI ────────────────────────────────────────────────────────────────────
st.markdown('<div class="thrift-header"><div class="thrift-wordmark">Thrift<span>Scan</span> AI</div><div class="thrift-sub">India Edition</div></div>', unsafe_allow_html=True)

col_left, col_right = st.columns([1, 1.35], gap="large")

with col_left:
    st.markdown('<div class="section-label">Upload Item</div>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Upload", type=["jpg", "jpeg", "png"], label_visibility="collapsed")
    
    if uploaded_file:
        image = Image.open(uploaded_file).convert("RGB")
        st.image(image, use_container_width=True)
    
    st.markdown('<div class="section-label">Price (₹)</div>', unsafe_allow_html=True)
    price = st.number_input("Price", min_value=0.0, value=500.0, step=50.0, label_visibility="collapsed")
    
    mode = st.selectbox("Mode", ["Full Analysis", "Quick Verdict", "Outfit Ideas"], label_visibility="collapsed")
    analyze = st.button("Analyze Item")

with col_right:
    st.markdown('<div class="section-label">Analysis Result</div>', unsafe_allow_html=True)
    
    if not uploaded_file:
        st.info("Upload an image to begin.")
    elif analyze:
        status = st.empty()
        status.markdown('<div class="step-indicator">AI is scanning your item...</div>', unsafe_allow_html=True)
        
        try:
            buf = io.BytesIO()
            # Optimize image size for faster API response
            img_resized = image.copy()
            img_resized.thumbnail((512, 512))
            img_resized.save(buf, format="JPEG")
            
            # Using the direct model string which works best with configured API keys
            model = genai.GenerativeModel(model_name="gemini-1.5-flash")
            
            response = model.generate_content([
                _build_prompt(price, mode),
                {"mime_type": "image/jpeg", "data": buf.getvalue()}
            ])
            
            status.empty()
            if response.text:
                _render_results(response.text, price, mode)
            else:
                st.error("AI returned an empty response. Try a different image.")
            
        except Exception as e:
            status.empty()
            st.error(_map_error(e))