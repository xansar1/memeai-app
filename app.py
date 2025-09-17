# app.py
import os
import random
import requests
import urllib.parse
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont
import streamlit as st

# Optional: OpenAI for captions
try:
    import openai
except Exception:
    openai = None

# ----- Page config -----
st.set_page_config(page_title="MemeAI — Instant AI Meme Generator", page_icon="🤖", layout="centered")
st.title("🤖 MemeAI — Instant AI Meme Generator")
st.markdown(
    "Type a topic or phrase, generate a funny meme caption, and share it. "
    "OpenAI key is optional (better captions if present)."
)

# ----- Helpers -----
MEME_TEMPLATES = [
    "drake", "distracted-boyfriend", "two-buttons", "futurama-fry", "success-kid",
    "doge", "one-does-not-simply", "gru", "mocking-spongebob", "rollsafe"
]

def get_openai_key_from_env_or_input():
    key = os.getenv("OPENAI_API_KEY", "")
    if not key:
        key = st.text_input("OpenAI API key (optional — will improve captions)", type="password")
    return key.strip()

def parse_caption_output(text):
    text = text.strip()
    top, bottom = "", ""
    if "TOP:" in text.upper() or "BOTTOM:" in text.upper():
        for line in text.splitlines():
            up = line.upper()
            if up.startswith("TOP:"):
                top = line.split(":",1)[1].strip()
            elif up.startswith("BOTTOM:"):
                bottom = line.split(":",1)[1].strip()
    elif "\n" in text:
        parts = [p.strip() for p in text.splitlines() if p.strip()]
        if len(parts) >= 2:
            top, bottom = parts[0], parts[1]
        else:
            top = parts[0]
    else:
        words = text.split()
        mid = max(1, len(words)//2)
        top = " ".join(words[:mid])
        bottom = " ".join(words[mid:])
    return top, bottom

def fallback_caption(prompt):
    punch_templates = [
        ("When you", "but your code says no"),
        ("Me trying to", "vs reality"),
        ("Expectation:", "Reality:"),
        ("When the deadline is", "and you haven't started")
    ]
    t = random.choice(punch_templates)
    top = f"{prompt} — {t[0]}" if prompt else t[0]
    bottom = t[1]
    return top, bottom

def generate_caption(prompt, openai_key=None):
    if not openai_key or not openai:
        return fallback_caption(prompt)
    try:
        openai.api_key = openai_key
        system = (
            "You are a witty meme caption generator. Produce two short lines: "
            "a TOP caption and a BOTTOM caption. Keep them punchy, family-friendly, "
            "and suitable for a meme. Return with TOP: ... and BOTTOM: ...."
        )
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": f"Create a meme caption for: {prompt}"}
        ]
        resp = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.9,
            max_tokens=80
        )
        text = resp.choices[0].message.content
        top, bottom = parse_caption_output(text)
        if not top and not bottom:
            return fallback_caption(prompt)
        return top, bottom
    except Exception:
        return fallback_caption(prompt)

def make_memegen_url(template, top, bottom):
    def enc(s):
        return urllib.parse.quote(s, safe='') if s else "_"
    return f"https://api.memegen.link/images/{template}/{enc(top)}/{enc(bottom)}.png"

def download_image_bytes(url):
    res = requests.get(url, timeout=10)
    res.raise_for_status()
    return res.content

def add_watermark(image_bytes, watermark_text):
    img = Image.open(BytesIO(image_bytes)).convert("RGBA")
    width, height = img.size
    txt_layer = Image.new("RGBA", img.size, (255,255,255,0))
    draw = ImageDraw.Draw(txt_layer)
    font_size = max(16, width // 25)
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        font = ImageFont.load_default()

    # use textbbox instead of deprecated textsize
    bbox = draw.textbbox((0, 0), watermark_text, font=font)
    text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]

    x = width - text_w - 10
    y = height - text_h - 10
    draw.rectangle((x-6, y-6, x+text_w+6, y+text_h+6), fill=(0,0,0,120))
    draw.text((x, y), watermark_text, font=font, fill=(255,255,255,200))
    out = Image.alpha_composite(img, txt_layer)
    buf = BytesIO()
    out.convert("RGB").save(buf, format="PNG")
    return buf.getvalue()

def make_share_links(meme_url, caption_text):
    t = urllib.parse.quote(caption_text)
    u = urllib.parse.quote(meme_url)
    return {
        "Twitter": f"https://twitter.com/intent/tweet?text={t}&url={u}",
        "WhatsApp": f"https://api.whatsapp.com/send?text={urllib.parse.quote(caption_text + ' ' + meme_url)}",
        "Reddit": f"https://www.reddit.com/submit?title={t}&url={u}"
    }

# ----- UI -----
with st.sidebar:
    st.header("Options")
    openai_key = get_openai_key_from_env_or_input()
    template = st.selectbox("Meme template", MEME_TEMPLATES)
    random_template = st.checkbox("Use random template", value=False)
    watermark = st.checkbox("Add watermark to downloaded image", value=True)
    watermark_text = st.text_input("Watermark text", value="MemeAI.app")

prompt = st.text_input("Enter a topic / line (e.g. 'When your code runs first try')", value="")
col1, col2 = st.columns([1,1])
with col1:
    generate_btn = st.button("Generate Meme")
with col2:
    random_btn = st.button("Surprise me (random prompt)")

if random_btn:
    sample_prompts = [
        "When the coffee kicks in",
        "When deadline is tomorrow",
        "When you fix a bug at 3 AM",
        "Me explaining AI to my family",
        "When WiFi resumes after outage"
    ]
    prompt = random.choice(sample_prompts)
    st.rerun()  # ✅ fixed

if generate_btn:
    if not prompt:
        st.info("Type a prompt first (or use Surprise me).")
    else:
        if random_template:
            template = random.choice(MEME_TEMPLATES)
        with st.spinner("Generating caption..."):
            top, bottom = generate_caption(prompt, openai_key)
        st.success("Caption ready!")
        st.write("**Top:**", top)
        st.write("**Bottom:**", bottom)
        meme_url = make_memegen_url(template, top, bottom)
        st.markdown("**Preview:**")
        try:
            img_bytes = download_image_bytes(meme_url)
            # use_container_width replaces deprecated use_column_width
            st.image(img_bytes, use_container_width=True)
            if watermark:
                wm_bytes = add_watermark(img_bytes, watermark_text)
                st.download_button("⬇️ Download (watermarked)", wm_bytes, file_name="meme.png", mime="image/png")
            else:
                st.download_button("⬇️ Download", img_bytes, file_name="meme.png", mime="image/png")
            share_txt = f"{top} / {bottom}"
            links = make_share_links(meme_url, share_txt)
            st.markdown("**Share:**")
            cols = st.columns(3)
            for i, (name, url) in enumerate(links.items()):
                cols[i].markdown(f"[{name}]({url})")
        except Exception as e:
            st.error(f"Failed to fetch meme image: {e}")

# ----- Footer -----
st.markdown("---")
st.caption("Made with ❤️ by Ansar")
