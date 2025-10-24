# Bewerber-Agent CH Cloud API v1
# by Stefan Mosimann
#
# Aufgabe:
# - Nimmt Rolle / Stadt / Radius entgegen
# - Fragt OpenAI (Web-Agent) nach passenden Schweizer Jobangeboten
# - Liefert ein pures JSON-Array zurück, das dein lokaler Bewerber-Agent direkt importieren kann

from flask import Flask, request, jsonify
import os
import json
import openai

app = Flask(__name__)

# OpenAI API Key muss bei Render unter Environment Variables gesetzt werden:
# Name: OPENAI_API_KEY
openai.api_key = os.getenv("OPENAI_API_KEY", "")

SYSTEM_PROMPT = (
    "Du bist ein Schweizer Job-Sourcing-Agent. "
    "Du suchst NUR in der Schweiz nach aktuellen Stellenangeboten "
    "(jobs.ch, jobup.ch, indeed.ch, etc.). "
    "Deine Antwort MUSS ein valides JSON-Array sein. "
    "KEIN Text davor, kein Text danach."
)

USER_TEMPLATE = (
    "Parameter:\n"
    "Rolle: {role}\n"
    "Stadt: {city}\n"
    "Radius: {radius} km\n\n"
    "Bitte gib mir eine Liste von passenden Schweizer Stelleninseraten "
    "im folgenden Format (ohne Erklärtext, nur JSON):\n"
    "[\n"
    "  {\n"
    "    \"id\": \"web_1\",\n"
    "    \"title\": \"Elektriker EFZ\",\n"
    "    \"company\": \"Elektro Basel AG\",\n"
    "    \"location\": {\n"
    "      \"city\": \"Basel\",\n"
    "      \"country\": \"CH\"\n"
    "    },\n"
    "    \"required_skills\": [\"EFZ\", \"Schaltschränke\", \"KNX\"],\n"
    "    \"nice_skills\": [\"PV\"],\n"
    "    \"min_experience_years\": 2,\n"
    "    \"languages\": [{\"code\": \"de\", \"level\": \"B2\"}],\n"
    "    \"driver_license_required\": true,\n"
    "    \"description\": \"Kurzbeschreibung der Aufgabe / Verantwortung (max 300 Zeichen)\",\n"
    "    \"canton\": \"BS\",\n"
    "    \"url\": \"https://example.com/job-12345\"\n"
    "  }\n"
    "]\n\n"
    "REGELN:\n"
    "- country MUSS immer \"CH\" sein.\n"
    "- url MUSS die Originalausschreibung sein.\n"
    "- description max. 300 Zeichen.\n"
    "- KEINE extra Kommentare, KEIN Markdown, NUR JSON."
)

@app.route('/', methods=['GET'])
def root():
    return jsonify({
        "status": "ok",
        "service": "Bewerber-Agent CH Cloud API v1 – by Stefan Mosimann",
        "message": "Nutze POST /api/search mit JSON body {role, city, radius}"
    })

@app.route('/api/search', methods=['POST'])
def api_search():
    body = request.get_json(force=True, silent=True) or {}
    role = body.get("role", "Elektriker EFZ")
    city = body.get("city", "Basel")
    radius = body.get("radius", 20)

    # Falls kein API-Key hinterlegt ist -> klare Fehlermeldung
    if not openai.api_key:
        return jsonify({
            "error": "OPENAI_API_KEY fehlt auf dem Server",
            "hint": "Bitte Environment Variable setzen."
        }), 500

    user_prompt = USER_TEMPLATE.format(role=role, city=city, radius=radius)

    # Aufruf OpenAI Chat Completions
    try:
        completion = openai.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.2,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ]
        )
        raw_text = completion.choices[0].message.content.strip()
    except Exception as e:
        return jsonify({
            "error": "Fehler bei OpenAI Anfrage",
            "details": str(e)
        }), 500

    # Sicherstellen, dass wir wirklich JSON zurückgeben
    try:
        data = json.loads(raw_text)
        if not isinstance(data, list):
            raise ValueError("Antwort ist kein JSON-Array")
        # Optional: kleine Säuberung, truncate description
        cleaned = []
        for idx, job in enumerate(data, start=1):
            j = dict(job)
            desc = (j.get("description") or "").strip()
            if len(desc) > 300:
                desc = desc[:300]
            j["description"] = desc
            # Fallbacks
            if "id" not in j:
                j["id"] = f"web_{idx}"
            if "location" in j and isinstance(j["location"], dict):
                j["location"]["country"] = "CH"
            cleaned.append(j)
        return jsonify(cleaned)
    except Exception:
        # Falls OpenAI uns doch Text drumrum gibt -> als raw zurück
        return jsonify({
            "error": "Antwort war kein valides JSON-Array",
            "raw": raw_text
        }), 502

if __name__ == '__main__':
    # Lokaler Test: python app.py  -> http://127.0.0.1:10000
    app.run(host='0.0.0.0', port=10000)
