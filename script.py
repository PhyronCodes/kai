import os
from dotenv import load_dotenv
from google import genai
from datetime import datetime
from google.genai._gaos.lib.compat_errors import APIError 

load_dotenv()

if os.getenv("GEMINI_API_KEY") is None:
    raise SystemExit("GEMINI_API_KEY not found. Check your .env file!")

client = genai.Client()

MODEL = "gemini-3.5-flash-lite"
TIMEOUT_SECONDS = 30
MAX_TURNS = 10
GOODBYE = "If you need anything else in the future, feel free to reach out. Have a great day!"

SYSTEM_PROMPT = """
You are KAI (Knowledge & Automation Interface), my Personal assistant. I am Tomás, a second year discrete maths student at the university of Warwick.
How you will respond: Aim to keep your answers around 1-3 sentences unless explicitly told otherwise. Answer in plain text with no markdowns, so that it can be read outloud.
When you don't know the answer to something you simply can't know: live information such as weather, news and prices, and personal things about you that you hasn't been told, such as timetables or deadlines, say you dont know the answer to avoid hallucinations and so you dont invent facts.
You can't actually remember anything beyond the current conversation, so you must not claim that you can. Only say you did something unless you actually did do it.
If I ask you to remember something, say you'll keep it in mind for this conversation only, and that you can't save it after I close the program (in your own words).
"""


class Assistant:
    def __init__(self):
        self.history = []

    def trim_history(self) -> None:
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

        now = datetime.now().strftime("%A %d %B %Y, %H:%M")
        system_prompt = f"{SYSTEM_PROMPT}\nThe current date and time is {now}."

        try:
            interaction = client.interactions.create(
                model=MODEL,
                input=self.history,
                store=False,
                system_instruction=system_prompt,
                timeout=TIMEOUT_SECONDS,
            )
        except APIError as e:
            self.history.pop()
            print(f"[debug] {type(e).__name__}: {e}")
            return "Sorry, I couldn't reach my brain just then. Try again in a moment."

        for step in interaction.steps:
            self.history.append(step.model_dump())
        return interaction.output_text

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