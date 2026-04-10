from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from app.models import Lesson, QuizQuestion


def make_client(tmp_path: Path) -> TestClient:
    db_file = tmp_path / "test_eng.db"
    app = create_app(db_url=f"sqlite:///{db_file.as_posix()}", testing=True)
    return TestClient(app)


def register_user(client: TestClient):
    response = client.post(
        "/register",
        data={
            "username": "alice",
            "email": "alice@example.com",
            "password": "StrongPass1",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard"


def test_auth_redirects_when_not_logged_in(tmp_path: Path):
    client = make_client(tmp_path)
    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_register_login_and_dashboard(tmp_path: Path):
    client = make_client(tmp_path)
    register_user(client)

    dashboard = client.get("/dashboard")
    assert dashboard.status_code == 200
    assert "Welcome, alice." in dashboard.text
    assert "Completed Lessons" in dashboard.text
    assert "Auto Conversation Zone" in dashboard.text
    assert "Start Auto Conversation" in dashboard.text

    client.get("/logout", follow_redirects=False)

    login = client.post(
        "/login",
        data={"identifier": "alice", "password": "StrongPass1"},
        follow_redirects=False,
    )
    assert login.status_code == 303
    assert login.headers["location"] == "/dashboard"


def test_quiz_submission_updates_progress(tmp_path: Path):
    client = make_client(tmp_path)
    register_user(client)

    with client.app.state.session_factory() as db:
        lesson = db.query(Lesson).order_by(Lesson.sort_order.asc()).first()
        assert lesson is not None
        questions = db.query(QuizQuestion).filter(QuizQuestion.lesson_id == lesson.id).all()
        assert questions

    form_payload = {f"q_{q.id}": q.correct_option for q in questions}
    response = client.post(f"/lesson/{lesson.id}/quiz", data=form_payload)

    assert response.status_code == 200
    assert "Your Score" in response.text
    assert "100.0%" in response.text

    progress = client.get("/api/progress")
    assert progress.status_code == 200
    progress_json = progress.json()
    assert progress_json["completed_lessons"] >= 1
    assert progress_json["avg_best_score"] >= 70


def test_speaking_attempt_api(tmp_path: Path):
    client = make_client(tmp_path)
    register_user(client)

    with client.app.state.session_factory() as db:
        lesson = db.query(Lesson).order_by(Lesson.sort_order.asc()).first()
        assert lesson is not None

    response = client.post(
        "/api/speaking/attempt",
        json={
            "lesson_id": lesson.id,
            "spoken_text": lesson.target_sentence,
            "target_sentence": lesson.target_sentence,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["accuracy"] >= 95
    assert "feedback" in payload


def test_dialogue_api_and_speaking_page(tmp_path: Path):
    client = make_client(tmp_path)
    register_user(client)

    with client.app.state.session_factory() as db:
        lesson = db.query(Lesson).order_by(Lesson.sort_order.asc()).first()
        assert lesson is not None

    speaking_page = client.get(f"/practice/speaking/{lesson.id}")
    assert speaking_page.status_code == 200
    assert "Instant Dialogue" in speaking_page.text
    assert "One-Click Auto Conversation" in speaking_page.text
    assert "Play Signal" in speaking_page.text

    response = client.post(
        "/api/dialogue/respond",
        json={
            "lesson_id": lesson.id,
            "message": "Hello teacher",
            "history": [],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] in {"local", "external"}
    assert payload["reply"]
