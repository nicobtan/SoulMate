import os
import pickle
import datetime
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

class CalendarManager:
    """
    Google Calendar API Manager.
    Handles OAuth 2.0 authentication and schedule retrieval.
    """
    
    # Scope needed to read calendar events
    SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
    
    def __init__(self, credentials_path='client_secret.json', token_path='token.json'):
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.creds = None
        self.service = None
        self.is_authenticated = False

    def authenticate(self, status_callback=None):
        """
        Authenticate with Google Calendar API.
        status_callback(msg, type='info'): called with status updates.
        type can be 'info', 'warn', 'error', or 'auth_url' for the URL itself.
        """
        def log(msg, type='info'):
            print(f"[{type.upper()}] {msg}")
            if status_callback:
                status_callback(msg, type)

        try:
            # 1. Load existing token
            if os.path.exists(self.token_path):
                log(f"Loading token from {self.token_path}")
                with open(self.token_path, 'rb') as token:
                    self.creds = pickle.load(token)

            # 2. Refresh or Login if invalid
            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    log("Refreshing token...")
                    self.creds.refresh(Request())
                else:
                    if not os.path.exists(self.credentials_path):
                        log(f"Error: {self.credentials_path} not found.", 'error')
                        return False
                    
                    log("Initiating OAuth flow...", 'info')
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, self.SCOPES)
                    
                    # Manual URL generation to help user
                    log("Generating Auth URL...", 'info')
                    
                    auth_port = 8080
                    flow.redirect_uri = f'http://localhost:{auth_port}/'
                    
                    auth_url, _ = flow.authorization_url(prompt='consent')
                    log(f"Auth URL Ready.", 'info')

                    # ACTION: Try to open browser directly (Python side)
                    import webbrowser
                    try:
                        webbrowser.open(auth_url)
                        log("Browser launch attempted.", 'info')
                    except Exception as e:
                        log(f"Browser launch failed: {e}", 'warn')
                    
                    # ACTION: Notify UI with URL
                    log(auth_url, 'auth_url') 

                    # Run local server for auth with fixed port
                    log("Waiting for localhost:8080 response...", 'info')
                    self.creds = flow.run_local_server(port=auth_port)
            
            # 4. Build service
            self.service = build('calendar', 'v3', credentials=self.creds)
            self.is_authenticated = True
            log("Google Calendar authenticated successfully.", 'info')
            
            # 3. Save the new token (Only if we successfully authenticated/refreshed)
            if self.creds and self.creds.valid:
                with open(self.token_path, 'wb') as token:
                    pickle.dump(self.creds, token)
                    
            return True

        except Exception as e:
            log(f"Authentication failed: {e}", 'error')
            return False

    def get_upcoming_events(self, max_results=20, status_callback=None):
        """
        Fetch upcoming N events.
        payload: list of strings (human readable)
        """
        if not self.is_authenticated or not self.service:
            if not self.authenticate(status_callback=status_callback):
                return ["Google Calendarの認証に失敗しました。"]

        try:
            now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
            events_result = self.service.events().list(
                calendarId='primary', timeMin=now,
                maxResults=max_results, singleEvents=True,
                orderBy='startTime').execute()
            events = events_result.get('items', [])

            if not events:
                return ["直近の予定はありません。"]

            formatted_events = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                # Format: "2023-10-27T10:00:00+09:00" -> "10/27 10:00"
                # Simple parsing logic
                time_str = start
                try:
                    dt = datetime.datetime.fromisoformat(start)
                    time_str = dt.strftime('%m/%d %H:%M')
                except:
                    pass # Keep original if parsing fails (e.g. all-day event "2023-10-27")
                
                summary = event.get('summary', '予定あり')
                formatted_events.append(f"{time_str}: {summary}")

            return formatted_events

        except Exception as e:
            print(f"Failed to fetch events: {e}")
            return [f"予定の取得に失敗しました: {e}"]

    def add_event(self, summary, start_time_str, duration_minutes=60, status_callback=None):
        """
        Adds an event to the primary calendar.
        start_time_str: ISO format or simpler 'YYYY-MM-DD HH:MM'
        """
        if not self.is_authenticated or not self.service:
             if not self.authenticate(status_callback=status_callback):
                 return "認証が必要です。"

        try:
            # Parse Time
            # Assume local time usage for simplicity or ISO
            try:
                 dt_start = datetime.datetime.strptime(start_time_str, '%Y-%m-%d %H:%M')
            except ValueError:
                 dt_start = datetime.datetime.fromisoformat(start_time_str)

            dt_end = dt_start + datetime.timedelta(minutes=duration_minutes)
            
            event = {
                'summary': summary,
                'start': {
                    'dateTime': dt_start.isoformat(),
                    'timeZone': 'Asia/Tokyo', # Assumption
                },
                'end': {
                    'dateTime': dt_end.isoformat(),
                    'timeZone': 'Asia/Tokyo',
                },
            }

            event = self.service.events().insert(calendarId='primary', body=event).execute()
            msg = f"予定を追加しました: {event.get('htmlLink')}"
            if status_callback:
                status_callback(msg, 'info')
            
            # Open the event immediately? Or just return link?
            # User wants to add it.
            return f"予定「{summary}」を追加したわ。（{dt_start.strftime('%m/%d %H:%M')}〜）"

        except Exception as e:
            err = f"予定の追加に失敗しました: {e}"
            if status_callback:
                status_callback(err, 'error')
            return err

if __name__ == "__main__":
    # Test Script
    cm = CalendarManager()
    # Simple console printer callback
    def console_callback(msg, type):
        print(f"[CALLBACK:{type}] {msg}")
        
    if cm.authenticate(status_callback=console_callback):
        print("--- Upcoming Events ---")
        events = cm.get_upcoming_events(status_callback=console_callback)
        for e in events:
            print(e)
