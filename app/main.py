import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI, Form, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from google import genai
from pydantic import BaseModel

from database import Prompt, SessionLocal, init_db

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
templates = Jinja2Templates(directory="templates")

init_db()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
BACKEND_API_KEY = os.getenv("BACKEND_API_KEY")
GEMINI_MODEL_ID = "models/gemini-2.5-flash"

gemini_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None


class PromptRequest(BaseModel):
    prompt: str


def mock_llm_response(prompt_text: str, user_id: int | None = None) -> str:
    prefix = f"user_id={user_id}\n" if user_id is not None else ""
    return (
        f"[MOCK MODE]\n"
        f"{prefix}"
        f"Prompt: {prompt_text}\n\n"
        f"Reason: GEMINI_API_KEY missing or LLM call failed."
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


def process_prompt_text(prompt_text: str, user_id: int | None = None) -> dict:
    prompt_text = prompt_text.strip()

    if not prompt_text:
        raise ValueError("Prompt cannot be empty")

    if gemini_client is None:
        logger.info("Gemini client missing. Using mock mode.")
        answer = mock_llm_response(prompt_text, user_id)
        mode = "mock"
        model_id = f"{GEMINI_MODEL_ID} (no key)"
    else:
        try:
            logger.info("Calling Gemini model.")
            answer = call_gemini(prompt_text)
            mode = "real"
            model_id = GEMINI_MODEL_ID
        except Exception as e:
            logger.exception("Gemini call failed.")
            answer = mock_llm_response(prompt_text, user_id) + f"\n\n[LLM ERROR] {repr(e)}"
            mode = "mock"
            model_id = f"{GEMINI_MODEL_ID} (failed)"

    return {
        "prompt": prompt_text,
        "response": answer,
        "mode": mode,
        "model_id": model_id,
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "gemini_key_present": bool(GEMINI_API_KEY),
        "model": GEMINI_MODEL_ID,
    }


@app.get("/debug-env")
def debug_env():
    return {
        "GEMINI_API_KEY_present": bool(GEMINI_API_KEY),
        "BACKEND_API_KEY_present": bool(BACKEND_API_KEY),
        "GEMINI_MODEL_ID": GEMINI_MODEL_ID,
    }


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

        result = process_prompt_text(row.text, user_id=user_id)

        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "user_id": user_id,
                "prompt_text": result["prompt"],
                "response": result["response"],
                "mode": result["mode"],
                "model_id": result["model_id"],
            }
        )

    except Exception as e:
        logger.exception("Server error during login flow.")
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": f"Server error: {e}"}
        )
    finally:
        if db is not None:
            db.close()


@app.post("/api/process-prompt")
def process_prompt_api(
    payload: PromptRequest,
    x_api_key: str | None = Header(default=None),
):
    if BACKEND_API_KEY and x_api_key != BACKEND_API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        result = process_prompt_text(payload.prompt)
        return JSONResponse(content=result)
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})
    except Exception as e:
        logger.exception("API processing failed.")
        return JSONResponse(status_code=500, content={"error": str(e)})