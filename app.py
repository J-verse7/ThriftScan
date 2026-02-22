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
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="hero"><h1>👕 ThriftScan AI</h1><p>Upload photo for AI verdict</p></div>', unsafe_allow_html=True)

# ─── Main Layout ───────────────────────────────────────────────────────────────
col_left, col_right = st.columns([1, 1.3], gap="large")

with col_left:
    st.markdown("### 📤 Upload Item")
    uploaded_file = st.file_uploader("Choose image", type=["jpg", "jpeg", "png"], label_visibility="collapsed")

    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, caption="Your item", use_container_width=True)
    
    price = st.number_input("💲 Price ($)", min_value=0.0, value=10.0, step=0.5)
    analyze_clicked = st.button("🚀 Analyze Now")

with col_right:
    st.markdown("### 🤖 AI Results")

    if uploaded_file and analyze_clicked:
        with st.spinner("Scanning..."):
            try:
                # API Call Setup
                buf = io.BytesIO()
                image.save(buf, format="JPEG")
                client = InferenceClient(token=HF_TOKEN)
                
                # Model Inference
                response = client.image_to_text(image=buf.getvalue(), model="Salesforce/blip-image-captioning-large")
                
                # Handle response type variations
                description = response[0]['generated_text'] if isinstance(response, list) else response
                if hasattr(description, 'generated_text'):
                    description = description.generated_text

                st.markdown(f'<div class="result-card">**Item Description:** {description}</div>', unsafe_allow_html=True)

                # Simplified Verdict Logic
                if price < 15:
                    st.markdown(f'<div class="verdict-buy"><h2>BUY IT!</h2><p>${price} is a steal.</p></div>', unsafe_allow_html=True)
                    st.balloons()
                elif price < 40:
                    st.markdown(f'<div class="verdict-negotiate"><h2>NEGOTIATE</h2><p>Try ${round(price*0.7, 2)}</p></div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="verdict-pass"><h2>PASS</h2><p>Too expensive.</p></div>', unsafe_allow_html=True)

            except Exception as e:
                st.error(f"Error: {str(e)}")
    else:
        st.info("Upload an image and hit Analyze.")
