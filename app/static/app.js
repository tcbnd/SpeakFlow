document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".reveal").forEach((node, idx) => {
        node.style.animationDelay = `${idx * 120}ms`;
    });

    const panel = document.querySelector("[data-speaking-panel]");
    if (!panel) {
        return;
    }

    const outputEl = panel.querySelector("[data-speaking-output]");
    const feedbackEl = panel.querySelector("[data-speaking-feedback]");
    const pronounceStatusEl = panel.querySelector("[data-pronounce-status]");
    const dialogueStatusEl = panel.querySelector("[data-dialogue-status]");
    const dialogueLogEl = panel.querySelector("[data-dialogue-log]");
    const dialogueInputEl = panel.querySelector("[data-dialogue-input]");
    const modalEl = panel.querySelector("[data-voice-modal]");
    const voiceAccessStatusEl = panel.querySelector("[data-voice-access-status]");
    const autoStartRequested = new URLSearchParams(window.location.search).get("auto") === "1";

    const grantVoiceAccessButton = panel.querySelector("[data-action='grant-voice-access']");
    const closeVoiceAccessButtons = panel.querySelectorAll("[data-action='close-voice-modal']");
    const playSampleButton = panel.querySelector("[data-action='play-sample']");
    const startAutoButton = panel.querySelector("[data-action='start-auto-dialogue']");
    const stopAutoButton = panel.querySelector("[data-action='stop-auto-dialogue']");
    const startPronunciationButton = panel.querySelector("[data-action='start-listening']");
    const stopPronunciationButton = panel.querySelector("[data-action='stop-listening']");
    const submitPronunciationButton = panel.querySelector("[data-action='submit-speaking']");
    const speakMessageButton = panel.querySelector("[data-action='speak-message']");
    const sendDialogueButton = panel.querySelector("[data-action='send-dialogue']");
    const replayReplyButton = panel.querySelector("[data-action='replay-reply']");

    const lessonId = Number(panel.getAttribute("data-lesson-id"));
    const targetSentence = panel.getAttribute("data-target-sentence") || "";

    const speechSynthesisApi = window.speechSynthesis;
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    let pronunciationRecognition = null;
    let dialogueRecognition = null;
    let pronunciationTranscript = "";
    let dialogueTranscript = "";
    let lastAssistantReply = "";
    let preferredVoice = null;
    let audioEnabled = false;
    let micEnabled = false;
    let hasPlayedSample = false;
    let autoMode = false;
    let dialogueListening = false;
    let dialogueCaptureMode = "manual";
    let dialogueRequestInFlight = false;

    const history = [];

    const updatePronounceStatus = (message) => {
        if (pronounceStatusEl) {
            pronounceStatusEl.textContent = message;
        }
    };

    const updateDialogueStatus = (message) => {
        if (dialogueStatusEl) {
            dialogueStatusEl.textContent = message;
        }
    };

    const updateVoiceAccessStatus = (message) => {
        if (voiceAccessStatusEl) {
            voiceAccessStatusEl.textContent = message;
        }
    };

    const openVoiceModal = () => {
        if (modalEl) {
            modalEl.hidden = false;
        }
    };

    const closeVoiceModal = () => {
        if (modalEl) {
            modalEl.hidden = true;
        }
    };

    const selectPreferredVoice = () => {
        if (!speechSynthesisApi) {
            return;
        }

        const voices = speechSynthesisApi.getVoices();
        preferredVoice = voices.find((voice) => voice.lang && voice.lang.toLowerCase().startsWith("en-us"));
        if (!preferredVoice) {
            preferredVoice = voices.find((voice) => voice.lang && voice.lang.toLowerCase().startsWith("en"));
        }
        if (!preferredVoice) {
            preferredVoice = voices[0] || null;
        }
    };

    const stopCurrentSpeech = () => {
        if (speechSynthesisApi && (speechSynthesisApi.speaking || speechSynthesisApi.pending)) {
            speechSynthesisApi.cancel();
        }
    };

    const enableAudioPlayback = () => {
        if (!speechSynthesisApi) {
            updatePronounceStatus("Speech output is not supported in this browser.");
            return false;
        }

        speechSynthesisApi.resume();
        selectPreferredVoice();
        audioEnabled = true;
        return true;
    };

    const requestMicPermission = async () => {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            updateVoiceAccessStatus("Microphone API is not supported in this browser.");
            return false;
        }

        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            stream.getTracks().forEach((track) => track.stop());
            micEnabled = true;
            return true;
        } catch (error) {
            updateVoiceAccessStatus("Microphone access was denied. Please allow permission.");
            return false;
        }
    };

    const grantVoiceAccess = async () => {
        updateVoiceAccessStatus("Requesting microphone and audio access...");

        const audioOk = enableAudioPlayback();
        const micOk = await requestMicPermission();

        if (audioOk && micOk) {
            updateVoiceAccessStatus("Voice access enabled. You can start auto conversation now.");
            updatePronounceStatus("Voice access enabled. Press the Play Signal button.");
            closeVoiceModal();
            return true;
        }

        return false;
    };

    const speakText = (text, options = {}) => {
        const onEnd = options.onEnd;
        const onError = options.onError;

        if (!audioEnabled || !speechSynthesisApi || !text || !text.trim()) {
            return false;
        }

        stopCurrentSpeech();
        const utterance = new SpeechSynthesisUtterance(text.trim());
        utterance.lang = "en-US";
        utterance.rate = 0.95;
        utterance.pitch = 1;

        if (preferredVoice) {
            utterance.voice = preferredVoice;
        }

        utterance.onend = () => {
            if (onEnd) {
                onEnd();
            }
        };

        utterance.onerror = () => {
            updatePronounceStatus("Audio playback failed. Open Voice Access and try again.");
            if (onError) {
                onError();
            }
        };

        speechSynthesisApi.speak(utterance);
        return true;
    };

    const appendDialogueBubble = (role, message) => {
        if (!dialogueLogEl) {
            return;
        }

        const bubble = document.createElement("div");
        bubble.className = `dialogue-item ${role}`;
        bubble.textContent = message;
        dialogueLogEl.appendChild(bubble);
        dialogueLogEl.scrollTop = dialogueLogEl.scrollHeight;
    };

    const pushHistory = (role, content) => {
        history.push({ role, content });
        if (history.length > 16) {
            history.splice(0, history.length - 16);
        }
    };

    const playSamplePronunciation = () => {
        if (!targetSentence) {
            updatePronounceStatus("No target sentence available for pronunciation.");
            return;
        }

        if (!audioEnabled) {
            openVoiceModal();
            updatePronounceStatus("Open Voice Access first, then play the sample.");
            return;
        }

        updatePronounceStatus("Playing sample pronunciation...");
        speakText(targetSentence, {
            onEnd: () => {
                hasPlayedSample = true;
                updatePronounceStatus("Sample played. Now record your pronunciation.");
            },
        });
    };

    const sendDialogueMessage = async (message, fromAutoMode) => {
        const finalMessage = (message || "").trim();
        if (!finalMessage || dialogueRequestInFlight) {
            return;
        }

        dialogueRequestInFlight = true;
        appendDialogueBubble("user", finalMessage);
        pushHistory("user", finalMessage);

        if (dialogueInputEl) {
            dialogueInputEl.value = "";
        }
        updateDialogueStatus("Coach is replying...");

        try {
            const response = await fetch("/api/dialogue/respond", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    lesson_id: lessonId,
                    message: finalMessage,
                    history,
                }),
            });

            const data = await response.json();
            if (!response.ok) {
                updateDialogueStatus(data.detail || "Could not get a dialogue reply.");
                if (autoMode && fromAutoMode) {
                    setTimeout(() => {
                        startAutoListening();
                    }, 450);
                }
                return;
            }

            const reply = (data.reply || "Please try again.").trim();
            appendDialogueBubble("assistant", reply);
            pushHistory("assistant", reply);
            lastAssistantReply = reply;
            updateDialogueStatus("Reply received. Continue the conversation.");

            if (audioEnabled) {
                speakText(reply, {
                    onEnd: () => {
                        if (autoMode && fromAutoMode) {
                            setTimeout(() => {
                                startAutoListening();
                            }, 250);
                        }
                    },
                });
            } else if (autoMode && fromAutoMode) {
                setTimeout(() => {
                    startAutoListening();
                }, 300);
            }
        } catch (error) {
            updateDialogueStatus("Network error while requesting dialogue reply.");
            if (autoMode && fromAutoMode) {
                setTimeout(() => {
                    startAutoListening();
                }, 500);
            }
        } finally {
            dialogueRequestInFlight = false;
        }
    };

    const stopAutoDialogue = () => {
        autoMode = false;
        dialogueListening = false;
        stopCurrentSpeech();

        if (dialogueRecognition) {
            try {
                dialogueRecognition.stop();
            } catch (error) {
                // No action needed if recognition was not active.
            }
        }

        updateDialogueStatus("Auto conversation stopped.");
    };

    const startAutoListening = () => {
        if (!autoMode || !dialogueRecognition || dialogueListening) {
            return;
        }

        if (speechSynthesisApi && speechSynthesisApi.speaking) {
            setTimeout(() => {
                startAutoListening();
            }, 200);
            return;
        }

        dialogueCaptureMode = "auto";
        dialogueTranscript = "";
        dialogueListening = true;
        updateDialogueStatus("Listening... speak now.");

        try {
            dialogueRecognition.start();
        } catch (error) {
            dialogueListening = false;
            setTimeout(() => {
                startAutoListening();
            }, 400);
        }
    };

    const startAutoDialogue = async () => {
        if (!dialogueRecognition) {
            updateDialogueStatus("Speech recognition is not supported in this browser.");
            return;
        }

        const voiceReady = await grantVoiceAccess();
        if (!voiceReady) {
            openVoiceModal();
            updateDialogueStatus("Please complete Voice Access first.");
            return;
        }

        autoMode = true;
        updateDialogueStatus("Auto conversation started.");
        startAutoListening();
    };

    if (speechSynthesisApi) {
        selectPreferredVoice();
        if (typeof speechSynthesisApi.addEventListener === "function") {
            speechSynthesisApi.addEventListener("voiceschanged", selectPreferredVoice);
        }
    }

    if (SpeechRecognition) {
        pronunciationRecognition = new SpeechRecognition();
        pronunciationRecognition.lang = "en-US";
        pronunciationRecognition.interimResults = true;
        pronunciationRecognition.continuous = false;

        pronunciationRecognition.onresult = (event) => {
            pronunciationTranscript = "";
            for (let i = 0; i < event.results.length; i += 1) {
                pronunciationTranscript += event.results[i][0].transcript;
            }
            outputEl.textContent = pronunciationTranscript.trim() || "Listening...";
        };

        pronunciationRecognition.onerror = () => {
            outputEl.textContent = "Speech recognition error. Please try again.";
        };

        pronunciationRecognition.onend = () => {
            if (!pronunciationTranscript.trim()) {
                outputEl.textContent = "No speech captured. Try speaking louder and closer to the microphone.";
            }
        };
    } else {
        outputEl.textContent = "Speech recognition is not supported in this browser. Use Chrome or Edge.";
    }

    if (SpeechRecognition) {
        dialogueRecognition = new SpeechRecognition();
        dialogueRecognition.lang = "en-US";
        dialogueRecognition.interimResults = false;
        dialogueRecognition.continuous = false;

        dialogueRecognition.onresult = (event) => {
            const phrase = event.results[0] && event.results[0][0] ? event.results[0][0].transcript : "";
            dialogueTranscript = phrase.trim();
        };

        dialogueRecognition.onerror = () => {
            dialogueListening = false;
            if (autoMode) {
                updateDialogueStatus("Could not capture voice. Listening again...");
                setTimeout(() => {
                    startAutoListening();
                }, 450);
            } else {
                updateDialogueStatus("Could not capture voice message. Please try again.");
            }
        };

        dialogueRecognition.onend = () => {
            const captured = dialogueTranscript.trim();
            dialogueListening = false;

            if (!captured) {
                if (autoMode) {
                    updateDialogueStatus("No speech detected. Listening again...");
                    setTimeout(() => {
                        startAutoListening();
                    }, 450);
                } else {
                    updateDialogueStatus("No voice message detected.");
                }
                return;
            }

            if (dialogueCaptureMode === "auto" && autoMode) {
                sendDialogueMessage(captured, true);
            } else {
                if (dialogueInputEl) {
                    dialogueInputEl.value = captured;
                }
                sendDialogueMessage(captured, false);
            }
        };
    }

    appendDialogueBubble(
        "assistant",
        "Hello. I am your fluency coach. Press One-Click Auto Conversation to start voice-to-voice practice."
    );

    closeVoiceAccessButtons.forEach((button) => {
        button.addEventListener("click", () => {
            closeVoiceModal();
        });
    });

    if (grantVoiceAccessButton) {
        grantVoiceAccessButton.addEventListener("click", async () => {
            await grantVoiceAccess();
        });
    }

    if (playSampleButton) {
        playSampleButton.addEventListener("click", () => {
            playSamplePronunciation();
        });
    }

    if (startPronunciationButton) {
        startPronunciationButton.addEventListener("click", () => {
            if (!pronunciationRecognition) {
                return;
            }

            if (!hasPlayedSample) {
                playSamplePronunciation();
                return;
            }

            pronunciationTranscript = "";
            outputEl.textContent = "Listening...";
            try {
                pronunciationRecognition.start();
            } catch (error) {
                outputEl.textContent = "Recorder is busy. Please try again.";
            }
        });
    }

    if (stopPronunciationButton) {
        stopPronunciationButton.addEventListener("click", () => {
            if (!pronunciationRecognition) {
                return;
            }
            pronunciationRecognition.stop();
        });
    }

    if (submitPronunciationButton) {
        submitPronunciationButton.addEventListener("click", async () => {
            const spokenText = pronunciationTranscript.trim();
            if (!spokenText) {
                feedbackEl.textContent = "Please record your voice before evaluation.";
                return;
            }

            feedbackEl.textContent = "Evaluating your pronunciation...";

            try {
                const response = await fetch("/api/speaking/attempt", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify({
                        lesson_id: lessonId,
                        spoken_text: spokenText,
                        target_sentence: targetSentence,
                    }),
                });

                const data = await response.json();
                if (!response.ok) {
                    feedbackEl.textContent = data.detail || "Could not evaluate speaking attempt.";
                    return;
                }

                feedbackEl.textContent = `Accuracy: ${data.accuracy}% - ${data.feedback}`;
            } catch (error) {
                feedbackEl.textContent = "Network error. Please try again.";
            }
        });
    }

    if (speakMessageButton) {
        speakMessageButton.addEventListener("click", () => {
            if (!dialogueRecognition) {
                updateDialogueStatus("Speech recognition is not supported in this browser.");
                return;
            }

            dialogueCaptureMode = "manual";
            dialogueTranscript = "";
            updateDialogueStatus("Listening for your message...");
            try {
                dialogueRecognition.start();
            } catch (error) {
                updateDialogueStatus("Voice recognizer is busy. Please try again.");
            }
        });
    }

    if (sendDialogueButton) {
        sendDialogueButton.addEventListener("click", async () => {
            const typed = dialogueInputEl ? dialogueInputEl.value.trim() : "";
            await sendDialogueMessage(typed, false);
        });
    }

    if (dialogueInputEl) {
        dialogueInputEl.addEventListener("keydown", async (event) => {
            if (event.key === "Enter") {
                event.preventDefault();
                await sendDialogueMessage(dialogueInputEl.value.trim(), false);
            }
        });
    }

    if (replayReplyButton) {
        replayReplyButton.addEventListener("click", () => {
            if (!lastAssistantReply) {
                updateDialogueStatus("No coach reply to replay yet.");
                return;
            }

            if (!audioEnabled) {
                openVoiceModal();
                updateDialogueStatus("Open Voice Access first, then replay reply.");
                return;
            }

            speakText(lastAssistantReply);
            updateDialogueStatus("Replaying latest reply.");
        });
    }

    if (startAutoButton) {
        startAutoButton.addEventListener("click", async () => {
            await startAutoDialogue();
        });
    }

    if (stopAutoButton) {
        stopAutoButton.addEventListener("click", () => {
            stopAutoDialogue();
        });
    }

    if (autoStartRequested) {
        updateDialogueStatus("Auto conversation requested from home page. Starting...");
        setTimeout(async () => {
            await startAutoDialogue();
        }, 120);
    }
});
