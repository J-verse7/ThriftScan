import streamlit as st
import base64
from huggingface_hub import InferenceClient
from PIL import Image
import io
import re

# ─── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ThriftScan AI",
    page_icon="👕",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .verdict-buy {
        background: linear-gradient(135deg, #1a472a, #2d6a4f);
        border-radius: 12px; padding: 20px; text-align: center;
        border: 2px solid #52b788; margin-top: 10px;
    }
    .verdict-pass {
        background: linear-gradient(135deg, #7b1313, #c1121f);
        border-radius: 12px; padding: 20px; text-align: center;
        border: 2px solid #e63946; margin-top: 10px;
    }
    .verdict-negotiate {
        background: linear-gradient(135deg, #7c4d03, #b5640a);
        border-radius: 12px; padding: 20px; text-align: center;
        border: 2px solid #f4a261; margin-top: 10px;
    }
    .info-card {
        background: #1e1e2e; border-radius: 10px;
        padding: 16px; border: 1px solid #333355;
        margin: 8px 0;
    }
    .tag {
        display: inline-block; background: #2a2a4a;
        border-radius: 20px; padding: 4px 12px;
        margin: 4px; font-size: 0.85em; border: 1px solid #444477;
    }
</style>
""", unsafe_allow_html=True)

# ─── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Settings")
    hf_token = st.text_input(
        "🔑 Hugging Face Token",
        type="password",
        help="Get free token at huggingface.co/settings/tokens"
    )
    st.markdown("---")
    st.subheader("💲 Item Price")
    price = st.number_input("Price you see on tag ($)", min_value=0.0, value=10.0, step=0.5)
    
    st.markdown("---")
    st.subheader("🎯 Analysis Mode")
    mode = st.radio("Focus on:", ["Full Analysis", "Quick Verdict Only", "Outfit Ideas Only"])
    
    st.markdown("---")
    st.caption("🔒 Token is hidden & never stored. Free HF tier works fine.")
    st.caption("📦 Model: LLaVA-1.6 (Vision + Language AI)")

# ─── Header ────────────────────────────────────────────────────────────────────
st.title("👕 ThriftScan AI")
st.markdown("**Your AI-powered thrift shopping assistant.** Upload any clothing photo → get instant analysis, outfit combos, and a buy/pass verdict.")
st.markdown("---")

# ─── Main Layout ──────────────────────────────────────────────────────────────
col_upload, col_results = st.columns([1, 1.2], gap="large")

with col_upload:
    st.subheader("📸 Upload Clothing Photo")
    uploaded_file = st.file_uploader(
        "Drag & drop or click to browse",
        type=["jpg", "jpeg", "png"],
        label_visibility="collapsed"
    )
    
    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, caption="📷 Your item", use_container_width=True)
        
        # Image metadata
        w, h = image.size
        st.caption(f"Resolution: {w}×{h}px | Format: {image.format or 'PNG'}")
        
        # Analyze button
        analyze_clicked = st.button("🚀 Analyze This Item", type="primary", use_container_width=True)
    else:
        st.info("👆 Upload a photo of any clothing item from a thrift store or your closet!")
        analyze_clicked = False
        
        # Demo hint
        st.markdown("""
        **Works best with:**
        - 📸 Clear, well-lit photos
        - 👗 Flat-lay or hanging shots  
        - 🧥 Single item per photo
        """)

# ─── Analysis Logic ────────────────────────────────────────────────────────────
with col_results:
    st.subheader("🤖 AI Analysis")
    
    if not uploaded_file:
        st.markdown('<div class="info-card">Results will appear here after you upload a photo and click Analyze.</div>', unsafe_allow_html=True)
    
    elif analyze_clicked:
        if not hf_token:
            st.error("⚠️ Please paste your Hugging Face token in the sidebar first!")
        else:
            with st.spinner("🔍 AI is analyzing your item... (may take 30-60s on free tier)"):
                try:
                    # ── Prepare image ──
                    buf = io.BytesIO()
                    image.save(buf, format="PNG")
                    img_b64 = base64.b64encode(buf.getvalue()).decode()

                    # ── Build prompt based on mode ──
                    if mode == "Quick Verdict Only":
                        prompt_text = f"""You are a thrift store expert. Look at this clothing item priced at ${price}.

Respond ONLY in this format:
**Item:** [name]
**Condition:** [Excellent/Good/Fair/Poor]
**Fair Market Value:** $[low]-$[high]
**Verdict:** BUY / PASS / NEGOTIATE
**One-line reason:** [why]"""
                    
                    elif mode == "Outfit Ideas Only":
                        prompt_text = """You are a fashion stylist. Look at this clothing item.
Give 4 creative outfit combinations. Format:
**Outfit 1 - [vibe/occasion]:** [what to pair it with]
**Outfit 2 - [vibe/occasion]:** [what to pair it with]
**Outfit 3 - [vibe/occasion]:** [what to pair it with]
**Outfit 4 - [vibe/occasion]:** [what to pair it with]
Be specific and fun!"""
                    
                    else:  # Full Analysis
                        prompt_text = f"""You are a professional thrift shopping advisor and fashion stylist. Analyze this clothing photo in detail.

The item is priced at ${price}. Give me a complete analysis in this EXACT format:

**Item Type:** [e.g., vintage denim jacket, floral midi dress]
**Color & Pattern:** [describe colors and any patterns]
**Material (estimated):** [e.g., 80% cotton, denim, polyester blend]
**Quality & Condition:** [Excellent/Good/Fair/Poor — explain briefly]
**Era/Style:** [e.g., 90s grunge, Y2K, classic preppy, cottagecore]
**Fair Market Value:** $[low]-$[high] (thrift store range)
**Resale Potential:** [High/Medium/Low — and why]

**Outfit Ideas:**
- **Casual:** [specific combo]
- **Smart Casual:** [specific combo]
- **Weekend:** [specific combo]

**Sustainability Note:** [brief eco-friendly angle]

**Final Verdict:** BUY / PASS / NEGOTIATE
**Reason:** [2-3 sentences max — direct and honest]"""

                    # ── Call HuggingFace API (Chat Completions with vision) ──
                    client = InferenceClient(token=hf_token)
                    
                    response = client.chat.completions.create(
                        model="llava-hf/llava-1.6-mistral-7b-hf",
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "image_url",
                                        "image_url": {"url": f"data:image/png;base64,{img_b64}"}
                                    },
                                    {
                                        "type": "text",
                                        "text": prompt_text
                                    }
                                ]
                            }
                        ],
                        max_tokens=500
                    )
                    
                    ai_text = response.choices[0].message.content

                    # ── Display Results ──
                    st.success("✅ Analysis Complete!")
                    st.markdown(ai_text)

                    # ── Smart Verdict Banner ──
                    if mode != "Outfit Ideas Only":
                        verdict_line = ""
                        for line in ai_text.split("\n"):
                            if "verdict" in line.lower():
                                verdict_line = line.upper()
                                break
                        
                        st.markdown("---")
                        if "BUY" in verdict_line and "PASS" not in verdict_line:
                            st.markdown(f'<div class="verdict-buy"><h2>🎉 BUY IT!</h2><p>Great deal at <strong>${price}</strong></p></div>', unsafe_allow_html=True)
                            st.balloons()
                        elif "PASS" in verdict_line:
                            st.markdown(f'<div class="verdict-pass"><h2>❌ PASS</h2><p>Not worth <strong>${price}</strong> — move on!</p></div>', unsafe_allow_html=True)
                        elif "NEGOTIATE" in verdict_line:
                            suggest = round(price * 0.65, 2)
                            st.markdown(f'<div class="verdict-negotiate"><h2>🤝 NEGOTIATE</h2><p>Try to get it down to <strong>${suggest}</strong></p></div>', unsafe_allow_html=True)

                except Exception as e:
                    err = str(e)
                    st.error(f"❌ API Error: {err}")
                    
                    if "401" in err or "unauthorized" in err.lower():
                        st.info("🔑 Token issue — make sure it starts with `hf_` and has Inference permissions.")
                    elif "503" in err or "loading" in err.lower():
                        st.info("⏳ Model is loading (cold start). Wait 30 seconds and try again — this is normal on free tier.")
                    elif "quota" in err.lower() or "429" in err:
                        st.info("🚦 Rate limited. Wait a minute and try again, or try a smaller image.")
                    else:
                        st.info("💡 Tips: Use a clear, well-lit photo. Reduce image size if it's very large.")

# ─── Footer ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<center><sub>ThriftScan AI • Built with Streamlit + HuggingFace LLaVA • 100% Free Tier</sub></center>",
    unsafe_allow_html=True
)