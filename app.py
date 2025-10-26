from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
import os, json

app = Flask(__name__)
CORS(app)

from openai import OpenAI
import os

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "ok",
        "message": "Nutze POST /api/search mit JSON body (role, city, radius)",
        "service": "Bewerber-Agent CH Cloud API v2"
    })

@app.route("/api/search", methods=["POST"])
def api_search():
    try:
        body = request.get_json(force=True)
        role = body.get("role", "")
        city = body.get("city", "")
        radius = body.get("radius", 20)
    except Exception:
        return jsonify({"error": "Ungültige JSON-Eingabe"}), 400

    prompt = f"""
    Du bist ein Schweizer Job-Scout. Suche im gesamten Internet nach aktuellen Stellenangeboten in der Schweiz.

    Anforderungen:
    - Beruf/Rolle: {role}
    - Ort: {city}
    - Umkreis: {radius} km
    - Sprache: Deutsch
    - Rückgabeformat: JSON-Liste, KEIN Fließtext!

    Format:
    [
      {{
        "title": "Jobtitel",
        "company": "Firma",
        "city": "Ort",
        "url": "https://...",
        "source": "Plattformname"
      }}
    ]

    Durchsuche bevorzugt: jobs.ch, jobup.ch, jobscout24.ch, indeed.ch, job-room.ch
    """

    try:
        completion = client.responses.create(
            model="gpt-4.1",
            reasoning={"effort": "medium"},
            input=prompt,
            max_output_tokens=800
        )
        result_text = completion.output_text.strip()

        if not result_text.startswith("["):
            return jsonify({"error": "Keine validen Jobdaten erhalten", "raw": result_text}), 500

        jobs = json.loads(result_text)
        return jsonify(jobs)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

