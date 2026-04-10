from __future__ import annotations

from sqlalchemy.orm import Session

from .models import Lesson, QuizQuestion


def seed_data(session: Session) -> None:
    if session.query(Lesson).count() > 0:
        return

    lessons_data = [
        {
            "title": "Daily Introductions",
            "level": "A1",
            "description": "Introduce yourself with confidence in daily conversations.",
            "target_sentence": "Hello, my name is Mia and I am from Hanoi.",
            "content": (
                "Use simple present tense for facts about yourself.\\n"
                "Useful starters: Hello, My name is..., I am from..., I work as..."
            ),
            "questions": [
                {
                    "prompt": "Choose the best introduction sentence.",
                    "option_a": "Hello, my name are Leo.",
                    "option_b": "Hello, my name is Leo.",
                    "option_c": "Hello, me name Leo.",
                    "option_d": "Hello, I name Leo is.",
                    "correct_option": "b",
                },
                {
                    "prompt": "Which sentence is correct?",
                    "option_a": "I am from Vietnam.",
                    "option_b": "I from Vietnam.",
                    "option_c": "I are from Vietnam.",
                    "option_d": "I be from Vietnam.",
                    "correct_option": "a",
                },
                {
                    "prompt": "Pick the correct job sentence.",
                    "option_a": "I work as designer.",
                    "option_b": "I am work a designer.",
                    "option_c": "I work as a designer.",
                    "option_d": "I working as designer.",
                    "correct_option": "c",
                },
            ],
        },
        {
            "title": "Ordering at a Cafe",
            "level": "A2",
            "description": "Order drinks and food politely and naturally.",
            "target_sentence": "Could I get a cappuccino and a cheese sandwich, please?",
            "content": (
                "Use polite requests with Could I... or Can I have...\\n"
                "Add please at the end for a friendly tone."
            ),
            "questions": [
                {
                    "prompt": "Most polite request at a cafe:",
                    "option_a": "Give me coffee.",
                    "option_b": "Coffee now.",
                    "option_c": "Could I get a coffee, please?",
                    "option_d": "I take coffee.",
                    "correct_option": "c",
                },
                {
                    "prompt": "Choose the correct sentence.",
                    "option_a": "Can I have two cookies?",
                    "option_b": "Can I has two cookies?",
                    "option_c": "Can I having two cookies?",
                    "option_d": "Can have I two cookies?",
                    "correct_option": "a",
                },
                {
                    "prompt": "Best response to 'Anything else?':",
                    "option_a": "No, that all.",
                    "option_b": "No, thats all, thanks.",
                    "option_c": "No all, thanks.",
                    "option_d": "No this all thanks to.",
                    "correct_option": "b",
                },
            ],
        },
        {
            "title": "Talking About Plans",
            "level": "B1",
            "description": "Discuss future plans with friends and colleagues.",
            "target_sentence": "I am going to visit my grandparents this weekend.",
            "content": (
                "Use 'going to' for planned actions and intentions.\\n"
                "Example: I am going to start a new course next month."
            ),
            "questions": [
                {
                    "prompt": "Choose the correct future plan sentence.",
                    "option_a": "I going to travel tomorrow.",
                    "option_b": "I am going to travel tomorrow.",
                    "option_c": "I am go to travel tomorrow.",
                    "option_d": "I gone to travel tomorrow.",
                    "correct_option": "b",
                },
                {
                    "prompt": "Which one is grammatically correct?",
                    "option_a": "She going to cook tonight.",
                    "option_b": "She is going cook tonight.",
                    "option_c": "She is going to cook tonight.",
                    "option_d": "She is go to cook tonight.",
                    "correct_option": "c",
                },
                {
                    "prompt": "Best completion: 'Tomorrow, we ... a meeting.'",
                    "option_a": "are going to have",
                    "option_b": "going to have",
                    "option_c": "is going to have",
                    "option_d": "are go to have",
                    "correct_option": "a",
                },
            ],
        },
        {
            "title": "Professional Meetings",
            "level": "B2",
            "description": "Lead meeting discussions with clear business language.",
            "target_sentence": "Let us review the timeline before we finalize the budget.",
            "content": (
                "Use formal verbs such as review, finalize, and clarify in meetings.\\n"
                "Frame suggestions with: Let us..., I suggest that..., Could we..."
            ),
            "questions": [
                {
                    "prompt": "Choose the most professional phrase.",
                    "option_a": "Let us review the timeline.",
                    "option_b": "Check timeline now.",
                    "option_c": "Timeline look now.",
                    "option_d": "You do timeline check.",
                    "correct_option": "a",
                },
                {
                    "prompt": "Best sentence for proposing an idea:",
                    "option_a": "I suggest that we postpone the launch.",
                    "option_b": "I suggest postpone launch we.",
                    "option_c": "Suggest we to postpone launch.",
                    "option_d": "I am suggest launch postpone.",
                    "correct_option": "a",
                },
                {
                    "prompt": "Pick the correct conditional statement.",
                    "option_a": "If we reduce costs, we will increase profit.",
                    "option_b": "If we will reduce costs, we increase profit.",
                    "option_c": "If we reduce costs, we increase will profit.",
                    "option_d": "If reduced costs, we will increased profit.",
                    "correct_option": "a",
                },
            ],
        },
        {
            "title": "Public Speaking Fluency",
            "level": "C1",
            "description": "Deliver persuasive ideas with fluency and precision.",
            "target_sentence": "The evidence clearly demonstrates why this strategy is sustainable in the long term.",
            "content": (
                "Use discourse markers: firstly, moreover, consequently, and ultimately.\\n"
                "Aim for complex but clear sentence structures when presenting arguments."
            ),
            "questions": [
                {
                    "prompt": "Which phrase shows strong argumentation?",
                    "option_a": "I think this maybe good.",
                    "option_b": "The evidence clearly demonstrates this point.",
                    "option_c": "This maybe true because yes.",
                    "option_d": "It is good maybe because things.",
                    "correct_option": "b",
                },
                {
                    "prompt": "Best transition for adding a point:",
                    "option_a": "By the way",
                    "option_b": "Moreover",
                    "option_c": "Anyway",
                    "option_d": "You know",
                    "correct_option": "b",
                },
                {
                    "prompt": "Pick the most formal conclusion sentence.",
                    "option_a": "So yeah, that is it.",
                    "option_b": "And done.",
                    "option_c": "In conclusion, this approach offers measurable long-term benefits.",
                    "option_d": "That is all from me, okay.",
                    "correct_option": "c",
                },
            ],
        },
    ]

    for index, lesson_data in enumerate(lessons_data, start=1):
        lesson = Lesson(
            title=lesson_data["title"],
            level=lesson_data["level"],
            description=lesson_data["description"],
            content=lesson_data["content"],
            target_sentence=lesson_data["target_sentence"],
            sort_order=index,
        )
        session.add(lesson)
        session.flush()

        for question in lesson_data["questions"]:
            session.add(
                QuizQuestion(
                    lesson_id=lesson.id,
                    prompt=question["prompt"],
                    option_a=question["option_a"],
                    option_b=question["option_b"],
                    option_c=question["option_c"],
                    option_d=question["option_d"],
                    correct_option=question["correct_option"],
                )
            )

    session.commit()
