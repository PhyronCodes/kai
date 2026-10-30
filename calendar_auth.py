"""Google Calendar sign-in, shared by everything that uses the calendar.

The first time, get_service() opens a browser so you can sign in and allow
KAI to manage your calendar events. It then saves token.json, so every later
run signs in silently (refreshing the token by itself when it expires).

Run this file directly to sign in and test: it prints your next 5 events.
"""
import datetime
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Read and write events (not calendar settings or sharing). If you ever change
# this, delete token.json so you're asked to sign in again with the new scope.
SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
CREDENTIALS_FILE = "credentials.json"   # downloaded from Google Cloud: identifies the app
TOKEN_FILE = "token.json"               # created on first sign-in: identifies YOU. Keep secret.


class NotSignedIn(Exception):
    """There's no usable sign-in and we're not allowed to open a browser."""


def get_service(interactive: bool = True):
    """Return a Calendar API client, signing in first if needed.

    interactive=False is for KAI itself: it must never open a browser in the
    middle of a conversation (in full-screen device mode nobody would see it),
    so it raises NotSignedIn instead."""
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())                  # silent: no browser needed
        else:
            if not interactive:
                raise NotSignedIn("no valid token.json")
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)     # opens the browser to sign in
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


if __name__ == "__main__":
    service = get_service()
    now = datetime.datetime.now(tz=datetime.timezone.utc).isoformat()
    result = service.events().list(
        calendarId="primary", timeMin=now, maxResults=5,
        singleEvents=True, orderBy="startTime",
    ).execute()
    events = result.get("items", [])
    if not events:
        print("Signed in. No upcoming events found.")
    for event in events:
        start = event["start"].get("dateTime", event["start"].get("date"))
        print(start, "-", event.get("summary", "(no title)"))