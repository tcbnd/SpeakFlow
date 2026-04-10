# SpeakFlow English Learning Platform

SpeakFlow is a complete English learning web platform built with FastAPI.

## Features

- User registration, login, and logout
- Structured lessons from A1 to C1
- Lesson detail pages with practical content
- Quiz system with scoring and pass threshold
- Speaking practice with browser speech recognition
- Instant dialogue mode for real-time conversation practice
- One-click voice-to-voice auto turn-taking conversation loop
- Progress dashboard with lesson status and recent attempts
- JSON APIs for speaking evaluation and progress summary
- Automated tests for key user flows

## Setup

```powershell
c:/Users/yoyo2/Downloads/eng/.venv/Scripts/python.exe -m pip install -r requirements.txt
```

## Run App

```powershell
c:/Users/yoyo2/Downloads/eng/.venv/Scripts/python.exe -m uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000` in your browser.

Use `Auto Conversation Zone` on dashboard home page to jump into voice mode. The voice access popup opens automatically when needed.

## Optional AI API

The app works without an API key using a built-in local conversation coach.

If you want external AI responses, set one of these environment variables before running:

- `ENG_AI_API_KEY` (or `OPENAI_API_KEY`)
- Optional model override: `ENG_AI_MODEL` (default `gpt-4o-mini`)
- Optional endpoint override: `ENG_AI_ENDPOINT`

## Run Tests

```powershell
c:/Users/yoyo2/Downloads/eng/.venv/Scripts/python.exe -m pytest -q
```
