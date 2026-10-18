import json
from datetime import date

TASKS_FILE = "tasks.json"

def load_tasks() -> list[dict]:
    """Return every task in the file, or an empty list if the file doesn't exist yet."""
    try:
        with open(TASKS_FILE) as f:
            return json.load(f)
    except (FileNotFoundError):
        return []


def save_tasks(tasks: list[dict]) -> None:
    """Write the whole list back to the file."""
    with open(TASKS_FILE, "w") as f:
        json.dump(tasks, f, indent=2)


def add_task(text: str, due: str | None = None) -> dict:
    """Add a task and return it. `due` is "YYYY-MM-DD" or None."""
    tasks = load_tasks()
    new_id = max((t["id"] for t in tasks), default=0) + 1
    task = {
        "id": new_id, 
        "text": text, 
        "done": False, 
        "created": date.today().strftime('%Y-%m-%d'), 
        "due": due
    }
    tasks.append(task)
    save_tasks(tasks)
    return task


def list_tasks(include_done: bool = False) -> list[dict]:
    """Return open tasks (or all of them), soonest due date first."""
    tasks = load_tasks()
    if not include_done:
        tasks =  [t for t in tasks if not t["done"]]
    tasks.sort(key=lambda t: (t["due"] is None, t["due"] or ""))
    return tasks


def due_tasks() -> tuple[list[dict], list[dict]]:
    """Return (due_today, overdue): open tasks due today, and open tasks
    whose due date has already passed."""
    today = date.today().strftime('%Y-%m-%d')
    tasks = list_tasks()
    overdue = []
    due_today = []
    for t in tasks:
        if t["due"] and t["due"] < today:
            overdue.append(t)
        elif t["due"] == today:
            due_today.append(t)
    return due_today, overdue


def join_names(tasks: list[dict]) -> str:
    """'A', 'A and B', or 'A, B and C'."""
    names = [t["text"] for t in tasks]
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + " and " + names[-1]


def briefing() -> str | None:
    """A spoken summary of what's due, or None if nothing is."""
    due_today, overdue = due_tasks()
    if not due_today and not overdue:
        return None

    parts = []
    if due_today:
        n = len(due_today)
        parts.append(f"You've got {n} {'task' if n == 1 else 'tasks'} due today: "
                     f"{join_names(due_today)}.")
    if overdue:
        n = len(overdue)
        parts.append(f"{n} {'task is' if n == 1 else 'tasks are'} overdue: "
                     f"{join_names(overdue)}.")
    return " ".join(parts)


def complete_task(task_id: int) -> dict:
    """Mark a task as done and return it, or return an error."""
    tasks = load_tasks()
    for t in tasks:
        if t["id"] == task_id:
            t["done"] = True
            save_tasks(tasks)
            return t
    return {"error": f"No task with id {task_id}"}


def delete_task(task_id: int) -> dict:
    """Remove a task and return it, or return an error."""
    tasks = load_tasks()
    for t in tasks:
        if t["id"] == task_id:
            tasks.remove(t)
            save_tasks(tasks)
            return t
    return {"error": f"No task with id {task_id}"}
    

# ---- What Gemini sees ----

ADD_TASK_TOOL = {
    "type": "function",          # always this, for your own functions
    "name": "add_task",          # must match the key in FUNCTIONS exactly
    "description": "Add a task to the user's to-do list. Use when they ask to add, remember or note down something they need to do.",        # WHEN Gemini should use it
    "parameters": {              # WHAT arguments it takes
        "type": "object",        # always "object": the arguments arrive as a dict
        "properties": {          # one entry per argument
            "text": {"type": "string", "description": "The task, short and clear, e.g. 'Email Capula'."},
            "due":  {"type": "string", "description": "Due date as YYYY-MM-DD. Leave out if no date was given."},
        },
        "required": ["text"],    # the arguments Gemini must always send
    },
}


LIST_TASKS_TOOL = {
    "type": "function",
    "name": "list_tasks",
    "description": "List the user's tasks. Use when they ask what's on their list, "
               "what's due next or what's coming up. Also use it to find a task's "
               "id before completing or deleting it.",     # when would you want KAI to look at your list?
    "parameters": {
        "type": "object",
        "properties": {
            "include_done": {
                "type": "boolean",             # it's a bool in Python
                "description": "True to include tasks already marked done. Only use if the user asks about finished tasks.",    # what does True do?
            },
        },
        "required": [],      # nothing is required, because include_done has a default
    },
}


COMPLETE_TASK_TOOL = {
    "type": "function",
    "name": "complete_task",
        "description": "Mark one of the user's tasks as done. Use when they say they've "
               "finished or completed a task. If you don't know the task's id, "
               "call list_tasks first to find it.",
        "parameters": {
        "type": "object",
        "properties": {
            "task_id": {
                "type": "integer",             # it's an int in Python
                "description": "The id of the task, from list_tasks.",
            },
        },
        "required": ["task_id"],   # which argument has no default?
    }
}


DELETE_TASK_TOOL = {"type": "function",
    "name": "delete_task",
        "description": "Permanently remove one of the user's tasks. Use only when they want "
               "a task gone (added by mistake, no longer needed), not when they've "
               "finished it. Use complete_task for that. If you don't know the "
               "task's id, call list_tasks first to find it.",
        "parameters": {
        "type": "object",
        "properties": {
            "task_id": {
                "type": "integer",             # it's an int in Python
                "description": "The id of the task, from list_tasks.",
            },
        },
        "required": ["task_id"],   # which argument has no default?
    }
}


TOOLS = [ADD_TASK_TOOL, LIST_TASKS_TOOL, COMPLETE_TASK_TOOL, DELETE_TASK_TOOL]

FUNCTIONS = {
    "add_task": add_task,
    "list_tasks": list_tasks,
    "complete_task": complete_task,
    "delete_task": delete_task,
}

if __name__ == "__main__":
    add_task("Email Capula", date.today().isoformat())
    add_task("Finish linear algebra sheet", date.today().isoformat())
    add_task("Buy coffee", "2026-10-01")
    print(briefing())