from __future__ import annotations

import os
import re
from datetime import UTC, datetime
from difflib import SequenceMatcher
from pathlib import Path

import httpx
from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from .auth import hash_password, validate_password_strength, verify_password
from .database import build_engine, build_session_factory, init_db
from .models import Lesson, LessonProgress, QuizAttempt, QuizQuestion, SpeakingAttempt, User
from .seed import seed_data

BASE_DIR = Path(__file__).resolve().parent


def normalize_text(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def utc_now() -> datetime:
    return datetime.now(UTC)


def get_or_create_progress(db: Session, user_id: int, lesson_id: int) -> LessonProgress:
    progress = db.query(LessonProgress).filter(
        LessonProgress.user_id == user_id,
        LessonProgress.lesson_id == lesson_id,
    ).first()
    if progress:
        return progress

    progress = LessonProgress(user_id=user_id, lesson_id=lesson_id, status="not_started")
    db.add(progress)
    db.flush()
    return progress


class SpeakingPayload(BaseModel):
    lesson_id: int
    spoken_text: str
    target_sentence: str | None = None


class DialogueTurn(BaseModel):
    role: str
    content: str


class DialoguePayload(BaseModel):
    lesson_id: int
    message: str
    history: list[DialogueTurn] = Field(default_factory=list)


def local_dialogue_reply(lesson: Lesson, user_message: str) -> str:
    normalized = normalize_text(user_message)

    if any(phrase in normalized for phrase in ["hello", "hi", "good morning", "good evening"]):
        return (
            f"Great start. For this lesson, try saying: '{lesson.target_sentence}'. "
            "Now tell me one sentence about your day."
        )

    if "my name" in normalized:
        return "Nice introduction. Add where you are from to make it more natural in conversation."

    if len(normalized.split()) < 4:
        return "Good try. Make a longer sentence with at least six words so we can improve fluency."

    return (
        "Nice sentence. Your grammar is mostly clear. "
        "Repeat it once more with slower pace and stronger final consonants for better clarity."
    )


def request_external_dialogue_reply(
    lesson: Lesson,
    user_message: str,
    history: list[DialogueTurn],
    api_key: str,
    model: str,
) -> str | None:
    endpoint = os.getenv("ENG_AI_ENDPOINT", "https://api.openai.com/v1/chat/completions")
    timeout_seconds = float(os.getenv("ENG_AI_TIMEOUT", "20"))

    system_prompt = (
        "You are an English fluency coach. "
        "Reply in short conversational English (1-3 sentences). "
        "Give practical corrections and keep encouragement high. "
        f"Current lesson topic: {lesson.title}. "
        f"Target sentence for reference: {lesson.target_sentence}"
    )

    messages = [{"role": "system", "content": system_prompt}]

    for turn in history[-8:]:
        role = turn.role.strip().lower()
        content = turn.content.strip()
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": user_message})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.5,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            response = client.post(endpoint, json=payload, headers=headers)
        if response.status_code >= 400:
            return None

        data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        return content or None
    except Exception:
        return None


def create_app(db_url: str | None = None, testing: bool = False) -> FastAPI:
    app = FastAPI(title="SpeakFlow English Platform", version="1.0.0")
    app.state.testing = testing

    app.add_middleware(
        SessionMiddleware,
        secret_key=os.getenv("ENG_SECRET_KEY", "dev-secret-key-change-me"),
        same_site="lax",
        https_only=False,
    )

    templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
    app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

    resolved_db_url = db_url or os.getenv("ENG_APP_DB", "sqlite:///./eng_platform.db")
    engine = build_engine(resolved_db_url)
    session_factory = build_session_factory(engine)
    app.state.session_factory = session_factory

    init_db(engine)

    with session_factory() as db:
        seed_data(db)

    def get_db(request: Request):
        db = request.app.state.session_factory()
        try:
            yield db
        finally:
            db.close()

    def current_user(request: Request, db: Session) -> User | None:
        user_id = request.session.get("user_id")
        if not user_id:
            return None
        return db.get(User, user_id)

    def render_template(request: Request, template_name: str, context: dict):
        payload = {
            "request": request,
            "current_year": utc_now().year,
        }
        payload.update(context)
        return templates.TemplateResponse(request, template_name, payload)

    @app.get("/")
    def home(request: Request, db: Session = Depends(get_db)):
        if current_user(request, db):
            return RedirectResponse(url="/dashboard", status_code=303)
        return RedirectResponse(url="/login", status_code=303)

    @app.get("/register")
    def register_page(request: Request, db: Session = Depends(get_db)):
        if current_user(request, db):
            return RedirectResponse(url="/dashboard", status_code=303)
        return render_template(request, "register.html", {"title": "Create account", "error": None})

    @app.post("/register")
    async def register(
        request: Request,
        username: str = Form(...),
        email: str = Form(...),
        password: str = Form(...),
        db: Session = Depends(get_db),
    ):
        if current_user(request, db):
            return RedirectResponse(url="/dashboard", status_code=303)

        username = username.strip()
        email = email.strip().lower()

        if not username or not email:
            return render_template(
                request,
                "register.html",
                {"title": "Create account", "error": "Username and email are required."},
            )

        strength_error = validate_password_strength(password)
        if strength_error:
            return render_template(request, "register.html", {"title": "Create account", "error": strength_error})

        existing_user = db.query(User).filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            return render_template(
                request,
                "register.html",
                {"title": "Create account", "error": "Username or email already exists."},
            )

        user = User(username=username, email=email, password_hash=hash_password(password))
        db.add(user)
        db.commit()
        db.refresh(user)

        request.session["user_id"] = user.id
        return RedirectResponse(url="/dashboard", status_code=303)

    @app.get("/login")
    def login_page(request: Request, db: Session = Depends(get_db)):
        if current_user(request, db):
            return RedirectResponse(url="/dashboard", status_code=303)
        return render_template(request, "login.html", {"title": "Login", "error": None})

    @app.post("/login")
    async def login(
        request: Request,
        identifier: str = Form(...),
        password: str = Form(...),
        db: Session = Depends(get_db),
    ):
        identifier = identifier.strip().lower()
        user = db.query(User).filter((User.email == identifier) | (User.username == identifier)).first()
        if not user or not verify_password(password, user.password_hash):
            return render_template(
                request,
                "login.html",
                {"title": "Login", "error": "Invalid credentials. Please try again."},
            )

        request.session["user_id"] = user.id
        return RedirectResponse(url="/dashboard", status_code=303)

    @app.get("/logout")
    def logout(request: Request):
        request.session.clear()
        return RedirectResponse(url="/login", status_code=303)

    @app.get("/dashboard")
    def dashboard(request: Request, db: Session = Depends(get_db)):
        user = current_user(request, db)
        if not user:
            return RedirectResponse(url="/login", status_code=303)

        lessons = db.query(Lesson).order_by(Lesson.sort_order.asc()).all()
        progress_rows = db.query(LessonProgress).filter(LessonProgress.user_id == user.id).all()
        progress_map = {item.lesson_id: item for item in progress_rows}
        completed_count = sum(1 for p in progress_rows if p.status == "completed")

        return render_template(
            request,
            "dashboard.html",
            {
                "title": "Dashboard",
                "user": user,
                "lessons": lessons,
                "progress_map": progress_map,
                "completed_count": completed_count,
                "total_lessons": len(lessons),
            },
        )

    @app.get("/lesson/{lesson_id}")
    def lesson_detail(lesson_id: int, request: Request, db: Session = Depends(get_db)):
        user = current_user(request, db)
        if not user:
            return RedirectResponse(url="/login", status_code=303)

        lesson = db.get(Lesson, lesson_id)
        if not lesson:
            raise HTTPException(status_code=404, detail="Lesson not found")

        progress = get_or_create_progress(db, user.id, lesson_id)
        db.commit()

        question_count = db.query(QuizQuestion).filter(QuizQuestion.lesson_id == lesson_id).count()
        return render_template(
            request,
            "lesson_detail.html",
            {
                "title": lesson.title,
                "user": user,
                "lesson": lesson,
                "progress": progress,
                "question_count": question_count,
            },
        )

    @app.get("/lesson/{lesson_id}/quiz")
    def quiz_page(lesson_id: int, request: Request, db: Session = Depends(get_db)):
        user = current_user(request, db)
        if not user:
            return RedirectResponse(url="/login", status_code=303)

        lesson = db.get(Lesson, lesson_id)
        if not lesson:
            raise HTTPException(status_code=404, detail="Lesson not found")

        questions = db.query(QuizQuestion).filter(QuizQuestion.lesson_id == lesson_id).all()
        if not questions:
            raise HTTPException(status_code=404, detail="Quiz not found")

        progress = get_or_create_progress(db, user.id, lesson_id)
        if progress.status == "not_started":
            progress.status = "in_progress"
        db.commit()

        return render_template(
            request,
            "quiz.html",
            {
                "title": f"Quiz - {lesson.title}",
                "user": user,
                "lesson": lesson,
                "questions": questions,
            },
        )

    @app.post("/lesson/{lesson_id}/quiz")
    async def submit_quiz(lesson_id: int, request: Request, db: Session = Depends(get_db)):
        user = current_user(request, db)
        if not user:
            return RedirectResponse(url="/login", status_code=303)

        lesson = db.get(Lesson, lesson_id)
        if not lesson:
            raise HTTPException(status_code=404, detail="Lesson not found")

        questions = db.query(QuizQuestion).filter(QuizQuestion.lesson_id == lesson_id).all()
        if not questions:
            raise HTTPException(status_code=404, detail="Quiz not found")

        form = await request.form()
        correct_answers = 0
        review_rows = []

        for question in questions:
            submitted = form.get(f"q_{question.id}")
            is_correct = submitted == question.correct_option
            if is_correct:
                correct_answers += 1
            review_rows.append(
                {
                    "question": question,
                    "submitted": submitted,
                    "is_correct": is_correct,
                }
            )

        total_questions = len(questions)
        score = round((correct_answers / total_questions) * 100, 2)

        attempt = QuizAttempt(
            user_id=user.id,
            lesson_id=lesson_id,
            score=score,
            total_questions=total_questions,
            correct_answers=correct_answers,
        )
        db.add(attempt)

        progress = get_or_create_progress(db, user.id, lesson_id)
        progress.attempts += 1
        progress.best_score = max(progress.best_score, score)
        progress.last_attempt_at = utc_now()
        progress.status = "completed" if score >= 70 else "in_progress"

        db.commit()

        return render_template(
            request,
            "quiz_result.html",
            {
                "title": f"Quiz Result - {lesson.title}",
                "user": user,
                "lesson": lesson,
                "score": score,
                "correct_answers": correct_answers,
                "total_questions": total_questions,
                "review_rows": review_rows,
                "passed": score >= 70,
            },
        )

    @app.get("/practice/speaking/{lesson_id}")
    def speaking_practice(lesson_id: int, request: Request, db: Session = Depends(get_db)):
        user = current_user(request, db)
        if not user:
            return RedirectResponse(url="/login", status_code=303)

        lesson = db.get(Lesson, lesson_id)
        if not lesson:
            raise HTTPException(status_code=404, detail="Lesson not found")

        return render_template(
            request,
            "speaking.html",
            {
                "title": f"Speaking - {lesson.title}",
                "user": user,
                "lesson": lesson,
            },
        )

    @app.post("/api/speaking/attempt")
    def speaking_attempt(payload: SpeakingPayload, request: Request, db: Session = Depends(get_db)):
        user = current_user(request, db)
        if not user:
            return JSONResponse(status_code=401, content={"detail": "Unauthorized"})

        lesson = db.get(Lesson, payload.lesson_id)
        if not lesson:
            return JSONResponse(status_code=404, content={"detail": "Lesson not found"})

        target = lesson.target_sentence
        spoken = payload.spoken_text.strip()
        if not spoken:
            return JSONResponse(status_code=400, content={"detail": "Spoken text cannot be empty"})

        normalized_target = normalize_text(target)
        normalized_spoken = normalize_text(spoken)
        ratio = SequenceMatcher(None, normalized_spoken, normalized_target).ratio()
        accuracy = round(ratio * 100, 2)

        db.add(
            SpeakingAttempt(
                user_id=user.id,
                lesson_id=lesson.id,
                target_sentence=target,
                spoken_text=spoken,
                accuracy=accuracy,
            )
        )

        progress = get_or_create_progress(db, user.id, lesson.id)
        progress.status = "completed" if accuracy >= 75 else progress.status
        progress.last_attempt_at = utc_now()

        db.commit()

        if accuracy >= 90:
            feedback = "Excellent pronunciation and fluency."
        elif accuracy >= 75:
            feedback = "Good work. Practice stress and rhythm for more natural speech."
        else:
            feedback = "Keep practicing. Speak slower and focus on key words."

        return {
            "accuracy": accuracy,
            "feedback": feedback,
            "target_sentence": target,
            "spoken_text": spoken,
        }

    @app.post("/api/dialogue/respond")
    def dialogue_respond(payload: DialoguePayload, request: Request, db: Session = Depends(get_db)):
        user = current_user(request, db)
        if not user:
            return JSONResponse(status_code=401, content={"detail": "Unauthorized"})

        lesson = db.get(Lesson, payload.lesson_id)
        if not lesson:
            return JSONResponse(status_code=404, content={"detail": "Lesson not found"})

        message = payload.message.strip()
        if not message:
            return JSONResponse(status_code=400, content={"detail": "Message cannot be empty"})

        provider = "local"
        reply = None

        api_key = os.getenv("ENG_AI_API_KEY") or os.getenv("OPENAI_API_KEY")
        model = os.getenv("ENG_AI_MODEL") or os.getenv("OPENAI_MODEL") or "gpt-4o-mini"

        if api_key and not request.app.state.testing:
            reply = request_external_dialogue_reply(lesson, message, payload.history, api_key, model)
            if reply:
                provider = "external"

        if not reply:
            reply = local_dialogue_reply(lesson, message)

        return {
            "reply": reply,
            "provider": provider,
            "lesson_id": lesson.id,
        }

    @app.get("/progress")
    def progress_page(request: Request, db: Session = Depends(get_db)):
        user = current_user(request, db)
        if not user:
            return RedirectResponse(url="/login", status_code=303)

        lessons = db.query(Lesson).order_by(Lesson.sort_order.asc()).all()
        progress_rows = db.query(LessonProgress).filter(LessonProgress.user_id == user.id).all()
        progress_map = {item.lesson_id: item for item in progress_rows}

        completed_count = sum(1 for p in progress_rows if p.status == "completed")
        avg_score = round(sum(p.best_score for p in progress_rows) / len(progress_rows), 2) if progress_rows else 0.0

        quiz_attempts = (
            db.query(QuizAttempt)
            .filter(QuizAttempt.user_id == user.id)
            .order_by(QuizAttempt.created_at.desc())
            .limit(8)
            .all()
        )
        speaking_attempts = (
            db.query(SpeakingAttempt)
            .filter(SpeakingAttempt.user_id == user.id)
            .order_by(SpeakingAttempt.created_at.desc())
            .limit(8)
            .all()
        )

        return render_template(
            request,
            "progress.html",
            {
                "title": "Progress",
                "user": user,
                "lessons": lessons,
                "progress_map": progress_map,
                "completed_count": completed_count,
                "total_lessons": len(lessons),
                "avg_score": avg_score,
                "quiz_attempts": quiz_attempts,
                "speaking_attempts": speaking_attempts,
            },
        )

    @app.get("/api/progress")
    def progress_api(request: Request, db: Session = Depends(get_db)):
        user = current_user(request, db)
        if not user:
            return JSONResponse(status_code=401, content={"detail": "Unauthorized"})

        total_lessons = db.query(Lesson).count()
        progress_rows = db.query(LessonProgress).filter(LessonProgress.user_id == user.id).all()
        completed = sum(1 for p in progress_rows if p.status == "completed")
        avg_best_score = round(sum(p.best_score for p in progress_rows) / len(progress_rows), 2) if progress_rows else 0.0

        return {
            "total_lessons": total_lessons,
            "completed_lessons": completed,
            "avg_best_score": avg_best_score,
            "active_lessons": total_lessons - completed,
        }

    return app


app = create_app()
