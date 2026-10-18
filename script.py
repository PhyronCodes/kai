import json
import os
from datetime import datetime

from dotenv import load_dotenv
from google import genai
from google.genai._gaos.lib.compat_errors import APIError

from tasks import TOOLS, FUNCTIONS

load_dotenv()

if os.getenv("GEMINI_API_KEY") is None:
    raise SystemExit("GEMINI_API_KEY not found. Check your .env file!")

client = genai.Client()

MODEL = "gemini-3.5-flash-lite"
TIMEOUT_SECONDS = 30
MAX_TURNS = 10
MAX_TOOL_ROUNDS = 5     # safety cap on tool calls per question
GOODBYE = "If you need anything else in the future, feel free to reach out. Have a great day!"

SYSTEM_PROMPT = """
You are KAI (Knowledge & Automation Interface), my Personal assistant. I am Tomás, a second year discrete maths student at the university of Warwick.
How you will respond: Aim to keep your answers around 1-3 sentences unless explicitly told otherwise. Answer in plain text with no markdowns, so that it can be read outloud.
When you don't know the answer to something you simply can't know: live information such as weather, news and prices, and personal things about you that you hasn't been told, such as timetables or deadlines, say you dont know the answer to avoid hallucinations and so you dont invent facts.
You can manage my to-do list with your tools: adding tasks (with due dates), listing them, marking them done and deleting them. The to-do list is saved, so it is still there next time. Apart from the to-do list, you can't remember anything beyond the current conversation, so you must not claim that you can.
Only say you added, completed or deleted a task if the tool actually succeeded. If a tool returns an error, tell me what went wrong instead of pretending it worked.
If I ask you to remember something that isn't a task, say you'll keep it in mind for this conversation only, and that you can't save it after I close the program (in your own words), unless it makes sense to add it to my to-do list.
"""


def run_tool(name: str, arguments: dict) -> dict | list:
    """Run the function Gemini asked for and return its result."""
    function = FUNCTIONS.get(name)
    if function is None:
        return {"error": f"Unknown tool: {name}"}
    try:
        return function(**arguments)
    except TypeError as e:          # wrong or missing arguments
        return {"error": str(e)}


class Assistant:
    def __init__(self):
        self.history = []

    def trim_history(self) -> None:
        """Keep the last MAX_TURNS questions. Only ever cuts just before a
        user_input step, so a function call is never split from its result."""
        user_positions = []
        for i, step in enumerate(self.history):
            if step["type"] == "user_input":
                user_positions.append(i)

        if len(user_positions) > MAX_TURNS:
            start = user_positions[-MAX_TURNS]
            self.history = self.history[start:]

    def ask(self, user_input: str) -> str:
        self.history.append({
            "type": "user_input",
            "content": [{"type": "text", "text": user_input}],
        })
        self.trim_history()
        turn_start = len(self.history) - 1   # where this turn's steps begin

        now = datetime.now()
        system_prompt = (f"{SYSTEM_PROMPT}\nThe current date and time is "
                         f"{now:%A %d %B %Y, %H:%M} ({now:%Y-%m-%d}).")

        try:
            for _ in range(MAX_TOOL_ROUNDS):
                interaction = client.interactions.create(
                    model=MODEL,
                    input=self.history,
                    store=False,
                    system_instruction=system_prompt,
                    tools=TOOLS,
                    timeout=TIMEOUT_SECONDS,
                )
                for step in interaction.steps:
                    self.history.append(step.model_dump())

                calls = [s for s in interaction.steps if s.type == "function_call"]
                if not calls:
                    return interaction.output_text

                for call in calls:
                    result = run_tool(call.name, call.arguments)
                    print(f"[debug] {call.name}({call.arguments}) -> {result}")
                    self.history.append({
                        "type": "function_result",
                        "name": call.name,
                        "call_id": call.id,
                        "result": [{"type": "text", "text": json.dumps(result)}],
                    })

            return "Sorry, I got stuck doing that. Could you try asking another way?"

        except APIError as e:
            del self.history[turn_start:]    # undo the whole half-finished turn
            print(f"[debug] {type(e).__name__}: {e}")
            return "Sorry, I couldn't reach my brain just then. Try again in a moment."


if __name__ == "__main__":
    kai = Assistant()

    try:
        while True:
            user_message = input("You: ").strip()
            if not user_message:
                continue
            if user_message.lower() == "quit":
                print(GOODBYE)
                break
            print("KAI: " + kai.ask(user_message))
    except (KeyboardInterrupt, EOFError):
        print("\n" + GOODBYE)