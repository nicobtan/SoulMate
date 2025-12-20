import datetime
from .google_auth_manager import GoogleAuthManager

class CalendarManager:
    """
    Google Calendar API Manager.
    Delegates Auth to GoogleAuthManager.
    """
    
    def __init__(self):
        self.auth_manager = GoogleAuthManager()
        self.service = None

    @property
    def is_authenticated(self):
        return self.auth_manager.is_authenticated

    def authenticate(self, status_callback=None):
        return self.auth_manager.authenticate(status_callback)

    def _get_service(self):
        if not self.service:
             self.service = self.auth_manager.get_service('calendar', 'v3')
        return self.service

    def get_upcoming_events(self, max_results=20, status_callback=None):
        """
        Fetch upcoming N events.
        """
        service = self._get_service()
        if not service:
            return ["Google Calendarの認証に失敗しました。"]

        try:
            now = datetime.datetime.utcnow().isoformat() + 'Z'
            events_result = service.events().list(
                calendarId='primary', timeMin=now,
                maxResults=max_results, singleEvents=True,
                orderBy='startTime').execute()
            events = events_result.get('items', [])

            if not events:
                return ["直近の予定はありません。"]

            formatted_events = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                time_str = start
                try:
                    dt = datetime.datetime.fromisoformat(start)
                    time_str = dt.strftime('%m/%d %H:%M')
                except:
                    pass
                
                summary = event.get('summary', '予定あり')
                formatted_events.append(f"{time_str}: {summary}")

            return formatted_events

        except Exception as e:
            print(f"Failed to fetch events: {e}")
            return [f"予定の取得に失敗しました: {e}"]

    def add_event(self, summary, start_time_str, duration_minutes=60, status_callback=None):
        """
        Adds an event to the primary calendar.
        """
        service = self._get_service()
        if not service:
            return "認証が必要です。"

        try:
            try:
                 dt_start = datetime.datetime.strptime(start_time_str, '%Y-%m-%d %H:%M')
            except ValueError:
                 dt_start = datetime.datetime.fromisoformat(start_time_str)

            dt_end = dt_start + datetime.timedelta(minutes=duration_minutes)
            
            event = {
                'summary': summary,
                'start': {
                    'dateTime': dt_start.isoformat(),
                    'timeZone': 'Asia/Tokyo',
                },
                'end': {
                    'dateTime': dt_end.isoformat(),
                    'timeZone': 'Asia/Tokyo',
                },
            }

            event = service.events().insert(calendarId='primary', body=event).execute()
            msg = f"予定を追加しました: {event.get('htmlLink')}"
            if status_callback:
                status_callback(msg, 'info')
            
            return f"予定「{summary}」を追加したわ。（{dt_start.strftime('%m/%d %H:%M')}〜）"

        except Exception as e:
            err = f"予定の追加に失敗しました: {e}"
            if status_callback:
                status_callback(err, 'error')
            return err

