import os
import sys
import time
import threading
import tempfile
import subprocess
import webbrowser
from datetime import datetime
import customtkinter as ctk  # pip install customtkinter
from tkinter import messagebox
from PIL import ImageGrab
import pytesseract
import cv2
import numpy as np
import requests
import simpleaudio as sa

# ─────────────── USER CONFIGURATION ─────────────── #

TARGET_URL            = "https://emochi.com/"              # URL to open at start
OUTPUT_TEXT_PATH      = "captured_screen_text.txt"         # where to save detected lines
LOG_FILE_PATH         = "capture_log.txt"                  # timestamped log
ELEVENLABS_API_URL    = "https://api.elevenlabs.io/v1/text-to-speech"

OCR_INTERVAL          = 2.0    # seconds between screen grabs
MIN_CONFIDENCE        = 60     # minimum OCR confidence
API_INFO_FILENAME     = "apiINFO.txt"                      # must exist next to this script

# ──────────────────────────────────────────────────── #

ocr_active = threading.Event()
ocr_thread_started = False
current_play_obj = None   # tracks the currently playing audio

def load_api_info():
    """
    Reads API key + (FriendlyName,VoiceID) pairs from apiINFO.txt.
    Expected format:
      Line 1: <ELEVENLABS_API_KEY>
      Lines 2+: <FriendlyName>,<VoiceID>
    Exits with a pop-up if missing or malformed.
    Returns (api_key, [(name1, id1), ...]).
    """
    if not os.path.exists(API_INFO_FILENAME):
        messagebox.showerror(
            "apiINFO.txt Not Found",
            f"Could not find '{API_INFO_FILENAME}'.\n"
            "Create it with:\n"
            "  Line 1: Your ElevenLabs API key\n"
            "  Lines 2+: FriendlyName,VoiceID"
        )
        sys.exit(1)

    with open(API_INFO_FILENAME, "r", encoding="utf-8") as f:
        lines = [ln.strip() for ln in f.readlines() if ln.strip()]

    if len(lines) < 2:
        messagebox.showerror(
            "apiINFO.txt Format Error",
            f"'{API_INFO_FILENAME}' needs at least 2 lines.\n"
            "Line 1: Your API key\n"
            "Lines 2+: FriendlyName,VoiceID"
        )
        sys.exit(1)

    api_key = lines[0]
    voice_entries = []
    for idx, entry in enumerate(lines[1:], start=2):
        if "," not in entry:
            messagebox.showerror(
                "apiINFO.txt Format Error",
                f"Line {idx} must be 'FriendlyName,VoiceID'.\nGot: '{entry}'"
            )
            sys.exit(1)
        name, vid = entry.split(",", 1)
        name = name.strip()
        vid = vid.strip()
        if not name or not vid:
            messagebox.showerror(
                "apiINFO.txt Format Error",
                f"Line {idx} has empty name or empty VoiceID.\nGot: '{entry}'"
            )
            sys.exit(1)
        voice_entries.append((name, vid))
    return api_key, voice_entries

def elevenlabs_tts(text, api_key, voice_id):
    """
    Sends SSML-wrapped text → ElevenLabs TTS → returns raw MP3 bytes.
    The SSML uses <prosody> to lower pitch and slow rate (seductive tone).
    """
    ssml_text = (
        "<speak>"
        "<prosody pitch=\"low\" rate=\"80%\">"
        f"{text}"
        "</prosody>"
        "</speak>"
    )

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "xi-api-key": api_key
    }
    payload = {
        "text": ssml_text,
        "voice_id": voice_id,
        "model_id": "eleven_multilingual_v1"
    }
    url = f"{ELEVENLABS_API_URL}/{voice_id}"
    resp = requests.post(url, headers=headers, json=payload, stream=True)
    if resp.status_code != 200:
        raise RuntimeError(f"TTS failed: {resp.status_code} {resp.text}")
    return resp.content

def play_audio_bytes(audio_bytes):
    """
    Writes MP3 bytes to a temp file, uses pydub→raw PCM→simpleaudio to play.
    Sets global current_play_obj so we can stop it mid-play when "Stop Reading" is pressed.
    """
    global current_play_obj
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tf:
        tf.write(audio_bytes)
        temp_path = tf.name

    try:
        from pydub import AudioSegment
        seg = AudioSegment.from_file(temp_path)  # requires ffmpeg on PATH
        data = seg.raw_data
        channels = seg.channels
        width = seg.sample_width
        rate = seg.frame_rate
        play_obj = sa.play_buffer(data, channels, width, rate)
        current_play_obj = play_obj
        play_obj.wait_done()
    except Exception as e:
        print("Audio playback error (pydub/ffmpeg required):", e)
    finally:
        current_play_obj = None
        os.remove(temp_path)

def ocr_loop(api_key, first_person_voice_id, narrator_voice_id):
    """
    When ocr_active.is_set(), captures full screen every OCR_INTERVAL, logs,
    and speaks each line in a seductive tone. If a line contains quotes ("), 
    use first-person voice with "I said:" prefix; otherwise, speak line verbatim.
    """
    seen_lines = set()

    # Prepare/clear output text file
    if not os.path.exists(OUTPUT_TEXT_PATH):
        open(OUTPUT_TEXT_PATH, "w", encoding="utf-8").close()

    # Start fresh log
    with open(LOG_FILE_PATH, "w", encoding="utf-8") as lf:
        lf.write(f"=== OCR Capture Log started at {datetime.now():%Y-%m-%d %H:%M:%S} ===\n")

    # Tesseract config: OEM 3, PSM 6, whitelist
    tess_config = (
        "--oem 3 "
        "--psm 6 "
        "-c tessedit_char_whitelist="
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "abcdefghijklmnopqrstuvwxyz"
        "0123456789"
        ".,!?%:;-’'\"()"
    )

    print(">> OCR loop running (awaiting ocr_active).")
    while True:
        if not ocr_active.is_set():
            time.sleep(0.1)
            continue

        # 1) Capture full-screen screenshot
        screen = ImageGrab.grab()
        rgb = cv2.cvtColor(np.array(screen), cv2.COLOR_BGR2RGB)

        # 2) Run Tesseract OCR
        data = pytesseract.image_to_data(rgb, output_type=pytesseract.Output.DICT)
        n = len(data["level"])
        line_map, bbox_map = {}, {}

        for i in range(n):
            conf = int(data["conf"][i] or 0)
            if conf < MIN_CONFIDENCE:
                continue

            key = (
                data["page_num"][i],
                data["block_num"][i],
                data["par_num"][i],
                data["line_num"][i],
            )
            word = data["text"][i].strip()
            if not word:
                continue

            x, y, w, h = (
                data["left"][i],
                data["top"][i],
                data["width"][i],
                data["height"][i]
            )
            if key not in line_map:
                line_map[key] = [word]
                bbox_map[key] = [x, y, x + w, y + h]
            else:
                line_map[key].append(word)
                x1, y1, x2, y2 = bbox_map[key]
                bbox_map[key] = [
                    min(x1, x),
                    min(y1, y),
                    max(x2, x + w),
                    max(y2, y + h),
                ]

        # 3) Process each new line sequentially
        for key, words in line_map.items():
            line_text = " ".join(words).strip()
            if not line_text or line_text in seen_lines:
                continue

            seen_lines.add(line_text)

            # a) Append to captured-text file
            with open(OUTPUT_TEXT_PATH, "a", encoding="utf-8") as f:
                f.write(line_text + "\n")

            # b) Append to log with timestamp
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            entry = f"[{ts}] {line_text}\n"
            with open(LOG_FILE_PATH, "a", encoding="utf-8") as lf:
                lf.write(entry)

            # c) Choose voice and prefix
            if '"' in line_text:
                to_speak = f"I said: {line_text}"
                voice_id = first_person_voice_id
            else:
                to_speak = line_text
                voice_id = narrator_voice_id

            # d) Speak via ElevenLabs TTS with seductive SSML
            try:
                audio_bytes = elevenlabs_tts(to_speak, api_key, voice_id)
                play_audio_bytes(audio_bytes)
            except Exception as e:
                err = f"[TTS error at {ts} on '{line_text}']: {e}\n"
                with open(LOG_FILE_PATH, "a", encoding="utf-8") as lf:
                    lf.write(err)
                print(err, end="")

            time.sleep(0.2)

        time.sleep(OCR_INTERVAL)

def launch_chrome_new_window(url):
    """
    Launches a new Chrome window explicitly for the given URL.
    """
    try:
        subprocess.Popen(
            ['start', 'chrome', '--new-window', url],
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except Exception:
        webbrowser.open_new(url)

# ────────────────────────── CUSTOMTKINTER GUI ────────────────────────── #

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.title("OCR Control Panel")
app.geometry("400x350")
app.resizable(False, False)

# Load voices and map names → IDs
api_key, voice_entries = load_api_info()
voice_names = [name for name, _ in voice_entries]

# ───────────── VOICE SELECTORS ───────────── #

# First-Person Voice
ctk.CTkLabel(app, text="Select First-Person Voice", font=("Segoe UI", 14)).pack(pady=(20, 5))
voice_var1 = ctk.StringVar(value=voice_names[0])
voice_menu1 = ctk.CTkOptionMenu(app, values=voice_names, variable=voice_var1)
voice_menu1.pack(pady=(0, 10))

# Narrator Voice
ctk.CTkLabel(app, text="Select Narrator Voice", font=("Segoe UI", 14)).pack(pady=(10, 5))
voice_var2 = ctk.StringVar(value=voice_names[0])
voice_menu2 = ctk.CTkOptionMenu(app, values=voice_names, variable=voice_var2)
voice_menu2.pack(pady=(0, 20))

# ───────────── BUTTONS ───────────── #
button_frame = ctk.CTkFrame(app)
button_frame.pack(pady=(10, 10))

def start_reading():
    global ocr_thread_started, first_person_voice_id, narrator_voice_id
    # Map selected names back to IDs
    name1 = voice_var1.get()
    name2 = voice_var2.get()
    first_person_voice_id = next(vid for nm, vid in voice_entries if nm == name1)
    narrator_voice_id = next(vid for nm, vid in voice_entries if nm == name2)

    if not ocr_thread_started:
        threading.Thread(
            target=ocr_loop,
            args=(api_key, first_person_voice_id, narrator_voice_id),
            daemon=True
        ).start()
        ocr_thread_started = True

    ocr_active.set()
    status_label.configure(text="Status: RUNNING", text_color="green")

def stop_reading():
    # 1) Stop new lines from being read
    ocr_active.clear()
    # 2) If audio is currently playing, stop it immediately
    global current_play_obj
    if current_play_obj is not None:
        try:
            current_play_obj.stop()
        except Exception:
            pass
    status_label.configure(text="Status: PAUSED", text_color="orange")

def quit_app():
    app.destroy()
    time.sleep(0.2)
    if os.path.exists(LOG_FILE_PATH):
        print("\n=== Printing capture log ===")
        with open(LOG_FILE_PATH, "r", encoding="utf-8") as lf:
            for line in lf:
                print(line, end="")
    else:
        print(f"No log file ({LOG_FILE_PATH}) found.")
    sys.exit(0)

ctk.CTkButton(button_frame, text="Start Reading", command=start_reading).grid(row=0, column=0, padx=5)
ctk.CTkButton(button_frame, text="Stop Reading", command=stop_reading).grid(row=0, column=1, padx=5)
ctk.CTkButton(button_frame, text="Quit", command=quit_app).grid(row=0, column=2, padx=5)

# ───────────── STATUS LABEL ───────────── #
status_label = ctk.CTkLabel(app, text="Status: PAUSED", font=("Segoe UI", 14), text_color="orange")
status_label.pack(pady=10)

# ───────────── RUN ───────────── #
# 1) Open a new Chrome window to emochi.com
launch_chrome_new_window(TARGET_URL)

# 2) Clear previous log if present
if os.path.exists(LOG_FILE_PATH):
    os.remove(LOG_FILE_PATH)

# 3) Start GUI loop
app.mainloop()
