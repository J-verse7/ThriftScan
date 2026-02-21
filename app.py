import streamlit as st
import base64
from huggingface_hub import InferenceClient
from PIL import Image
import io

# ─── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ThriftScan AI",
    page_icon="👕",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ─── Load Token (Hidden from users — set in Streamlit Cloud Secrets) ──────────
try:
    HF_TOKEN = st.secrets["HF_TOKEN"]
except Exception:
    st.error("⚠️ App not configured yet. Owner needs to add HF_TOKEN in Streamlit Cloud secrets.")
    st.stop()

# ─── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .hero {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        border-radius: 16px; padding: 32px; text-align: center;
        margin-bottom: 24px; border: 1px solid #e94560;
    }
    .hero h1 { font-size: 2.4em; margin: 0; color: #fff; }
    .hero p  { color: #aaa; margin: 8px 0 0; font-size: 1.05em; }

    .upload-box {
        border: 2px dashed #444; border-radius: 14px; padding: 24px;
        text-align: center; background: #111122;
    }
    .result-card {
        background: #12122a; border-radius: 14px; padding: 22px;
        border: 1px solid #2a2a5a; margin-bottom: 16px;
    }
    .verdict-buy {
        background: linear-gradient(135deg, #0d3b1e, #1a5c32);
        border-radius: 14px; padding: 24px; text-align: center;
        border: 2px solid #52b788; margin-top: 16px;
    }
    .verdict-pass {
        background: linear-gradient(135deg, #3b0d0d, #5c1a1a);
        border-radius: 14px; padding: 24px; text-align: center;
        border: 2px solid #e63946; margin-top: 16px;
    }
    .verdict-negotiate {
        background: linear-gradient(135deg, #3b2500, #5c3c00);
        border-radius: 14px; padding: 24px; text-align: center;
        border: 2px solid #f4a261; margin-top: 16px;
    }
    .step-box {
        background: #0e0e22; border-radius: 10px; padding: 14px 18px;
        border-left: 4px solid #e94560; margin: 6px 0; font-size: 0.93em;
    }
    .stButton > button {
        background: linear-gradient(135deg, #e94560, #c42348) !important;
        color: white !important; border: none !important;
        border-radius: 10px !important; font-weight: 600 !important;
        font-size: 1.05em !important; padding: 12px 28px !important;
        width: 100% !important; transition: opacity 0.2s !important;
    }
    .stButton > button:hover { opacity: 0.88 !important; }
    hr { border-color: #222244; }
</style>
""", unsafe_allow_html=True)

# ─── Hero Banner ───────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <h1>👕 ThriftScan AI</h1>
    <p>Upload any clothing photo → Get AI analysis, outfit ideas & instant buy/pass verdict</p>
</div>
""", unsafe_allow_html=True)

# ─── How it works ──────────────────────────────────────────────────────────────
with st.expander("ℹ️ How does this work?"):
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.markdown('<div class="step-box">📸 <b>Step 1</b><br>Upload a clear photo of the clothing item</div>', unsafe_allow_html=True)
    with col_b:
        st.markdown('<div class="step-box">💲 <b>Step 2</b><br>Enter the price tag you see in the store</div>', unsafe_allow_html=True)
    with col_c:
        st.markdown('<div class="step-box">🤖 <b>Step 3</b><br>AI analyzes material, style, value & gives verdict</div>', unsafe_allow_html=True)

st.markdown("")

# ─── Main Layout ───────────────────────────────────────────────────────────────
col_left, col_right = st.columns([1, 1.3], gap="large")

with col_left:
    st.markdown("### 📤 Upload Item")
    uploaded_file = st.file_uploader(
        "Choose image",
        type=["jpg", "jpeg", "png"],
        label_visibility="collapsed"
    )

    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, caption="Your item", use_container_width=True)
        w, h = image.size
        st.caption(f"📐 {w}×{h}px")
    else:
        st.markdown("""
        <div class="upload-box">
            <div style="font-size:2.5em">👗</div>
            <div style="color:#888; margin-top:8px;">Drag & drop or click above to upload</div>
            <div style="color:#555; font-size:0.82em; margin-top:6px;">JPG · JPEG · PNG</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("")
    price = st.number_input("💲 Price tag on item ($)", min_value=0.0, value=10.0, step=0.5)
    mode = st.selectbox(
        "🎯 Analysis Mode",
        ["Full Analysis", "Quick Verdict Only", "Outfit Ideas Only"],
        help="Full Analysis gives everything. Quick is fast. Outfit Ideas focuses on styling."
    )
    analyze_clicked = st.button("🚀 Analyze Now — It's Free!")

# ─── Results Column ────────────────────────────────────────────────────────────
with col_right:
    st.markdown("### 🤖 AI Results")

    if not uploaded_file:
        st.markdown("""
        <div class="result-card" style="text-align:center; color:#555; padding:48px 24px;">
            <div style="font-size:2.5em">🔍</div>
            <div style="margin-top:12px;">Your analysis will appear here</div>
            <div style="font-size:0.82em; margin-top:6px;">Upload a photo and hit Analyze</div>
        </div>
        """, unsafe_allow_html=True)

    elif analyze_clicked:
        with st.spinner("🤖 AI is scanning your item... (first run may take ~30s)"):
            try:
                # ── Resize & encode image ───────────────────────────────────
                buf = io.BytesIO()
                if image.width > 800 or image.height > 800:
                    image.thumbnail((800, 800), Image.LANCZOS)
                image.save(buf, format="PNG")
                img_b64 = base64.b64encode(buf.getvalue()).decode()

                # ── Build prompt ────────────────────────────────────────────
                if mode == "Quick Verdict Only":
                    prompt_text = f"""You are a thrift store expert. This item is priced at ${price}.
Respond in this exact format:
**Item:** [name]
**Condition:** [Excellent / Good / Fair / Poor]
**Fair Value:** $[low]–$[high]
**Verdict:** BUY / PASS / NEGOTIATE
**Reason:** [1-2 sentences, honest and direct]"""

                elif mode == "Outfit Ideas Only":
                    prompt_text = """You are a creative fashion stylist. Look at this clothing item.
Give 4 outfit combinations:
**Outfit 1 – [Occasion]:** [specific items to pair + why it works]
**Outfit 2 – [Occasion]:** [specific items to pair + why it works]
**Outfit 3 – [Occasion]:** [specific items to pair + why it works]
**Outfit 4 – [Occasion]:** [specific items to pair + why it works]"""

                else:
                    prompt_text = f"""You are a professional thrift shopping advisor. Analyze this clothing item priced at ${price}.
Respond in this EXACT format:

**Item Type:** [e.g., vintage denim jacket]
**Color & Pattern:** [describe]
**Estimated Material:** [e.g., cotton blend, denim, polyester]
**Condition:** [Excellent / Good / Fair / Poor — brief reason]
**Style Era:** [e.g., 90s grunge, Y2K, minimalist]
**Fair Market Value:** $[low]–$[high]
**Resale Potential:** [High / Medium / Low — one sentence]

**Outfit Ideas:**
- **Casual:** [specific combo]
- **Smart Casual:** [specific combo]
- **Weekend:** [specific combo]

**Sustainability Bonus:** [one fun eco fact about buying secondhand]

**Verdict:** BUY / PASS / NEGOTIATE
**Reason:** [2–3 sentences, honest, no fluff]"""

                # ── API Call ────────────────────────────────────────────────
                              # ── API Call ────────────────────────────────────────────────
                client = InferenceClient(token=HF_TOKEN)

                caption = client.image_to_text(
                    image=buf.getvalue(),
                    model="Salesforce/blip-image-captioning-large"
                )

                ai_text = f"""
**Item Description:** {caption.generated_text}

**AI Advice:** Evaluate quality, stitching, material wear and resale value based on this description.
"""s
                # ── Display results ─────────────────────────────────────────
                st.markdown(f'<div class="result-card">{ai_text}</div>', unsafe_allow_html=True)

                # ── Verdict banner ──────────────────────────────────────────
                if mode != "Outfit Ideas Only":
                    verdict = ""
                    for line in ai_text.upper().split("\n"):
                        if "VERDICT" in line:
                            verdict = line
                            break

                    st.markdown("---")
                    if "BUY" in verdict and "PASS" not in verdict:
                        st.markdown(f"""<div class="verdict-buy">
                            <div style="font-size:2em">🎉</div>
                            <h2 style="color:#52b788; margin:8px 0">BUY IT!</h2>
                            <p style="color:#ccc;">${price} is a great deal. Grab it!</p>
                        </div>""", unsafe_allow_html=True)
                        st.balloons()
                    elif "PASS" in verdict:
                        st.markdown(f"""<div class="verdict-pass">
                            <div style="font-size:2em">❌</div>
                            <h2 style="color:#e63946; margin:8px 0">PASS</h2>
                            <p style="color:#ccc;">${price} isn't worth it. Walk away!</p>
                        </div>""", unsafe_allow_html=True)
                    elif "NEGOTIATE" in verdict:
                        suggest = round(price * 0.65, 2)
                        st.markdown(f"""<div class="verdict-negotiate">
                            <div style="font-size:2em">🤝</div>
                            <h2 style="color:#f4a261; margin:8px 0">NEGOTIATE</h2>
                            <p style="color:#ccc;">Good item — try to bring it down to <b>${suggest}</b></p>
                        </div>""", unsafe_allow_html=True)

            except Exception as e:
                err = str(e)
                if "401" in err or "unauthorized" in err.lower():
                    st.error("🔑 Auth failed. App owner needs to verify the HF token in Secrets.")
                elif "503" in err or "loading" in err.lower():
                    st.warning("⏳ Model is warming up. Wait 30 seconds and try again — totally normal!")
                elif "429" in err or "quota" in err.lower():
                    st.warning("🚦 Too many requests right now. Wait a minute and retry.")
                elif "413" in err or "too large" in err.lower():
                    st.warning("📦 Image too large. Try a smaller photo.")
                else:
                    st.error(f"Something went wrong: {err}")
                    st.info("💡 Try a clearer, well-lit photo or a smaller file.")

    else:
        st.markdown("""
        <div class="result-card" style="text-align:center; color:#666; padding:48px 24px;">
            <div style="font-size:2em">👆</div>
            <div style="margin-top:10px;">Hit <b>Analyze Now</b> to get results!</div>
        </div>
        """, unsafe_allow_html=True)

# ─── Footer ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<center><sub>👕 ThriftScan AI &nbsp;•&nbsp; Powered by LLaVA on Hugging Face &nbsp;•&nbsp; 100% Free to use</sub></center>",
    unsafe_allow_html=True
)