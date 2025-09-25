import json
import os
import requests
from flask import Flask, request, jsonify
import firebase_admin
from firebase_admin import credentials, firestore
import logging
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

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handles a POST request from a Dialogflow CX agent."""
    req = request.get_json(silent=True, force=True)

    # Default fallback response
    fulfillment_response = {
        "fulfillmentResponse": {
            "messages": [
                {"text": {"text": ["I'm sorry, I didn't understand that. Could you please rephrase?"]}}
            ]
        }
    }

    # Chips to display at the end of the flow
    final_chips_payload = {
        "richContent": [
            [
                {
                    "type": "chips",
                    "options": [
                        {"text": "Feedback"},
                        {"text": "Recommendation"}
                    ]
                }
            ]
        ]
    }

    try:
        # Extract intent (if present) and session parameters
        intent_display_name = req.get("intentInfo", {}).get("displayName")
        parameters = req.get("sessionInfo", {}).get("parameters", {})

        # --- PricingMembershipIntent ---
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
                "richContent": [
                    [
                        {
                            "type": "chips",
                            "options": [
                                {"text": "View Pricing Details"},
                                {"text": "Get a Quote"}
                            ]
                        }
                    ]
                ]
            }
            fulfillment_response = {
                "fulfillmentResponse": {
                    "messages": [card_text_message, {"payload": chips_payload}]
                }
            }

        # --- ViewPricingIntent ---
        elif intent_display_name == 'ViewPricingIntent':
            card_text_message = {"text": {"text": ["Sorry, I could not find pricing details for this gym."]}}
            if db is not None:
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
                        "Our flexible plans are designed to fit your lifestyle.\n\n"
                        "1. 12-Month Commitment Plan\n"
                        f"   - Commitment: {twelve_month.get('commitment', 'N/A')}\n"
                        f"   - Price: {twelve_month.get('currency', 'GBP')} {twelve_month.get('discountPrice', 'N/A')} per {twelve_month.get('period', 'month')}\n"
                        f"   - Original Price: {twelve_month.get('currency', 'GBP')} {twelve_month.get('originalPrice', 'N/A')}\n"
                    )
                    if promotion.get('active'):
                        pricing_info += f"   - Promotion: {promotion.get('description', 'N/A')} ({promotion.get('condition', 'N/A')})\n\n"
                    else:
                        pricing_info += "\n"

                    pricing_info += (
                        "2. 1-Month Rolling Plan\n"
                        f"   - Commitment: {one_month_rolling.get('commitment', 'N/A')}\n"
                        f"   - Price: {one_month_rolling.get('currency', 'GBP')} {one_month_rolling.get('price', 'N/A')} per {one_month_rolling.get('period', 'month')}\n\n"
                    )
                    card_text_message = {"text": {"text": [pricing_info]}}
                else:
                    card_text_message = {"text": {"text": ["Sorry, I could not find pricing details for this gym."]}}
            else:
                card_text_message = {"text": {"text": ["Sorry, the database is not connected. I cannot provide pricing details at this time."]}}

            # Add the final chips to the response
            final_chips = {
                "richContent": [
                    [
                        {
                            "type": "chips",
                            "options": [
                                {"text": "Get a Quote"},
                                {"text": "Join now"}
                            ]
                        }
                    ]
                ]
            }
            fulfillment_response = {"fulfillmentResponse": {"messages": [card_text_message, {"payload": final_chips}, {"payload": final_chips_payload}]}}


        # --- JoinNowIntent ---
        elif intent_display_name == 'JoinNowIntent':
            card_text_message = {"text": {"text": ["Sorry, I could not find details to join this gym."]}}
            if db is not None:
                doc_ref = db.collection('gyms').document('covent-garden-fitness-wellbeing-gym')
                doc = doc_ref.get()
                if doc.exists:
                    data = doc.to_dict()
                    anytime_prices = data.get('membership', {}).get('anytime', {})
                    twelve_month = anytime_prices.get('12MonthCommitment', {})

                    activation_fee = 29.00
                    monthly_remainder = 31.85
                    today_total = activation_fee + monthly_remainder

                    today_date = datetime.date.today()
                    today_day = today_date.strftime("%#d" if os.name == 'nt' else "%-d")
                    today_month = today_date.strftime("%B")
                    next_month = (today_date.replace(day=28) + datetime.timedelta(days=4)).strftime("%B")

                    join_details_text = (
                        f"We've defaulted the start date to the first available date you can join this gym:\n"
                        f"{today_day} {today_month}\n\n"
                        f"Activation Fee:\n£{activation_fee:.2f}\n"
                        f"For the remainder of this month:\n£{monthly_remainder:.2f}\n"
                        f"Monthly direct debit (Starting 1st {next_month} 2025)\n"
                        f"£{twelve_month.get('originalPrice', 'N/A'):.2f}\n"
                        f"£{twelve_month.get('discountPrice', 'N/A'):.2f}\n"
                        f"-50% promotional discount\n"
                        f"(Just £{twelve_month.get('discountPrice', 'N/A'):.2f} per month for 3 months, "
                        f"then £{twelve_month.get('originalPrice', 'N/A'):.2f} per month from 1 January 2026)\n"
                        f"To pay today:\n£{today_total:.2f}"
                    )
                    card_text_message = {"text": {"text": [join_details_text]}}
            else:
                card_text_message = {"text": {"text": ["Sorry, the database is not connected. I cannot provide details to join at this time."]}}

            fulfillment_response = {"fulfillmentResponse": {"messages": [card_text_message, {"payload": final_chips_payload}]}}

        # --- GetQuoteIntent ---
        elif intent_display_name == 'GetQuoteIntent':
            fulfillment_response = {
                "fulfillmentResponse": {
                    "messages": [
                        {"text": {"text": ["To get a personalized quote, please tell me your full name, email address, and a good time for a team member to contact you. Our team will be in touch within 24 hours to provide you with a tailored quote. What is your full name?"]}}
                    ]
                }
            }

        # --- SubmitQuoteFormIntent OR Form FINAL handling ---
        elif intent_display_name == 'SubmitQuoteFormIntent' or (
            parameters.get("name") and parameters.get("email_address") and parameters.get("contact_time")
        ):
            confirmation_message = "Sorry, I encountered an issue while saving your information. Please try again later."
            if db is not None:
                try:
                    user_name_dict = parameters.get('name', {})
                    user_name = user_name_dict.get('original')
                    
                    user_email = parameters.get('email_address')
                    
                    user_time_dict = parameters.get('contact_time', {})
                    user_time = f"{int(user_time_dict.get('hours', 0))}:{int(user_time_dict.get('minutes', 0)):02d}"

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
                except Exception as e:
                    logging.error(f"Error saving quote to Firestore: {e}")
            else:
                confirmation_message = "Sorry, the database is not connected. I cannot save your information at this time."

            fulfillment_response = {"fulfillmentResponse": {"messages": [{"text": {"text": [confirmation_message]}}, {"payload": final_chips_payload}]}}
    
    except Exception as e:
        logging.error(f"Webhook error: {e}")

    return jsonify(fulfillment_response)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
