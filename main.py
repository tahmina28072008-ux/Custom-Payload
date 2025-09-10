# webhook.py

from flask import Flask, request, jsonify
import firebase_admin
from firebase_admin import credentials, firestore
import logging
import os

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

# This is the endpoint that Dialogflow will call.
@app.route('/webhook', methods=['POST'])
def webhook():
    """
    Handles a POST request from a Dialogflow CX agent.
    Parses the request and returns a fulfillment response.
    """
    # Get the JSON request body
    req = request.get_json(silent=True, force=True)
    
    # Initialize a default response.
    fulfillment_response = {
        "fulfillmentResponse": {
            "messages": [
                {
                    "text": {
                        "text": [
                            "I'm sorry, I didn't understand that. Could you please rephrase?"
                        ]
                    }
                }
            ]
        }
    }

    try:
        # Extract the intent display name from the request
        intent_display_name = req['intentInfo']['displayName']

        # Check if the intent is "PricingMembershipIntent"
        if intent_display_name == 'PricingMembershipIntent':
            # This is the text message containing the card details
            card_text_message = {
                "text": {
                    "text": [
                        "Membership & Pricing\n\nChoose the plan that's right for you.\n\nWe offer a variety of flexible membership options. Our current special is 50% off a 12-month membership until 2026! Our most popular plan includes unlimited access to all facilities and classes."
                    ]
                }
            }

            # This is the chips payload
            chips_payload = {
                "richContent": [
                    [
                        {
                            "type": "chips",
                            "options": [
                                {
                                    "text": "View Pricing Details"
                                },
                                {
                                    "text": "Get a Quote"
                                }
                            ]
                        }
                    ]
                ]
            }

            # Build the fulfillment response with both messages
            fulfillment_response = {
                "fulfillmentResponse": {
                    "messages": [
                        card_text_message,
                        {"payload": chips_payload}
                    ]
                }
            }

        elif intent_display_name == 'ViewPricingIntent':
            # This is the text message containing the card details
            
            db = firestore.client()
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
                    f"- {twelve_month.get('commitment', '12-month commitment')}: {twelve_month.get('currency', 'GBP')} {twelve_month.get('discountPrice', 'N/A')} per {twelve_month.get('period', 'month')} "
                    f"(Original Price: {twelve_month.get('currency', 'GBP')} {twelve_month.get('originalPrice', 'N/A')})\n"
                    f"  Promotion: {promotion.get('description', 'N/A')}\n\n"
                    f"- {one_month_rolling.get('commitment', 'No commitment')}: {one_month_rolling.get('currency', 'GBP')} {one_month_rolling.get('price', 'N/A')} per {one_month_rolling.get('period', 'month')}\n\n"
                )
                
                card_text_message = {
                    "text": {
                        "text": [
                            pricing_info
                        ]
                    }
                }
            else:
                card_text_message = {
                    "text": {
                        "text": [
                            "Sorry, I could not find pricing details for this gym."
                        ]
                    }
                }
            
            # This is the chips payload
            chips_payload = {
                "richContent": [
                    [
                        {
                            "type": "chips",
                            "options": [
                                {
                                    "text": "Get a Quote"
                                }
                            ]
                        }
                    ]
                ]
            }

            # Build the fulfillment response with both messages
            fulfillment_response = {
                "fulfillmentResponse": {
                    "messages": [
                        card_text_message,
                        {"payload": chips_payload}
                    ]
                }
            }

        elif intent_display_name == 'GetQuoteIntent':
            # The simple text response for the "Get a Quote" intent.
            fulfillment_response = {
                "fulfillmentResponse": {
                    "messages": [
                        {
                            "text": {
                                "text": [
                                    "To get a personalized quote, please tell me your full name, email address, and a good time for a team member to contact you. Our team will be in touch within 24 hours to provide you with a tailored quote."
                                ]
                            }
                        }
                    ]
                }
            }
        
    except KeyError as e:
        # Log the error if the intent info is missing
        print(f"Error: Missing key in request JSON - {e}")
    except Exception as e:
        # Log any other errors
        print(f"An error occurred: {e}")

    # Return the final JSON response to Dialogflow
    return jsonify(fulfillment_response)

if __name__ == '__main__':
    # Run the Flask app on localhost, port 5000
    app.run(debug=True, host='0.0.0.0', port=5000)
