import os
import pickle
import threading
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

class GoogleAuthManager:
    """
    Central Manager for Google API Authentication.
    Handles OAuth 2.0 flow and token management for multiple scopes.
    """
    
    # Combined Scopes for SoulMate (Calendar + Docs)
    SCOPES = [
        'https://www.googleapis.com/auth/calendar.readonly', # Read Calendar
        'https://www.googleapis.com/auth/documents'          # Read/Write Docs
    ]
    
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(GoogleAuthManager, cls).__new__(cls)
        return cls._instance

    def __init__(self, credentials_path='settings/client_secret.json', token_path='settings/token.pickle'):
        # Ensure init only runs once
        if getattr(self, '_initialized', False):
            return
            
        self.credentials_path = credentials_path
        self.token_path = token_path
        
        # Adjust paths if not found (fallback to root or src)
        if not os.path.exists(self.credentials_path):
            # Try root 'client_secret.json' (legacy support)
            if os.path.exists('client_secret.json'):
                self.credentials_path = 'client_secret.json'
        
        if not os.path.exists(os.path.dirname(self.token_path)):
             # Ensure settings dir exists
             os.makedirs(os.path.dirname(self.token_path), exist_ok=True)

        self.creds = None
        self.is_authenticated = False
        self._initialized = True

    def set_api_instance(self, api_instance):
        """Sets the API instance to allow UI logging."""
        self.api_instance = api_instance

    def authenticate(self, status_callback=None):
        """
        Authenticate with Google APIs.
        Returns True if successful.
        """
        # Ensure only one auth flow happens at a time
        with self._lock:
            # Re-check inside lock
            if self.is_authenticated and self.creds and self.creds.valid:
                return True
                
    def authenticate(self, status_callback=None):
        """
        Authenticate with Google APIs.
        Returns True if successful.
        """
        # Ensure only one auth flow happens at a time
        with self._lock:
            # Re-check inside lock
            if self.is_authenticated and self.creds and self.creds.valid:
                return True
                
            def log(msg, type='info'):
                print(f"[GoogleAuth:{type.upper()}] {msg}")
                # 1. Direct Callback
                if status_callback:
                    status_callback(msg, type)
                
                # 2. UI Logging via API Instance (Target: Sys Tab)
                if hasattr(self, 'api_instance') and self.api_instance:
                    if type == 'auth_url':
                        self.api_instance.log_to_debug(f"Auth URL: {msg}", 'warn')
                    else:
                        self.api_instance.log_to_debug(msg, type)

            # Retry loop for CSRF/Stray requests
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    # 1. Load existing token (Only on first attempt or if we want to re-verify)
                    if attempt == 0 and os.path.exists(self.token_path):
                        try:
                            with open(self.token_path, 'rb') as token:
                                self.creds = pickle.load(token)
                        except:
                            self.creds = None

                    # 2. Refresh or Login if invalid
                    if not self.creds or not self.creds.valid:
                        if self.creds and self.creds.expired and self.creds.refresh_token:
                            log("Refreshing token...")
                            try:
                                self.creds.refresh(Request())
                            except Exception as e:
                                log(f"Token refresh failed ({e}), re-authenticating...", 'warn')
                                self.creds = None # Force re-auth
                        
                        if not self.creds: # If still no creds
                            if not os.path.exists(self.credentials_path):
                                log(f"Error: {self.credentials_path} not found.", 'error')
                                return False
                            
                            if attempt > 0:
                                log(f"Retry {attempt}/{max_retries}: Restarting OAuth flow (Ignore previous errors)...", 'warn')

                            log("Initiating OAuth flow...", 'info')
                            
                            flow = InstalledAppFlow.from_client_secrets_file(
                                self.credentials_path, self.SCOPES)
                            
                            auth_port = 8080
                            flow.redirect_uri = f'http://localhost:{auth_port}/'
                            
                            # Force consent to ensure we get a new refresh token
                            auth_url, _ = flow.authorization_url(prompt='consent')
                            log(f"Auth URL Generated (Attempt {attempt+1}).", 'info')

                            # Open Browser
                            import webbrowser
                            try:
                                webbrowser.open(auth_url)
                            except:
                                pass
                            
                            # Notify UI logic
                            log(auth_url, 'auth_url') 

                            log("Waiting for localhost:8080...", 'info')
                            # run_local_server raises Exception on failure (e.g. CSRF)
                            self.creds = flow.run_local_server(port=auth_port)
                    
                    # 3. Save Token
                    if self.creds and self.creds.valid:
                        with open(self.token_path, 'wb') as token:
                            pickle.dump(self.creds, token)
                        self.is_authenticated = True
                        log("Authenticated successfully.", 'info')
                        return True
                    
                except Exception as e:
                    log(f"Authentication attempt {attempt+1} failed: {e}", 'warn')
                    # Reset creds to force full re-auth next loop
                    self.creds = None
                    # Continue to next attempt
            
            log("All authentication attempts failed.", 'error')
            self.is_authenticated = False
            return False

    def get_service(self, api_name, api_version):
        """Returns a built service resource."""
        # Check authentication first (thread-safe check usually)
        if not self.is_authenticated or not self.creds:
            if not self.authenticate():
                return None
        try:
             # creds object is thread safe for usage
            return build(api_name, api_version, credentials=self.creds)
        except Exception as e:
            print(f"[GoogleAuth] Failed to build service {api_name}: {e}")
            return None
