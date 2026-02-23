import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io

st.set_page_config(page_title="ThriftScan AI", page_icon="👕", layout="wide", initial_sidebar_state="collapsed")

if "GEMINI_API_KEY" not in st.secrets:
    st.error("GEMINI_API_KEY missing in Streamlit Secrets.")
    st.stop()

client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@300;400;600;700&family=DM+Sans:wght@300;400;500&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; background-color: #0a0a0a; color: #e8e2d9; }
.thrift-header { background: linear-gradient(160deg, #0a0a0a 0%, #141410 40%, #1a1a12 100%); border-bottom: 1px solid #2a2618; padding: 48px 0 36px; text-align: center; margin-bottom: 40px; }
.thrift-wordmark { font-family: 'Cormorant Garamond', serif; font-size: 3.4em; font-weight: 300; letter-spacing: 0.18em; color: #e8e2d9; text-transform: uppercase; margin: 0; }
.thrift-wordmark span { color: #c4a454; }
.panel { background: #0f0f0c; border: 1px solid #1e1d16; border-radius: 4px; padding: 28px; }
.section-label { font-size: 0.68em; letter-spacing: 0.3em; text-transform: uppercase; color: #6b6454; margin-bottom: 16px; padding-bottom: 10px; border-bottom: 1px solid #1e1d16; }
.result-row { display: flex; border-bottom: 1px solid #1a1910; padding: 12px 0; align-items: baseline; }
.result-key { font-size: 0.68em; letter-spacing: 0.2em; text-transform: uppercase; color: #6b6454; min-width: 140px; }
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
.err-box { background: #150a0a; border: 1px solid #3a1a18; padding: 16px 20px; color: #c47070; border-radius: 4px; }
</style>
""", unsafe_allow_html=True)


def _build_prompt(price: float, mode: str) -> str:
    return (
        f"You are an expert thrift store analyst in India. Analyze this clothing item. "
        f"The asking price is Rs.{price:.0f} (Indian Rupees). "
        "Respond in EXACT format:\n"
        "ITEM: name\nMATERIAL: fabric\nCONDITION: level\nERA: style\n"
        "FAIR VALUE: Rs.low-Rs.high\nRESALE: level\nOUTFIT 1: combo\nOUTFIT 2: combo\n"
        "SUSTAINABILITY: benefit\nVERDICT: BUY or PASS or NEGOTIATE\nREASON: 2 short sentences."
    )


def _render_results(raw: str, price: float):
    lines = {}
    for line in raw.splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            lines[key.strip().upper()] = val.strip()
    row_keys = ["ITEM", "MATERIAL", "CONDITION", "ERA", "FAIR VALUE", "RESALE", "OUTFIT 1", "OUTFIT 2", "SUSTAINABILITY"]
    rows_html = ""
    for k in row_keys:
        gold = ' gold' if "VALUE" in k else ''
        rows_html += f'<div class="result-row"><div class="result-key">{k.title()}</div><div class="result-val{gold}">{lines.get(k, "N/A")}</div></div>'
    st.markdown(f'<div class="panel">{rows_html}</div>', unsafe_allow_html=True)
    if "VERDICT" in lines:
        v = lines["VERDICT"].upper()
        v_class = "verdict-buy" if "BUY" in v else "verdict-pass" if "PASS" in v else "verdict-negotiate"
        st.markdown(
            f'<div class="verdict-card {v_class}"><div class="verdict-label">{v}</div>'
            f'<div style="width:1px;height:40px;background:#2a2618;margin:0 20px;"></div>'
            f'<div style="color:#b0a898;font-size:0.84em;flex:1;">{lines.get("REASON","N/A")}</div></div>',
            unsafe_allow_html=True
        )
        if "BUY" in v:
            st.balloons()


st.markdown(
    '<div class="thrift-header"><div class="thrift-wordmark">Thrift<span>Scan</span> AI</div>'
    '<div style="font-size:0.78em;color:#6b6454;margin-top:10px;">India Edition · Prices in Rs.</div></div>',
    unsafe_allow_html=True
)

col_left, col_right = st.columns([1, 1.35], gap="large")

with col_left:
    st.markdown('<div class="section-label">Upload Item</div>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Upload", type=["jpg", "jpeg", "png"], label_visibility="collapsed")
    if uploaded_file:
        image = Image.open(uploaded_file).convert("RGB")
        st.image(image, use_container_width=True)
    price_val = st.number_input("Price (Rs.)", min_value=0, value=500, step=50)
    mode_val = st.selectbox("Mode", ["Full Analysis", "Quick Verdict", "Outfit Ideas"])
    analyze_btn = st.button("Analyze Item")

with col_right:
    st.markdown('<div class="section-label">Analysis Result</div>', unsafe_allow_html=True)
    if not uploaded_file:
        st.info("Upload an image to begin.")
    elif analyze_btn:
        status = st.empty()
        status.markdown('<div style="font-size:0.72em;color:#6b6454;">Scanning your item...</div>', unsafe_allow_html=True)
        try:
            buf = io.BytesIO()
            image.save(buf, format="JPEG", quality=85)
            image_bytes = buf.getvalue()
            response = client.models.generate_content(
                model="gemini-1.5-flash",
                contents=[
                    _build_prompt(price_val, mode_val),
                    types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                ]
            )
            status.empty()
            _render_results(response.text, price_val)
        except Exception as e:
            status.empty()
            st.markdown(f'<div class="err-box">Error: {str(e)}</div>', unsafe_allow_html=True)

st.markdown(
    "<div style='height:48px'></div>"
    "<div style='text-align:center;font-size:0.68em;color:#2a2618;padding-bottom:24px;'>"
    "ThriftScan AI · Gemini 1.5 Flash · Indian Market · Prices in Rs.</div>",
    unsafe_allow_html=True
)
```

---

**Step 4** — Scroll down on GitHub, click **"Commit changes"** → **"Commit directly to main"** → **"Commit changes"**

**Step 5** — Now go to:
```
https://github.com/J-verse7/ThriftScan/edit/main/requirements.txt
```
Select all, delete, paste this exactly:
```
streamlit
google-genai>=1.5.0
Pillow
