"""KAI's Google Calendar tools: functions Gemini can call, plus their descriptions.

Dates are "YYYY-MM-DD" and times "HH:MM" (24-hour), always in local time.
Every function returns a dict or list that Gemini reads; problems come back
as {"error": ...} instead of crashing, so KAI can say what went wrong.
"""
from datetime import date, datetime, timedelta
from functools import wraps

from google.auth.exceptions import RefreshError
from googleapiclient.errors import HttpError

from calendar_auth import NotSignedIn, get_service

CALENDAR_ID = "primary"
SIGN_IN_ERROR = ("The calendar sign-in has expired or is missing. Tell the user to "
                 "delete token.json and run calendar_auth.py to sign in again.")


def calendar_call(function):
    """Decorator: turns sign-in and API problems into error dicts for Gemini."""
    @wraps(function)
    def wrapper(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except (NotSignedIn, RefreshError):
            return {"error": SIGN_IN_ERROR}
        except HttpError as e:
            return {"error": f"Google Calendar error: {e.reason}"}
        except ValueError as e:                  # e.g. a badly formatted date
            return {"error": f"Invalid date or time: {e}"}
    return wrapper


def local_datetime(day: str, time: str = "00:00") -> datetime:
    """"2026-10-31" + "14:30" -> a timezone-aware datetime in local time."""
    return datetime.fromisoformat(f"{day}T{time}").astimezone()


def simplify(event: dict) -> dict:
    """Keep only what Gemini needs from Google's (very long) event data."""
    start, end = event["start"], event["end"]
    all_day = "date" in start
    return {
        "id": event["id"],
        "title": event.get("summary", "(no title)"),
        "all_day": all_day,
        "start": start.get("date") if all_day else start["dateTime"][:16].replace("T", " "),
        "end": end.get("date") if all_day else end["dateTime"][:16].replace("T", " "),
        "location": event.get("location", ""),
    }


@calendar_call
def list_events(start_date: str, end_date: str | None = None) -> list[dict]:
    """Events from the start of start_date to the end of end_date (inclusive)."""
    end_date = end_date or start_date
    time_min = local_datetime(start_date)
    time_max = local_datetime(end_date) + timedelta(days=1)
    result = get_service(interactive=False).events().list(
        calendarId=CALENDAR_ID,
        timeMin=time_min.isoformat(),
        timeMax=time_max.isoformat(),
        singleEvents=True,          # expand repeating events into single ones
        orderBy="startTime",
    ).execute()
    return [simplify(e) for e in result.get("items", [])]


@calendar_call
def add_event(title: str, date: str, start_time: str | None = None,
              duration_minutes: int = 60, location: str | None = None) -> dict:
    """Create an event. No start_time means an all-day event."""
    if start_time:
        start = local_datetime(date, start_time)
        end = start + timedelta(minutes=duration_minutes)
        body = {"start": {"dateTime": start.isoformat()}, "end": {"dateTime": end.isoformat()}}
    else:
        next_day = (local_datetime(date) + timedelta(days=1)).date().isoformat()
        body = {"start": {"date": date}, "end": {"date": next_day}}
    body["summary"] = title
    if location:
        body["location"] = location
    event = get_service(interactive=False).events().insert(calendarId=CALENDAR_ID, body=body).execute()
    return simplify(event)


@calendar_call
def move_event(event_id: str, new_date: str, new_start_time: str | None = None) -> dict:
    """Move an event to a new date (and time), keeping its length."""
    service = get_service(interactive=False)
    event = service.events().get(calendarId=CALENDAR_ID, eventId=event_id).execute()
    if "dateTime" in event["start"]:
        old_start = datetime.fromisoformat(event["start"]["dateTime"])
        old_end = datetime.fromisoformat(event["end"]["dateTime"])
        time = new_start_time or old_start.astimezone().strftime("%H:%M")
        start = local_datetime(new_date, time)
        end = start + (old_end - old_start)
        patch = {"start": {"dateTime": start.isoformat()}, "end": {"dateTime": end.isoformat()}}
    else:
        days = (date.fromisoformat(event["end"]["date"]) - date.fromisoformat(event["start"]["date"])).days
        end = (date.fromisoformat(new_date) + timedelta(days=days)).isoformat()
        patch = {"start": {"date": new_date}, "end": {"date": end}}
    event = service.events().patch(calendarId=CALENDAR_ID, eventId=event_id, body=patch).execute()
    return simplify(event)


@calendar_call
def delete_event(event_id: str) -> dict:
    """Delete an event and return what was deleted."""
    service = get_service(interactive=False)
    event = service.events().get(calendarId=CALENDAR_ID, eventId=event_id).execute()
    service.events().delete(calendarId=CALENDAR_ID, eventId=event_id).execute()
    return {"deleted": simplify(event)}


def calendar_briefing() -> str | None:
    """A spoken summary of today's events, or None if there are none (or no sign-in)."""
    events = list_events(date.today().isoformat())
    if not events or isinstance(events, dict):      # empty, or an error dict
        return None
    parts = []
    for e in events:
        if e["all_day"]:
            parts.append(e["title"])
        else:
            parts.append(f"{e['title']} at {e['start'][11:16]}")
    n = len(parts)
    names = parts[0] if n == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]
    return f"On your calendar today: {names}."


# ---- What Gemini sees ----

EVENT_ID_HINT = "If you don't know the event's id, call list_events first to find it."

LIST_EVENTS_TOOL = {
    "type": "function",
    "name": "list_events",
    "description": "List the user's calendar events between two dates. Use when they ask "
                   "what's on, what they're doing on a day, when something is, or whether "
                   "they're free. Also use it to find an event's id before moving or deleting it.",
    "parameters": {
        "type": "object",
        "properties": {
            "start_date": {"type": "string", "description": "First day, YYYY-MM-DD."},
            "end_date": {"type": "string",
                         "description": "Last day, YYYY-MM-DD, inclusive. Leave out for a single day."},
        },
        "required": ["start_date"],
    },
}

ADD_EVENT_TOOL = {
    "type": "function",
    "name": "add_event",
    "description": "Add an event to the user's calendar. Use when they ask to schedule, book or "
                   "put something in their calendar at a particular time or day. For things "
                   "they need to do without a set time, use add_task instead.",
    "parameters": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Short event title, e.g. 'Study session'."},
            "date": {"type": "string", "description": "Day of the event, YYYY-MM-DD."},
            "start_time": {"type": "string",
                           "description": "Start time, HH:MM in 24-hour local time. Leave out for an all-day event."},
            "duration_minutes": {"type": "integer",
                                 "description": "Length in minutes. Defaults to 60 if not given."},
            "location": {"type": "string", "description": "Where it is, if the user said."},
        },
        "required": ["title", "date"],
    },
}

MOVE_EVENT_TOOL = {
    "type": "function",
    "name": "move_event",
    "description": "Move an existing event to a new day and/or time, keeping its length. "
                   "Use when the user wants to reschedule something. " + EVENT_ID_HINT,
    "parameters": {
        "type": "object",
        "properties": {
            "event_id": {"type": "string", "description": "The event's id, from list_events."},
            "new_date": {"type": "string", "description": "New day, YYYY-MM-DD."},
            "new_start_time": {"type": "string",
                               "description": "New start time, HH:MM (24-hour). Leave out to keep the same time."},
        },
        "required": ["event_id", "new_date"],
    },
}

DELETE_EVENT_TOOL = {
    "type": "function",
    "name": "delete_event",
    "description": "Delete an event from the user's calendar. Only when they clearly ask to "
                   "cancel or remove it. " + EVENT_ID_HINT,
    "parameters": {
        "type": "object",
        "properties": {
            "event_id": {"type": "string", "description": "The event's id, from list_events."},
        },
        "required": ["event_id"],
    },
}

CALENDAR_TOOLS = [LIST_EVENTS_TOOL, ADD_EVENT_TOOL, MOVE_EVENT_TOOL, DELETE_EVENT_TOOL]

CALENDAR_FUNCTIONS = {
    "list_events": list_events,
    "add_event": add_event,
    "move_event": move_event,
    "delete_event": delete_event,
}


if __name__ == "__main__":
    today = date.today().isoformat()
    print("Today:", list_events(today))
    print("Briefing:", calendar_briefing())
