import os
import requests
from flask import Flask, render_template, request, jsonify
from groq import Groq
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# --- Configuration ---
try:
    groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
except Exception as e:
    print(f"Error initializing Groq client: {e}")
    groq_client = None

# API for Tafsir (Commentary)
TAFSIR_API_BASE_URL = "https://cdn.jsdelivr.net/gh/spa5k/tafsir_api@main/tafsir"
TAFSIR_SOURCES = {
    "context": "en-kashf-al-asrar-tafsir",
    "classical": "en-tafisr-ibn-kathir",
    "modern": "en-tafsir-maarif-ul-quran"
}
DATA_UNAVAILABLE_MESSAGE = "Information from this source is currently unavailable or not found for this verse."

# API for Quran Text and Translation
QURAN_API_BASE_URL = "http://api.alquran.cloud/v1/ayah"

def get_ayah_text(surah: int, ayah: int) -> str:
    """Fetches the English translation of a specific ayah."""
    url = f"{QURAN_API_BASE_URL}/{surah}:{ayah}/en.asad"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data.get('code') == 200 and data.get('data', {}).get('text'):
            return data['data']['text']
        else:
            return "Could not retrieve the translation for this verse."
    except requests.exceptions.RequestException as e:
        print(f"Error fetching Ayah text: {e}")
        return "Could not retrieve the translation due to a network error."

def get_tafsir_data(surah: int, ayah: int) -> dict:
    """Fetches commentary with robust error handling."""
    collected_data = {}
    for source_name, source_slug in TAFSIR_SOURCES.items():
        url = f"{TAFSIR_API_BASE_URL}/{source_slug}/{surah}/{ayah}.json"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            text = data.get("text", "").strip()
            collected_data[source_name] = text if text else DATA_UNAVAILABLE_MESSAGE
        except requests.exceptions.RequestException as e:
            print(f"Error fetching Tafsir from {source_slug}: {e}")
            collected_data[source_name] = DATA_UNAVAILABLE_MESSAGE
    return collected_data

def generate_explanation_prompt(surah: int, ayah: int, ayah_text: str, tafsir_data: dict) -> str:
    """
    Constructs a more direct and forceful prompt to ensure the Ayah is printed.
    """
    # --- MODIFICATION START: This entire function is rewritten for clarity and forcefulness ---

    # Start with a clear definition of the persona and overall goal.
    prompt = f"""You are a helpful and knowledgeable assistant for Quranic studies. Your primary task is to provide a clear, multi-source explanation for Surah {surah}, Ayah {ayah}.

**Your response MUST be structured in the following order:**

**1. The Verse:**
   - Start with the heading "### The Verse (Surah {surah}: Ayah {ayah})".
   - Immediately after the heading, quote the English translation of the verse provided below.

**2. The Explanation:**
   - Based on the data provided, generate a detailed explanation. You must attribute every piece of information to its source using phrases like "According to Al-Wahidi...", "Ibn Kathir explains that...", etc.
   - If the 'Shan-e-Nazool' (reason for revelation) from Al-Wahidi is available, present it first under the heading "### Shan-e-Nazool (Reason for Revelation)".
   - If it is unavailable, DO NOT mention the unavailability. Simply proceed to the next section.
   - Present the commentary from Tafsir Ibn Kathir under the heading "### Classical Commentary: Tafsir Ibn Kathir".
   - Present the commentary from Maarif-ul-Quran under the heading "### Modern Commentary: Maarif-ul-Quran".

**3. Summary:**
   - Conclude with a brief summary under the heading "### Summary".

---
**DATA FOR YOUR TASK:**

**[Verse Translation]:**
{ayah_text}

**[Al-Wahidi's Asbab Al-Nuzul]:**
{tafsir_data.get('context')}

**[Tafsir Ibn Kathir]:**
{tafsir_data.get('classical')}

**[Maarif-ul-Quran]:**
{tafsir_data.get('modern')}
---

Begin your response now.
"""
    # --- MODIFICATION END ---
    return prompt

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/explain', methods=['POST'])
def explain_ayah():
    if not groq_client:
        return jsonify({"error": "Groq client is not initialized. Check API key."}), 500

    data = request.get_json()
    if not data or 'surah' not in data or 'ayah' not in data:
        return jsonify({"error": "Missing Surah or Ayah number"}), 400

    try:
        surah = int(data['surah'])
        ayah = int(data['ayah'])
    except (ValueError, TypeError):
        return jsonify({"error": "Surah and Ayah must be numbers"}), 400
    
    ayah_text = get_ayah_text(surah, ayah)
    tafsir_data = get_tafsir_data(surah, ayah)
    prompt = generate_explanation_prompt(surah, ayah, ayah_text, tafsir_data)
    
    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            # MODIFICATION: Using the model name that is confirmed to be available and powerful.
            model="llama-3.3-70b-versatile", 
            temperature=0.6, # Slightly reduced for more factual consistency
            max_tokens=2048,
        )
        explanation = chat_completion.choices[0].message.content
        return jsonify({"explanation": explanation})
    except Exception as e:
        print(f"Error calling Groq API: {e}")
        return jsonify({"error": f"Failed to get explanation from the language model: {e}"}), 500


#llama-3.3-70b-versatile