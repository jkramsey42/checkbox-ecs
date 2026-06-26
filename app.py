import os
import json
from datetime import datetime, timezone

from flask import Flask, request, jsonify
import gspread
from google.oauth2.service_account import Credentials


app = Flask(__name__)

SPREADSHEET_ID = os.environ["SPREADSHEET_ID"]
WORKSHEET_NAME = os.environ.get("WORKSHEET_NAME", "Sheet1")
GOOGLE_APPLICATION_CREDENTIALS = os.environ.get(
    "GOOGLE_APPLICATION_CREDENTIALS",
    "/etc/secrets/service_account.json"
)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def get_worksheet():
    creds = Credentials.from_service_account_file(
        GOOGLE_APPLICATION_CREDENTIALS,
        scopes=SCOPES
    )
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SPREADSHEET_ID)
    return sheet.worksheet(WORKSHEET_NAME)


def get_value(data, *possible_keys):
    """
    Tries several possible Checkbox field names and returns the first match.
    Useful while adapting to a new questionnaire.
    """
    for key in possible_keys:
        if key in data:
            return data.get(key)
    return ""


@app.route("/", methods=["GET"])
def home():
    return "Checkbox webhook app is running."


@app.route("/checkbox-webhook", methods=["POST"])
def checkbox_webhook():
    data = request.get_json(silent=True)

    if data is None:
        data = request.form.to_dict()

    print("Incoming Checkbox payload:")
    print(json.dumps(data, indent=2, default=str))

    worksheet = get_worksheet()

    row = [
        datetime.now(timezone.utc).isoformat(),
        get_value(data, "survey_name", "SurveyName", "surveyTitle"),
        get_value(data, "numericid", "NumericID", "respondentid"),
        get_value(data, "language", "Language", "Language"),
        get_value(data, "orgname", "orgname", "orgname"),
        get_value(data, "jobcat", "jobcat", "jobcat"),

        get_value(data, "first_name", "FirstName", "firstName"),
        get_value(data, "last_name", "LastName", "lastName"),
        get_value(data, "email", "Email", "email"),
        get_value(data, "q1", "Q1"),
        get_value(data, "q2", "Q2"),
        get_value(data, "q3", "Q3"),
    ]

    worksheet.append_row(row, value_input_option="USER_ENTERED")

    return jsonify({"status": "success"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
