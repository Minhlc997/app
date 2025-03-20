import requests
import jwt
import json
import logging
import os
import time
import threading
import concurrent.futures
from datetime import datetime, timedelta, timezone
from flask import Flask, render_template, request, jsonify, g
from functools import wraps
from dotenv import load_dotenv

load_dotenv()

# --- Configuration ---
ISSUER_ID = "0376081d-4ffe-488f-8bbd-9022065cbe73"
KEY_ID = "CXH5GY5U42"
PRIVATE_KEY_PATH = r"C:\Users\ADM\Desktop\APIKeys\AuthKey_CXH5GY5U42.p8"
INTERNAL_BETA_GROUP_ID = os.environ.get('INTERNAL_BETA_GROUP_ID')
API_KEY = os.environ.get('API_KEY')  # No default value - MUST be in .env
TEMP_EMAIL_API_URL = 'https://api.tempmail.lol/v1/email'  # Updated to TempMail API

# Constants
MAX_THREADS = 5  # Default number of threads
APPSTORE_CONNECT_API_BASE = 'https://api.appstoreconnect.apple.com/v1'

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(threadName)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Flask Setup ---
app = Flask(__name__)

# --- Load Private Key ---
try:
    with open(PRIVATE_KEY_PATH, 'r') as key_file:
        PRIVATE_KEY = key_file.read()
    if not PRIVATE_KEY:
        raise ValueError("Private key could not be loaded.")  # More informative error
except FileNotFoundError:
    logger.error(f"ERROR: Private key file not found at {PRIVATE_KEY_PATH}. Check your .env and file location.")
    exit(1)  # Exit immediately - can't continue without the key
except Exception as e:
    logger.error(f"ERROR: Could not load private key: {e}")
    exit(1)

# --- Function Definitions ---
def create_jwt():
    """Creates a JWT for App Store Connect API authentication."""
    now = datetime.now(timezone.utc)
    expiration = now + timedelta(minutes=15)  # 15 minutes is the maximum allowed by App Store Connect
    payload = {"iss": ISSUER_ID, "exp": int(expiration.timestamp()), "aud": "appstoreconnect-v1"}
    headers = {"kid": KEY_ID, "typ": "JWT"}
    try:
        token = jwt.encode(payload, PRIVATE_KEY, algorithm="ES256", headers=headers)
        return token
    except Exception as e:
        logger.error(f"ERROR: Could not create JWT: {e}")  # More specific error logging
        return None  # Return None to indicate failure

def api_request(url, method='GET', data=None, headers=None, retries=3, backoff_factor=2):
    """Makes a request to the App Store Connect API with retries and JWT authentication."""
    if headers is None:
        headers = {}
    jwt_token = create_jwt()
    if not jwt_token:
        logger.error("ERROR: No JWT token generated. Cannot make API request.")
        return None

    headers['Authorization'] = f'Bearer {jwt_token}'

    for attempt in range(retries):
        try:
            response = requests.request(method, url, headers=headers, json=data, timeout=15)  # Timeout of 15s
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            return response.json()
        except requests.exceptions.HTTPError as e:
            logger.warning(f"API Request failed (HTTP Error, attempt {attempt + 1}/{retries}): {e.response.status_code} - {e.response.text}")
            if attempt == retries - 1:
                return None  # Don't sleep on the last attempt
            time.sleep(backoff_factor ** attempt)
        except requests.exceptions.RequestException as e:
            logger.warning(f"API Request failed (attempt {attempt + 1}/{retries}): {e}")
            if attempt == retries - 1:
                return None
            time.sleep(backoff_factor ** attempt)
        except Exception as e:
            logger.error(f"Unexpected error during API request: {e}")  # Catch unexpected
            return None
    return None

def create_temp_email():
    """Creates a temporary email address using the TempMail API."""
    try:
        response = requests.get(TEMP_EMAIL_API_URL, timeout=10)
        response.raise_for_status()
        return response.json().get('email')
    except requests.exceptions.RequestException as e:
        logger.error(f"Error creating temp email: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error creating temp email: {e}")  # Catch unexpected
        return None

def check_tester_exists(email):
    """Checks if a tester already exists (by email) and returns their ID."""
    url = f"{APPSTORE_CONNECT_API_BASE}/betaTesters?filter[email]={email}&limit=1"
    response = api_request(url)
    if response and response.get('data'):
        return response['data'][0]['id']  # Return the tester's ID
    return None

def add_tester_to_group(email, beta_group_id):
    """Adds a tester to the specified beta group. Handles existing testers."""
    tester_id = check_tester_exists(email)
    if tester_id:
        logger.info(f"Tester {email} already exists (ID: {tester_id}). Skipping creation.")
        return tester_id  # Return existing tester ID

    # Create the tester
    create_url = f"{APPSTORE_CONNECT_API_BASE}/betaTesters"
    create_data = {
        "data": {
            "type": "betaTesters",
            "attributes": {
                "email": email,
                "firstName": "Test",  # Using generic names
                "lastName": "User"
            }
        }
    }
    create_response = api_request(create_url, method='POST', data=create_data)
    if not create_response or 'data' not in create_response:
        logger.error(f"Failed to create tester {email}")
        return None
    tester_id = create_response['data']['id']
    logger.info(f"Created new tester: {email} (ID: {tester_id})")

    # Add the tester to the beta group
    add_url = f"{APPSTORE_CONNECT_API_BASE}/betaGroups/{beta_group_id}/relationships/betaTesters"
    add_data = {"data": [{"type": "betaTesters", "id": tester_id}]}
    add_response = api_request(add_url, method='POST', data=add_data)
    if not add_response:  # App Store Connect returns 204 No Content on success
        logger.error(f"Failed to add tester {email} (ID: {tester_id}) to group {beta_group_id}")
        return None

    logger.info(f"Added tester {email} to group {beta_group_id}")
    return tester_id

def get_invitation_link(tester_id):
    """Retrieves the TestFlight invitation link for a tester."""
    url = f"{APPSTORE_CONNECT_API_BASE}/betaTesters/{tester_id}?fields[betaTesters]=inviteUrl"
    response = api_request(url)
    if response and response.get('data') and response['data'].get('attributes') and response['data']['attributes'].get('inviteUrl'):
        return response['data']['attributes']['inviteUrl']
    else:
        logger.warning(f"Could not retrieve invitation URL for tester {tester_id}")
        return None

def invite_worker():
    """Worker function for inviting a single tester (thread-safe)."""
    email = create_temp_email()
    if not email:
        return  # Exit if email creation fails

    tester_id = add_tester_to_group(email, INTERNAL_BETA_GROUP_ID)
    if not tester_id:
        return  # Exit if adding tester fails

    invitation_link = get_invitation_link(tester_id)
    with app.app_context():  # Needed to access flask.g
        if 'invitation_links' not in g:
            g.invitation_links = []
        if invitation_link:
            logger.info(f"Invitation link for {email}: {invitation_link}")
            g.invitation_links.append({'email': email, 'link': invitation_link})
        else:
            logger.warning(f"No invitation link retrieved for {email}")
            g.invitation_links.append({'email': email, 'link': 'Error: Could not retrieve link'})

def run_invites(num_threads, interval):
    """Runs the invitation process using multiple threads, with a delay."""
    while True:  # Loop indefinitely
        logger.info(f"Starting a new batch of invitations (threads: {num_threads}, interval: {interval}s)")
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(invite_worker) for _ in range(num_threads)]
            concurrent.futures.wait(futures, timeout=60)  # Add a timeout
        logger.info(f"Batch complete. Waiting for {interval} seconds...")
        time.sleep(interval)

# --- Authentication Decorator ---
def authenticate(func):
    """Decorator for basic authentication."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        auth = request.authorization
        if not auth or not auth.username or auth.username != API_KEY:
            return jsonify({'message': 'Authentication required'}), 401  # 401 Unauthorized
        return func(*args, **kwargs)
    return wrapper

# --- Flask Routes ---
@app.route('/start', methods=['POST'])
@authenticate
def start_invites():
    """Starts the auto-invite process (requires authentication)."""
    num_threads = request.form.get('threads', type=int, default=MAX_THREADS)
    interval = request.form.get('interval', type=int, default=60)
    num_threads = max(1, min(num_threads, 20))  # Limit threads to a reasonable range (1-20)

    threading.Thread(target=run_invites, args=(num_threads, interval), daemon=True).start()
    return jsonify({'message': f'Auto-invite process started with {num_threads} threads and {interval}s interval.'})

@app.route('/status', methods=['GET'])
def get_status():
    """Returns the current list of invitation links (JSON)."""
    with app.app_context():
        if 'invitation_links' in g:
            return jsonify(g.invitation_links)
        return jsonify([])  # Return empty list if no invitations yet

@app.route('/', methods=['GET'])
def index():
    """Serves the main HTML page."""
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))