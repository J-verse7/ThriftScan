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

# ─── Load Token ───────────────────────────────────────────────────────────────
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
    .result-card {
        background: #12122a; border-radius: 14px; padding: 22px;
        border: 1px solid #2a2a5a; margin-bottom: 16px;
    }
    .verdict-buy { background: #0d3b1e; border: 2px solid #52b788; border-radius: 14px; padding: 20px; text-align: center; }
    .verdict-pass { background: #3b0d0d; border: 2px solid #e63946; border-radius: 14px; padding: 20px; text-align: center; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="hero"><h1>👕 ThriftScan AI</h1><p>AI-Powered Clothing Analysis</p></div>', unsafe_allow_html=True)

# ─── Layout ────────────────────────────────────────────────────────────────────
col_left, col_right = st.columns([1, 1.3], gap="large")

with col_left:
    st.markdown("### 📤 Upload Item")
    uploaded_file = st.file_uploader("Choose image", type=["jpg", "jpeg", "png"], label_visibility="collapsed")
    price = st.number_input("💲 Price ($)", min_value=0.0, value=10.0)
    analyze_clicked = st.button("🚀 Analyze Now")

with col_right:
    st.markdown("### 🤖 AI Results")
    
    if uploaded_file and analyze_clicked:
        with st.spinner("Analyzing..."):
            try:
                # 1. Process Image & Fix RGBA Error
                image = Image.open(uploaded_file)
                if image.mode in ("RGBA", "P"):
                    image = image.convert("RGB")
                
                buf = io.BytesIO()
                image.save(buf, format="JPEG")
                img_bytes = buf.getvalue()

                # 2. Call BLIP Model
                client = InferenceClient(token=HF_TOKEN)
                response = client.image_to_text(image=img_bytes, model="Salesforce/blip-image-captioning-large")
                
                # Extract text description
                desc = response[0]['generated_text'] if isinstance(response, list) else response
                if hasattr(desc, 'generated_text'):
                    desc = desc.generated_text

                st.markdown(f'<div class="result-card"><b>Description:</b> {desc}</div>', unsafe_allow_html=True)

                # 3. Simple Verdict Logic
                if price < 20:
                    st.markdown('<div class="verdict-buy">✅ BUY IT!</div>', unsafe_allow_html=True)
                    st.balloons()
                else:
                    st.markdown('<div class="verdict-pass">❌ PASS: Too expensive.</div>', unsafe_allow_html=True)

            except Exception as e:
                st.error(f"Error: {str(e)}")
    else:
        st.info("Upload an image and click Analyze.")
