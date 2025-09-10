# webhook.py

from flask import Flask, request, jsonify

app = Flask(__name__)

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

        elif intent_display_name == 'View Pricing Details':
            # The JSON payload for the "View Pricing Details" rich response card.
            rich_content_payload = {
                "richContent": [
                    [
                        {
                            "type": "info",
                            "title": "Pricing Details",
                            "subtitle": "Our flexible plans are designed to fit your lifestyle.",
                            "text": "We offer a range of plans including monthly, 6-month, and 12-month memberships. All plans include unlimited access to our facilities and classes. Prices vary by location. Please contact us for a personalized quote.",
                            "actionLink": "https://example.com/pricing"
                        },
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
            fulfillment_response = {
                "fulfillmentResponse": {
                    "messages": [
                        {
                            "payload": rich_content_payload
                        }
                    ]
                }
            }

        elif intent_display_name == 'Get a Quote':
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

    # Return the final JSON response to Dialogflow
    return jsonify(fulfillment_response)

if __name__ == '__main__':
    # Run the Flask app on localhost, port 5000
    app.run(debug=True, host='0.0.0.0', port=5000)
