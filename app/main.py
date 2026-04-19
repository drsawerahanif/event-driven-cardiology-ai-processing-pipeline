import os

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from database import SessionLocal, Prompt, init_db

from google import genai

from dotenv import load_dotenv
load_dotenv() # Reads the .env file in the root folder to read the Gemini API Key

app = FastAPI()
templates = Jinja2Templates(directory="templates")

init_db()

# -----------------------------
# Gemini configuration (NEW SDK)
# -----------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL_ID = "models/gemini-2.5-flash"  # Update to the desired Gemini model

gemini_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None


@app.get("/debug-env")
def debug_env():
    return {
        "GEMINI_API_KEY_present": bool(GEMINI_API_KEY),
        "GEMINI_MODEL_ID": GEMINI_MODEL_ID,
    }


def mock_llm_response(prompt_text: str, user_id: int) -> str:
    return (
        f"[MOCK MODE]\n"
        f"user_id={user_id}\n"
        f"Prompt from DB: {prompt_text}\n\n"
        f"Reason: GEMINI_API_KEY missing or LLM call failed.\n"
        f"This still demonstrates the full pipeline: Frontend -> Backend -> DB -> (LLM stub) -> Frontend."
    )


def call_gemini(prompt_text: str) -> str:
    full_prompt = (
        "You are a medical assistant. Provide concise, clinically reasonable information. "
        "Do not provide a medical diagnosis. Advise seeing a clinician for urgent or severe symptoms. "
        "If unsure, say you are unsure. Do not invent citations.\n\n"
        f"User prompt: {prompt_text}"
    )

    resp = gemini_client.models.generate_content(
        model=GEMINI_MODEL_ID,
        contents=full_prompt,
    )

    text = (getattr(resp, "text", "") or "").strip()
    return text if text else "[Empty response returned by Gemini]"


@app.get("/", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login", response_class=HTMLResponse)
def login(request: Request, user_id: int = Form(...)):
    db = None
    try:
        db = SessionLocal()

        row = db.query(Prompt).filter(Prompt.id == user_id).first()
        if not row:
            return templates.TemplateResponse(
                "login.html",
                {"request": request, "error": "Invalid User ID"}
            )

        prompt_text = row.text

        if gemini_client is None:
            print("DEBUG: gemini_client is None -> mock mode")
            answer = mock_llm_response(prompt_text, user_id)
            mode = "mock"
            model_id = f"{GEMINI_MODEL_ID} (no key)"
        else:
            try:
                print("DEBUG: Calling Gemini (new SDK)...")
                answer = call_gemini(prompt_text)
                mode = "real"
                model_id = GEMINI_MODEL_ID
            except Exception as e:
                print("DEBUG: Gemini failed:", repr(e))
                answer = mock_llm_response(prompt_text, user_id) + f"\n\n[LLM ERROR] {repr(e)}"
                mode = "mock"
                model_id = f"{GEMINI_MODEL_ID} (failed)"

        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "user_id": user_id,
                "prompt_text": prompt_text,
                "response": answer,
                "mode": mode,
                "model_id": model_id,
            }
        )

    except Exception as e:
        print("DEBUG: Server error:", repr(e))
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": f"Server error: {e}"}
        )
    finally:
        if db is not None:
            db.close()
