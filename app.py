from flask import Flask, request, jsonify
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import json
import os

app = Flask(__name__)

# === CONFIGURATION ===
# Replace with your actual spreadsheet ID
SPREADSHEET_ID = "1UQtc6_iIJ5IVbdjwVgEV17MZ_0kyQ-CCc7_-LDOpL_E"
WORKSHEET_NAME = "Sheet1"  # or whatever the tab is called

# Google Sheets setup
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

# Assumes the JSON key file is in the same folder, named service_account.json
creds = ServiceAccountCredentials.from_json_keyfile_name(
    "service_account.json", scope
)
gclient = gspread.authorize(creds)
sheet = gclient.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_NAME)

def to_int_or_none(val):
    """Try to convert a value to int; if it fails or is empty, return None."""
    if val is None:
        return None
    if isinstance(val, int):
        return val
    s = str(val).strip()
    if s == "":
        return None
    try:
        return int(s)
    except ValueError:
        return None

def parse_gender(val):
    """Map gender to numeric code:
       1, 2 as-is; 'Prefer to specify: ...' => 3; otherwise None."""
    if val is None:
        return None

    # If it's already like "1" or "2"
    if str(val).strip() in ("1", "2"):
        return int(str(val).strip())

    # Handle "Prefer to specify: something"
    s = str(val).strip()
    if s.lower().startswith("prefer to specify:"):
        return 3

    # Fallback if something unexpected comes through
    return None


def bool_to_01(val):
    """Convert booleans / boolean-like values to 1/0; return None if unknown."""
    if isinstance(val, bool):
        return 1 if val else 0
    if val is None:
        return None
    s = str(val).strip().lower()
    if s in ("true", "1", "yes", "y"):
        return 1
    if s in ("false", "0", "no", "n"):
        return 0
    return None

@app.route("/checkbox-webhook", methods=["POST"])
def checkbox_webhook():
    """
    Endpoint that Checkbox will POST to when someone completes a survey.
    """
    try:
        data = request.get_json(force=True, silent=False)
    except Exception as e:
        # If JSON parsing fails
        return jsonify({"status": "error", "message": f"Invalid JSON: {e}"}), 400

    # --- Inspect the payload structure on first run ---
    # For debugging: print to logs so you can see what Checkbox sends
    print("Received payload:", json.dumps(data, indent=2))

    # You will need to adjust these keys based on Checkbox's actual payload.
    # For now, we guess at some common fields and fall back to "Unknown".
    # survey_name = data.get("SurveyName") or data.get("surveyName") or "UnknownSurvey"
    # response_id = data.get("ResponseId") or data.get("responseId") or "UnknownResponse"
    client_name_from_header = request.headers.get("orgname", "UnknownClient")
    CSU_name_from_header = request.headers.get("CSU", "UnknownCSU")
    numeric_id = data.get("NumericId", "UnknownNumericID")

    # =========================================================
    # ITEM VALUES 1–8
    # =========================================================
    item_values = []
    for i in range(1, 9):
        key = f"Please indicate your level of agreement with the following items._item{i}_Column2"
        item_values.append(to_int_or_none(data.get(key)))

    (
        item1, item2, item3, item4,
        item5, item6, item7, item8
    ) = item_values

    # =========================================================
    # DEMOGRAPHICS
    # =========================================================
    #gender = to_int_or_none(data.get("gender"))
    gender = parse_gender(data.get("gender"))
    age = to_int_or_none(data.get("age"))

    race1 = bool_to_01(data.get("race_1"))
    race2 = bool_to_01(data.get("race_2"))
    race3 = bool_to_01(data.get("race_3"))
    race4 = bool_to_01(data.get("race_4"))
    race5 = bool_to_01(data.get("race_5"))
    race6 = bool_to_01(data.get("race_6"))
    race7 = bool_to_01(data.get("race_7"))
    race_other_text = data.get("race_Other:")

    timestamp = datetime.utcnow().isoformat()
    raw_payload_str = json.dumps(data)

    row = [
        timestamp,
        client_name_from_header,
        CSU_name_from_header,
        numeric_id,
        item1,
        item2,
        item3,
        item4,
        item5,
        item6,
        item7,
        item8,
        gender,
        age,
        race1,
        race2,
        race3,
        race4,
        race5,
        race6,
        race7,
        race_other_text,
        raw_payload_str,
    ]

    try:
        sheet.append_row(row, value_input_option="RAW")
    except Exception as e:
        print("Error writing to Google Sheet:", e)
        return jsonify({"status": "error", "message": "Failed to write to sheet"}), 500

    # Checkbox just needs a 200 OK or similar
    return jsonify({"status": "success"}), 200


@app.route("/", methods=["GET"])
def health_check():
    return "Checkbox webhook receiver is running.", 200


if __name__ == "__main__":
    # For local testing only; in production use gunicorn or similar
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)








