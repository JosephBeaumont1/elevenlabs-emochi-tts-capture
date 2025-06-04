README – Setup Instructions for OCR + TTS Project

version 0.1.0 beta
demo video- https://youtu.be/DxZfeW8K4n4

───────────────────────────────────────────────────────────────────────────────
THIS IS A WIP VERSION AND IS EXTREMLY BUGGY IT MAY CRASH OR NOT WORK FOR BEST OUTCOME FOLLOW INSTRUCTIONS

SYSTEM REQUIREMENTS
─────────────────────
• Windows 10/11 (or macOS/Linux)
• Python 3.7 or newer
• Google Chrome browser installed
• Tesseract OCR engine installed and on your PATH
• ffmpeg installed and on your PATH

FILES INCLUDED
─────────────────
• grab_emochi_chat.py
• apiINFO.txt (contains ElevenLabs API key + voice list)
• README.txt (this document)

PREREQUISITE SOFTWARE & LIBRARIES
─────────────────────────────────────
You need to install several Python packages plus two external tools (Tesseract OCR and ffmpeg). Follow these steps:

A) Install Python 3.7+

Go to https://www.python.org/downloads/

Download and run the Windows installer (choose “Add Python to PATH”).

Verify by opening Command Prompt and typing:
python --version

B) Install Python packages (using pip)

Open a Command Prompt (cmd).

Run the following command to install all required packages at once:
pip install customtkinter Pillow pytesseract opencv-python numpy requests simpleaudio pydub pygetwindow

C) Install Tesseract OCR engine
• Windows:
1. Download the “Tesseract installer for Windows” from
https://github.com/tesseract-ocr/tesseract/releases
2. Run the installer. During installation, choose “Add Tesseract to PATH”.
3. Verify by opening Command Prompt and typing:
tesseract --version
• macOS (Homebrew):
brew install tesseract
• Ubuntu/Debian Linux:
sudo apt-get update
sudo apt-get install tesseract-ocr python3-tk

D) Install ffmpeg (for pydub audio decoding)
• Windows:
1. Download a static build of ffmpeg from https://ffmpeg.org/download.html
2. Unzip to a folder (e.g. C:\ffmpeg).
3. Add C:\ffmpeg\bin to your PATH environment variable (System → Advanced → Environment Variables).
4. Verify by opening Command Prompt and typing:
ffmpeg -version
• macOS (Homebrew):
brew install ffmpeg
• Ubuntu/Debian Linux:
sudo apt-get update
sudo apt-get install ffmpeg

SET UP ElevenLabs API INFORMATION
─────────────────────────────────────────

Open apiINFO.txt in a plain text editor (Notepad, TextEdit, VS Code, etc.).

The first line must be your ElevenLabs API key (the long alphanumeric string you get from https://elevenlabs.io/).

Each subsequent line defines one custom voice in the format:
FriendlyVoiceName,VoiceID
Example:
3beef47a...a1,VoiceID_of_Alice
BobVoice,xyz123abc...

Save and close apiINFO.txt.

VERIFY Python ENVIRONMENT
─────────────────────────────────
In Command Prompt or Terminal, run:
pip --version
python --version
tesseract --version
ffmpeg -version
Each should return a version number; if any command is not found, revisit the installation steps above.

RUN THE SCRIPT
──────────────────

Place grab_emochi_chat.py and apiINFO.txt in the same folder.

Open Command Prompt and navigate to that folder, for example:
cd "C:\Path\To\Folder"

Run:
python grab_emochi_chat.py

A GUI window titled “OCR Control Panel” will appear on top of your screen. It includes:
• Dropdown menus to select your “First-Person Voice” and “Narrator Voice” (from the voices listed in apiINFO.txt).
• Buttons:
– Start Reading → begins live OCR and text-to-speech.
– Stop Reading → pauses OCR/TTS (audio in progress will also stop).
– Quit → closes the GUI and prints the capture_log.txt (if it exists).

HOW IT WORKS (AT A GLANCE)
──────────────────────────────────
• When you launch, the script automatically opens a new Chrome window loading https://emochi.com/.
• Click Start Reading to begin capturing the Chrome window’s visible content every 2 seconds.
• Each newly detected line of text is appended to captured_screen_text.txt and read aloud using ElevenLabs TTS.
– Lines containing quotation marks (“…”) use the “First-Person Voice” with the prefix “I said: …”.
– All other lines use the “Narrator Voice” verbatim.
• Click Stop Reading to pause capturing and stop any currently playing audio.
• Click Quit to close the GUI. If a capture_log.txt exists, its contents will be printed to the console.

TROUBLESHOOTING
─────────────────────
• “tesseract not found” error – Tesseract is not on PATH. Reinstall or add its installation folder (e.g. C:\Program Files\Tesseract-OCR) to PATH.
• “ffmpeg required” warnings – Install ffmpeg and add ffmpeg/bin to PATH.
• No audio plays or strange audio errors – Confirm pydub and simpleaudio are installed. Verify pip show pydub simpleaudio returns info. Also check ffmpeg is working.
• No voices listed in dropdowns – Check apiINFO.txt. The very first line must be your API key; lines below must contain a comma.
• Chrome window not found – Make sure Chrome is running and not minimized. The script highlights whichever visible Chrome window it finds.
• Permission issues on Windows – If “Access denied” appears, try running Command Prompt as Administrator.

FILES GENERATED AT RUNTIME
──────────────────────────────────
• captured_screen_text.txt – every detected line of on-screen text (appended).
• capture_log.txt – timestamped log of all detected lines (rewritten each run).

───────────────────────────────────────────────────────────────────────────────
Thank you for using this OCR + TTS tool. Follow these steps, and you should be up and running in under 15 minutes. If any step fails, revisit the corresponding section above.







