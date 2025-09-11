# main.py

from flask import Flask, request, jsonify
import firebase_admin
from firebase_admin import credentials, firestore
import logging
import os
import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize Flask app
app = Flask(__name__)

# --- Firestore Connection Setup ---
db = None
try:
    cred = credentials.ApplicationDefault()
    firebase_admin.initialize_app(cred)
    logging.info("Firestore connected using Cloud Run environment credentials.")
    db = firestore.client()
except ValueError:
    try:
        if os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'):
            cred = credentials.Certificate(os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'))
            firebase_admin.initialize_app(cred)
            logging.info("Firestore connected using GOOGLE_APPLICATION_CREDENTIALS.")
            db = firestore.client()
        else:
            logging.warning("No GOOGLE_APPLICATION_CREDENTIALS found. Running in mock data mode.")
    except Exception as e:
        logging.error(f"Error initializing Firebase: {e}")
        logging.warning("Continuing without database connection. Using mock data.")


# --- Utility function to normalize Dialogflow parameters ---
def normalize_param(param):
    if isinstance(param, dict):
        # Handle name objects
        if 'original' in param:
            return param['original']
        elif 'name' in param:
            return param['name']
        # Handle time objects
        elif 'hours' in param and 'minutes' in param:
            hours = int(param.get('hours', 0))
            minutes = int(param.get('minutes', 0))
            return f"{hours:02d}:{minutes:02d}"
        else:
            return str(param)
    return str(param)


# --- Webhook Endpoint ---
@app.route('/webhook', methods=['POST'])
def webhook():
    """
    Handles POST requests from Dialogflow CX.
    Returns a fulfillment response.
    """
    req = request.get_json(silent=True, force=True)

    # Default fallback response
    fulfillment_response = {
        "fulfillmentResponse": {
            "messages": [
                {"text": {"text": ["I'm sorry, I didn't understand that. Could you please rephrase?"]}}
            ]
        }
    }

    try:
        # Extract intent display name safely
        intent_display_name = req.get('intentInfo', {}).get('displayName', '')

        parameters = req.get('sessionInfo', {}).get('parameters', {})

        # --- Pricing Membership Intent ---
        if intent_display_name == 'PricingMembershipIntent':
            card_text_message = {
                "text": {
                    "text": [
                        "Membership & Pricing\n\nChoose the plan that's right for you.\n\n"
                        "We offer a variety of flexible membership options. "
                        "Our current special is 50% off a 12-month membership until 2026! "
                        "Our most popular plan includes unlimited access to all facilities and classes."
                    ]
                }
            }
            chips_payload = {
                "richContent": [[{"type": "chips", "options": [{"text": "View Pricing Details"}, {"text": "Get a Quote"}]}]]
            }
            fulfillment_response = {
                "fulfillmentResponse": {"messages": [card_text_message, {"payload": chips_payload}]}
            }

        # --- View Pricing Intent ---
        elif intent_display_name == 'ViewPricingIntent':
            if db:
                doc_ref = db.collection('gyms').document('covent-garden-fitness-wellbeing-gym')
                doc = doc_ref.get()
                if doc.exists:
                    data = doc.to_dict()
                    anytime_prices = data.get('membership', {}).get('anytime', {})
                    twelve_month = anytime_prices.get('12MonthCommitment', {})
                    one_month_rolling = anytime_prices.get('1MonthRolling', {})
                    promotion = anytime_prices.get('promotion', {})

                    pricing_info = (
                        f"Pricing Details for {data.get('name', 'this gym')}\n\n"
                        f"Our flexible plans are designed to fit your lifestyle.\n\n"
                        f"1. 12-Month Commitment Plan\n"
                        f"   - Commitment: {twelve_month.get('commitment', 'N/A')}\n"
                        f"   - Price: {twelve_month.get('currency', 'GBP')} {twelve_month.get('discountPrice', 'N/A')} per {twelve_month.get('period', 'month')}\n"
                        f"   - Original Price: {twelve_month.get('currency', 'GBP')} {twelve_month.get('originalPrice', 'N/A')}\n"
                    )
                    if promotion.get('active'):
                        pricing_info += f"   - Promotion: {promotion.get('description', 'N/A')} ({promotion.get('condition', 'N/A')})\n\n"
                    pricing_info += (
                        f"2. 1-Month Rolling Plan\n"
                        f"   - Commitment: {one_month_rolling.get('commitment', 'N/A')}\n"
                        f"   - Price: {one_month_rolling.get('currency', 'GBP')} {one_month_rolling.get('price', 'N/A')} per {one_month_rolling.get('period', 'month')}\n\n"
                    )
                    card_text_message = {"text": {"text": [pricing_info]}}
                else:
                    card_text_message = {"text": {"text": ["Sorry, I could not find pricing details for this gym."]}}
            else:
                card_text_message = {"text": {"text": ["Sorry, the database is not connected."]}}
            chips_payload = {
                "richContent": [[{"type": "chips", "options": [{"text": "Get a Quote"}, {"text": "Join now"}]}]]
            }
            fulfillment_response = {"fulfillmentResponse": {"messages": [card_text_message, {"payload": chips_payload}]}}

        # --- Join Now Intent ---
        elif intent_display_name == 'JoinNowIntent':
            if db:
                doc_ref = db.collection('gyms').document('covent-garden-fitness-wellbeing-gym')
                doc = doc_ref.get()
                if doc.exists:
                    data = doc.to_dict()
                    twelve_month = data.get('membership', {}).get('anytime', {}).get('12MonthCommitment', {})
                    activation_fee = 29.00
                    monthly_remainder = 31.85
                    today_total = activation_fee + monthly_remainder
                    today_date = datetime.date.today()
                    today_day = today_date.strftime("%#d" if os.name == 'nt' else "%-d")
                    today_month = today_date.strftime("%B")
                    next_month = (today_date.replace(day=28) + datetime.timedelta(days=4)).strftime("%B")

                    join_text = (
                        f"We've defaulted the start date to the first available date you can join this gym:\n"
                        f"{today_day} {today_month}\n\n"
                        f"Activation Fee: £{activation_fee:.2f}\n"
                        f"For the remainder of this month: £{monthly_remainder:.2f}\n"
                        f"Monthly direct debit (Starting 1st {next_month} 2025): "
                        f"£{twelve_month.get('discountPrice', 'N/A'):.2f}\n"
                        f"(Just £{twelve_month.get('discountPrice', 'N/A'):.2f} per month for 3 months, then "
                        f"£{twelve_month.get('originalPrice', 'N/A'):.2f} per month from Jan 2026)\n"
                        f"To pay today: £{today_total:.2f}"
                    )
                    fulfillment_response = {"fulfillmentResponse": {"messages": [{"text": {"text": [join_text]}}]}}
                else:
                    fulfillment_response = {"fulfillmentResponse": {"messages": [{"text": {"text": ["Gym details not found."]}}]}}
            else:
                fulfillment_response = {"fulfillmentResponse": {"messages": [{"text": {"text": ["Database not connected."]}}]}}

        # --- Get Quote Intent ---
        elif intent_display_name == 'GetQuoteIntent':
            fulfillment_response = {
                "fulfillmentResponse": {
                    "messages": [
                        {"text": {"text": ["To get a personalized quote, please tell me your full name, email address, and a good time for a team member to contact you."]}}
                    ]
                }
            }

        # --- Submit Quote Form Intent ---
        elif intent_display_name == 'SubmitQuoteFormIntent':
            user_name = normalize_param(parameters.get('name'))
            user_email = normalize_param(parameters.get('email_address'))
            user_time = normalize_param(parameters.get('contact_time'))

            if db:
                try:
                    db.collection('quotes').add({
                        'name': user_name,
                        'email': user_email,
                        'contact_time': user_time,
                        'submission_timestamp': datetime.datetime.now()
                    })
                    confirmation_message = (
                        f"Thank you, {user_name}! We have received your request.\n"
                        f"A team member will be in touch with you at {user_time} at {user_email} to provide a tailored quote.\n"
                        f"We look forward to speaking with you!"
                    )
                    fulfillment_response = {"fulfillmentResponse": {"messages": [{"text": {"text": [confirmation_message]}}]}}
                except Exception as e:
                    logging.error(f"Error saving quote to Firestore: {e}")
                    fulfillment_response = {"fulfillmentResponse": {"messages": [{"text": {"text": ["Error saving your information. Please try again later."]}}]}}
            else:
                fulfillment_response = {"fulfillmentResponse": {"messages": [{"text": {"text": ["Database not connected. Cannot save information."]}}]}}

    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")

    return jsonify(fulfillment_response)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
