import streamlit as st
import requests
import json
import re
from datetime import datetime

# Define the Workflow webhook URL
WEBHOOK_URL = "https://prod-140.westus.logic.azure.com:443/workflows/b411851f8e484cc1979e8398536d77bf/triggers/manual/paths/invoke?api-version=2016-06-01&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=fQQ-yBNGDU1cAHw8UVpNYvfPibeCRgPfV6vdJuMnE7U"
NHTSA_API_URL = "https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVinValues/{vin}?format=json"

# Function to validate VIN format
def is_valid_vin(vin):
    if len(vin) != 17:
        return False, "VIN must be exactly 17 characters."
    if not re.match(r"^[A-HJ-NPR-Z0-9]{17}$", vin):
        return False, "VIN contains invalid characters (I, O, Q not allowed)."
    return True, ""

# Function to decode VIN using NHTSA API
def decode_vin(vin):
    try:
        response = requests.get(NHTSA_API_URL.format(vin=vin))
        if response.status_code == 200:
            data = response.json()
            results = data.get("Results", [])[0]
            if results.get("ErrorCode") == "0":
                return True, {
                    "Make": results.get("Make", "Unknown"),
                    "Model": results.get("Model", "Unknown"),
                    "Year": results.get("ModelYear", "Unknown")
                }
            else:
                return False, f"VIN decode failed: {results.get('ErrorText', 'Unknown error')}"
        else:
            return False, f"NHTSA API error: {response.status_code}"
    except Exception as e:
        return False, f"Error contacting NHTSA API: {str(e)}"

# Streamlit app title
st.title("REQUEST SERVICE LINCOLN" )

# Create a form
with st.form(key="repair_request_form"):
    repair_order = st.text_input("Repair Order #")
    shop_name = st.text_input("Shop Name")
    vin_number = st.text_input("VIN #", max_chars=17)
    request_description = st.text_area("Request Description", height=150)
    earliest_start_date = st.date_input("Earliest Start Date Requested", min_value=datetime.today())
    submit_button = st.form_submit_button(label="Submit Request")

# Handle form submission
if submit_button:
    if not all([repair_order, shop_name, vin_number, request_description, earliest_start_date]):
        st.error("Please fill out all fields.")
    else:
        vin_valid, vin_error = is_valid_vin(vin_number.upper())
        if not vin_valid:
            st.error(vin_error)
        else:
            vin_decoded, vin_result = decode_vin(vin_number)
            if not vin_decoded:
                st.error(vin_result)
            else:
                formatted_date = earliest_start_date.strftime("%Y-%m-%d")
                payload = {
                    "type": "message",
                    "attachments": [
                        {
                            "contentType": "application/vnd.microsoft.card.adaptive",
                            "content": {
                                "type": "AdaptiveCard",
                                "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                                "version": "1.0",
                                "body": [
                                    {"type": "TextBlock", "text": "New Repair Request", "weight": "Bolder", "size": "Medium"},
                                    {"type": "TextBlock", "text": f"**Repair Order #:** {repair_order}", "wrap": True},
                                    {"type": "TextBlock", "text": f"**Shop Name:** {shop_name}", "wrap": True},
                                    {"type": "TextBlock", "text": f"**VIN #:** {vin_number}", "wrap": True},
                                    {"type": "TextBlock", "text": f"**Vehicle Details:** {vin_result['Year']} {vin_result['Make']} {vin_result['Model']}", "wrap": True},
                                    {"type": "TextBlock", "text": f"**Request Description:** {request_description}", "wrap": True},
                                    {"type": "TextBlock", "text": f"**Earliest Start Date Requested:** {formatted_date}", "wrap": True}
                                ]
                            }
                        }
                    ]
                }
                try:
                    response = requests.post(
                        WEBHOOK_URL,
                        headers={"Content-Type": "application/json"},
                        data=json.dumps(payload)
                    )
                    if response.status_code == 202:
                        st.success("Your repair request has been submitted successfully!")
                        st.write(f"Decoded VIN: {vin_result['Year']} {vin_result['Make']} {vin_result['Model']}")
                    else:
                        st.error(f"Failed to submit request. Error: {response.status_code} - {response.text}")
                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")

