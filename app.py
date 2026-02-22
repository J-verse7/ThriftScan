import streamlit as st
from huggingface_hub import InferenceClient
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
try:
    HF_TOKEN = st.secrets["HF_TOKEN"]
except (KeyError, FileNotFoundError):
    st.error(
        "Configuration error: HF_TOKEN not found. "
        "Add it under App Settings → Secrets on Streamlit Cloud."
    )
    st.stop()

# ── Models ─────────────────────────────────────────────────────────────────────
CAPTION_MODEL = "Salesforce/blip-image-captioning-large"   # Step 1: image → text
ANALYSIS_MODEL = "mistralai/Mistral-7B-Instruct-v0.2"      # Step 2: text → verdict

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@300;400;600;700&family=DM+Sans:wght@300;400;500&display=swap');

/* ── Base ── */
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: #0a0a0a;
    color: #e8e2d9;
}

/* ── Header ── */
.thrift-header {
    background: linear-gradient(160deg, #0a0a0a 0%, #141410 40%, #1a1a12 100%);
    border-bottom: 1px solid #2a2618;
    padding: 48px 0 36px;
    text-align: center;
    margin-bottom: 40px;
    position: relative;
    overflow: hidden;
}
.thrift-header::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    background: radial-gradient(ellipse at 50% 0%, rgba(196,164,84,0.08) 0%, transparent 60%);
    pointer-events: none;
}
.thrift-wordmark {
    font-family: 'Cormorant Garamond', serif;
    font-size: 3.4em;
    font-weight: 300;
    letter-spacing: 0.18em;
    color: #e8e2d9;
    text-transform: uppercase;
    margin: 0;
    line-height: 1;
}
.thrift-wordmark span { color: #c4a454; }
.thrift-sub {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.78em;
    font-weight: 300;
    letter-spacing: 0.28em;
    color: #6b6454;
    text-transform: uppercase;
    margin-top: 10px;
}

/* ── Panels ── */
.panel {
    background: #0f0f0c;
    border: 1px solid #1e1d16;
    border-radius: 4px;
    padding: 28px;
}

/* ── Section labels ── */
.section-label {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.68em;
    letter-spacing: 0.3em;
    text-transform: uppercase;
    color: #6b6454;
    margin-bottom: 16px;
    padding-bottom: 10px;
    border-bottom: 1px solid #1e1d16;
}

/* ── Upload area ── */
.upload-placeholder {
    border: 1px dashed #2a2618;
    border-radius: 4px;
    padding: 48px 24px;
    text-align: center;
    background: #0a0a08;
    color: #3d3a30;
}
.upload-icon { font-size: 2em; margin-bottom: 8px; opacity: 0.5; }
.upload-hint { font-size: 0.8em; letter-spacing: 0.05em; margin-top: 6px; }

/* ── Inputs ── */
[data-testid="stNumberInput"] input,
[data-testid="stSelectbox"] > div {
    background: #0f0f0c !important;
    border: 1px solid #2a2618 !important;
    border-radius: 4px !important;
    color: #e8e2d9 !important;
    font-family: 'DM Sans', sans-serif !important;
}

/* ── Button ── */
.stButton > button {
    background: #c4a454 !important;
    color: #0a0a0a !important;
    border: none !important;
    border-radius: 4px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 500 !important;
    font-size: 0.8em !important;
    letter-spacing: 0.2em !important;
    text-transform: uppercase !important;
    padding: 14px 32px !important;
    width: 100% !important;
    transition: background 0.2s, opacity 0.2s !important;
}
.stButton > button:hover { background: #b89440 !important; }

/* ── Results ── */
.result-empty {
    text-align: center;
    padding: 60px 24px;
    color: #2a2618;
}
.result-empty-icon { font-size: 2em; opacity: 0.4; margin-bottom: 12px; }
.result-empty-text { font-size: 0.8em; letter-spacing: 0.12em; text-transform: uppercase; }

.result-row {
    display: flex;
    gap: 0;
    border-bottom: 1px solid #1a1910;
    padding: 12px 0;
    align-items: baseline;
}
.result-row:last-child { border-bottom: none; }
.result-key {
    font-size: 0.68em;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: #6b6454;
    min-width: 140px;
    flex-shrink: 0;
}
.result-val {
    font-size: 0.9em;
    color: #d4cec5;
    line-height: 1.6;
}
.result-val.gold { color: #c4a454; font-weight: 500; }

/* ── Verdict cards ── */
.verdict-card {
    border-radius: 4px;
    padding: 24px 28px;
    margin-top: 20px;
    display: flex;
    align-items: center;
    gap: 20px;
}
.verdict-buy    { background: #0a1a0e; border: 1px solid #1e4028; }
.verdict-pass   { background: #1a0a0a; border: 1px solid #40201e; }
.verdict-negotiate { background: #141008; border: 1px solid #3d2c10; }

.verdict-label {
    font-family: 'Cormorant Garamond', serif;
    font-size: 1.9em;
    font-weight: 600;
    letter-spacing: 0.08em;
    line-height: 1;
}
.verdict-buy .verdict-label    { color: #4caf72; }
.verdict-pass .verdict-label   { color: #c4504a; }
.verdict-negotiate .verdict-label { color: #c49440; }

.verdict-sub {
    font-size: 0.78em;
    color: #6b6454;
    letter-spacing: 0.05em;
    margin-top: 4px;
}

.verdict-divider {
    width: 1px;
    height: 44px;
    background: #2a2618;
    flex-shrink: 0;
}
.verdict-reason {
    font-size: 0.84em;
    color: #b0a898;
    line-height: 1.7;
    flex: 1;
}

/* ── Progress / spinner text ── */
.step-indicator {
    font-size: 0.72em;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: #6b6454;
    margin: 8px 0;
}

/* ── Error / warning ── */
.err-box {
    background: #150a0a;
    border: 1px solid #3a1a18;
    border-radius: 4px;
    padding: 16px 20px;
    font-size: 0.84em;
    color: #c47070;
    line-height: 1.6;
}

/* ── Divider ── */
hr { border-color: #1a1910 !important; margin: 24px 0 !important; }

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stDecoration"] { display: none; }
</style>
""", unsafe_allow_html=True)

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="thrift-header">
    <div class="thrift-wordmark">Thrift<span>Scan</span> AI</div>
    <div class="thrift-sub">Intelligent Clothing Analysis</div>
</div>
""", unsafe_allow_html=True)

# ── Layout ─────────────────────────────────────────────────────────────────────
col_left, col_right = st.columns([1, 1.35], gap="large")

# ══ LEFT COLUMN ════════════════════════════════════════════════════════════════
with col_left:
    st.markdown('<div class="section-label">Upload Item</div>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader(
        "Upload clothing image",
        type=["jpg", "jpeg", "png"],
        label_visibility="collapsed",
    )

    if uploaded_file:
        image = Image.open(uploaded_file).convert("RGB")
        st.image(image, use_container_width=True)
        w, h = image.size
        st.markdown(
            f'<div style="font-size:0.7em;letter-spacing:0.1em;color:#3d3a30;'
            f'text-transform:uppercase;margin-top:6px;">{w} × {h} px</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown("""
        <div class="upload-placeholder">
            <div class="upload-icon">◻</div>
            <div>Drag & drop or click to browse</div>
            <div class="upload-hint">JPG · JPEG · PNG</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    st.markdown('<div class="section-label">Price</div>', unsafe_allow_html=True)
    price = st.number_input(
        "Price ($)",
        min_value=0.0,
        value=10.0,
        step=0.5,
        format="%.2f",
        label_visibility="collapsed",
    )

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    st.markdown('<div class="section-label">Mode</div>', unsafe_allow_html=True)
    mode = st.selectbox(
        "Analysis mode",
        ["Full Analysis", "Quick Verdict", "Outfit Ideas"],
        label_visibility="collapsed",
    )

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    analyze = st.button("Analyze Item")

# ══ RIGHT COLUMN ═══════════════════════════════════════════════════════════════
with col_right:
    st.markdown('<div class="section-label">Analysis</div>', unsafe_allow_html=True)

    # ── Idle state ─────────────────────────────────────────────────────────────
    if not uploaded_file:
        st.markdown("""
        <div class="result-empty">
            <div class="result-empty-icon">◻</div>
            <div class="result-empty-text">Upload an image to begin</div>
        </div>
        """, unsafe_allow_html=True)

    # ── Waiting for click ──────────────────────────────────────────────────────
    elif not analyze:
        st.markdown("""
        <div class="result-empty">
            <div class="result-empty-icon">→</div>
            <div class="result-empty-text">Click Analyze Item to continue</div>
        </div>
        """, unsafe_allow_html=True)

    # ── Run analysis ───────────────────────────────────────────────────────────
    else:
        client = InferenceClient(token=HF_TOKEN)

        # ── Step 1 of 2: Image captioning via BLIP ─────────────────────────
        step1 = st.empty()
        step1.markdown('<div class="step-indicator">Step 1 / 2 — Reading image…</div>', unsafe_allow_html=True)

        try:
            buf = io.BytesIO()
            img = image.copy()
            if img.width > 768 or img.height > 768:
                img.thumbnail((768, 768), Image.LANCZOS)
            img.save(buf, format="JPEG", quality=85)
            image_bytes = buf.getvalue()

            caption_result = client.image_to_text(
                image=image_bytes,
                model=CAPTION_MODEL,
            )
            # InferenceClient returns a string or ImageToTextOutput object
            if hasattr(caption_result, "generated_text"):
                caption = caption_result.generated_text
            else:
                caption = str(caption_result)

        except Exception as e:
            step1.empty()
            err = str(e)
            _friendly = _map_error(err)
            st.markdown(f'<div class="err-box">{_friendly}</div>', unsafe_allow_html=True)
            st.stop()

        # ── Step 2 of 2: LLM analysis via Mistral ─────────────────────────
        step1.markdown('<div class="step-indicator">Step 2 / 2 — Analysing…</div>', unsafe_allow_html=True)

        try:
            prompt = _build_prompt(caption, price, mode)

            llm_response = client.text_generation(
                prompt=prompt,
                model=ANALYSIS_MODEL,
                max_new_tokens=480,
                temperature=0.4,
                repetition_penalty=1.1,
                stop_sequences=["</s>", "[/INST]", "###"],
            )

            raw_text = llm_response.strip()

        except Exception as e:
            step1.empty()
            err = str(e)
            st.markdown(f'<div class="err-box">{_map_error(err)}</div>', unsafe_allow_html=True)
            st.stop()

        step1.empty()

        # ── Parse and render results ───────────────────────────────────────
        _render_results(caption, raw_text, price, mode)


# ── Helper functions ───────────────────────────────────────────────────────────

def _build_prompt(caption: str, price: float, mode: str) -> str:
    """Build the Mistral instruction prompt."""

    base = f"""[INST] You are a professional thrift store expert and fashion stylist.

A customer found a clothing item described as: "{caption}"
The asking price is ${price:.2f}.

"""

    if mode == "Quick Verdict":
        base += """Respond in this EXACT format and nothing else:

ITEM: [item name]
CONDITION: [Excellent / Good / Fair / Poor]
FAIR VALUE: $[low]–$[high]
VERDICT: [BUY / PASS / NEGOTIATE]
REASON: [One honest sentence]
[/INST]"""

    elif mode == "Outfit Ideas":
        base += """Give 4 creative outfit ideas. Respond in this EXACT format:

ITEM: [item name]
OUTFIT 1 ([occasion]): [specific pieces to pair with it]
OUTFIT 2 ([occasion]): [specific pieces to pair with it]
OUTFIT 3 ([occasion]): [specific pieces to pair with it]
OUTFIT 4 ([occasion]): [specific pieces to pair with it]
[/INST]"""

    else:  # Full Analysis
        base += """Respond in this EXACT format and nothing else:

ITEM: [item name and brief descriptor]
MATERIAL: [estimated fabric / material]
CONDITION: [Excellent / Good / Fair / Poor — one-line reason]
ERA / STYLE: [decade or aesthetic, e.g. 90s denim, minimalist, Y2K]
FAIR VALUE: $[low]–$[high]
RESALE: [High / Medium / Low — one reason]
OUTFIT 1 (Casual): [specific combo]
OUTFIT 2 (Smart Casual): [specific combo]
OUTFIT 3 (Going Out): [specific combo]
SUSTAINABILITY: [one eco benefit of buying this secondhand]
VERDICT: [BUY / PASS / NEGOTIATE]
REASON: [2 direct honest sentences — no fluff]
[/INST]"""

    return base


def _render_results(caption: str, raw: str, price: float, mode: str):
    """Parse the LLM output and render it as structured UI."""

    lines = {}
    for line in raw.splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            lines[key.strip().upper()] = val.strip()

    # ── Structured rows ─────────────────────────────────────────────────
    row_keys = {
        "Full Analysis":  ["ITEM", "MATERIAL", "CONDITION", "ERA / STYLE", "FAIR VALUE", "RESALE"],
        "Quick Verdict":  ["ITEM", "CONDITION", "FAIR VALUE"],
        "Outfit Ideas":   ["ITEM"],
    }

    display_rows = row_keys.get(mode, [])

    rows_html = ""
    for k in display_rows:
        val = lines.get(k, lines.get(k.replace(" / ", "/"), ""))
        if val:
            gold_keys = {"FAIR VALUE", "RESALE", "VERDICT"}
            val_class = "result-val gold" if k in gold_keys else "result-val"
            rows_html += f"""
            <div class="result-row">
                <div class="result-key">{k.title()}</div>
                <div class="{val_class}">{val}</div>
            </div>"""

    # ── Outfit rows ─────────────────────────────────────────────────────
    outfit_html = ""
    for i in range(1, 5):
        key = f"OUTFIT {i}"
        if key in lines:
            outfit_html += f"""
            <div class="result-row">
                <div class="result-key">{key.title()}</div>
                <div class="result-val">{lines[key]}</div>
            </div>"""

    # ── Sustainability ───────────────────────────────────────────────────
    sustain_html = ""
    if mode == "Full Analysis" and "SUSTAINABILITY" in lines:
        sustain_html = f"""
        <div class="result-row">
            <div class="result-key">Sustainability</div>
            <div class="result-val">{lines["SUSTAINABILITY"]}</div>
        </div>"""

    if rows_html or outfit_html:
        st.markdown(
            f'<div class="panel">{rows_html}{outfit_html}{sustain_html}</div>',
            unsafe_allow_html=True,
        )
    else:
        # Fallback: show raw text
        st.markdown(
            f'<div class="panel"><div class="result-val" style="white-space:pre-wrap;">{raw}</div></div>',
            unsafe_allow_html=True,
        )

    # ── Verdict card ─────────────────────────────────────────────────────
    if mode != "Outfit Ideas":
        verdict_raw = lines.get("VERDICT", "").upper()
        reason = lines.get("REASON", "")

        if "BUY" in verdict_raw and "PASS" not in verdict_raw:
            v_class, v_label, v_sub = "verdict-buy", "Buy", f"${price:.2f} is a good deal."
        elif "PASS" in verdict_raw:
            v_class, v_label, v_sub = "verdict-pass", "Pass", f"Not worth ${price:.2f} — walk away."
        elif "NEGOTIATE" in verdict_raw:
            suggest = round(price * 0.65, 2)
            v_class  = "verdict-negotiate"
            v_label  = "Negotiate"
            v_sub    = f"Try to bring it down to ${suggest:.2f}."
        else:
            v_class = v_label = v_sub = ""

        if v_label:
            divider = '<div class="verdict-divider"></div>' if reason else ""
            reason_html = f'<div class="verdict-reason">{reason}</div>' if reason else ""

            st.markdown(f"""
            <div class="verdict-card {v_class}">
                <div>
                    <div class="verdict-label">{v_label}</div>
                    <div class="verdict-sub">{v_sub}</div>
                </div>
                {divider}
                {reason_html}
            </div>
            """, unsafe_allow_html=True)

            if v_label == "Buy":
                st.balloons()

    # ── Caption debug (collapsed) ─────────────────────────────────────────
    with st.expander("View raw image caption", expanded=False):
        st.markdown(
            f'<div style="font-size:0.8em;color:#6b6454;font-style:italic;">{caption}</div>',
            unsafe_allow_html=True
        )


def _map_error(err: str) -> str:
    """Convert raw exceptions into clean user-facing messages."""
    e = err.lower()
    if "401" in e or "unauthorized" in e:
        return "Authentication failed. The app owner needs to verify the HF_TOKEN in Streamlit Secrets."
    if "503" in e or "loading" in e or "currently loading" in e:
        return "The AI model is warming up. Please wait 30–60 seconds and try again."
    if "429" in e or "rate limit" in e or "quota" in e:
        return "Request limit reached. Please wait a moment and try again."
    if "413" in e or "too large" in e or "payload" in e:
        return "The image is too large. Please use a smaller or lower-resolution photo."
    if "timeout" in e or "timed out" in e:
        return "The request timed out. The free tier can be slow — please try again."
    return f"Something went wrong. Please try again. ({err[:120]})"


# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown("<div style='height:48px'></div>", unsafe_allow_html=True)
st.markdown("""
<div style="text-align:center; font-size:0.68em; letter-spacing:0.2em;
text-transform:uppercase; color:#2a2618; padding-bottom:24px;">
    ThriftScan AI &nbsp;·&nbsp; BLIP + Mistral &nbsp;·&nbsp; Free Tier
</div>
""", unsafe_allow_html=True)