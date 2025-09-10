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

        # Check if the intent is "Pricing and Membership"
        if intent_display_name == 'Pricing and Membership':
            # This is the correct JSON payload for the rich response card.
            rich_content_payload = {
                "richContent": [
                    [
                        {
                            "type": "info",
                            "title": "Membership & Pricing",
                            "subtitle": "Choose the plan that's right for you.",
                            "text": "We offer a variety of flexible membership options. Our current special is 50% off a 12-month membership until 2026! Our most popular plan includes unlimited access to all facilities and classes.",
                            "image": {
                                "src": {
                                    "rawUrl": "https://example.com/membership_image.png"
                                }
                            },
                            "actionLink": "https://example.com/pricing"
                        },
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

            # Build the fulfillment response with the rich content payload
            fulfillment_response = {
                "fulfillmentResponse": {
                    "messages": [
                        {
                            "payload": rich_content_payload
                        }
                    ]
                }
            }
        
        # You can add more intents here if needed for other rich responses
        # elif intent_display_name == 'View Pricing Details':
        #     # Add logic for "View Pricing Details"
        #     pass

    except KeyError as e:
        # Log the error if the intent info is missing
        print(f"Error: Missing key in request JSON - {e}")

    # Return the final JSON response to Dialogflow
    return jsonify(fulfillment_response)

if __name__ == '__main__':
    # Run the Flask app on localhost, port 5000
    app.run(debug=True, host='0.0.0.0', port=5000)
