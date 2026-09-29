# DeskPilot

DeskPilot is a Windows desktop assistant for natural-language local computer
automation.

## Current capabilities

- Open and close applications
- Open files and folders using natural-language names
- Search files and folders with fuzzy filename matching
- Search by file extension
- Find latest files and files modified today/yesterday
- Show, minimize, maximize, restore, and switch visible windows
- Open supported websites and search in the browser
- Dedicated Recycle Bin open/count/empty/close support
- Local system diagnostics for common development tools
- Screenshot support using the existing Windows screenshot path

## Safety

- File deletion is intentionally **not** exposed as a DeskPilot tool.
- The Recycle Bin implementation is kept separate from normal file search.
- Do not commit or share the `.env` file. Keep your `GROQ_API_KEY` private.

## Setup

Install the Python dependencies:

```bash
pip install -r requirements.txt
```

Make sure `.env` contains your `GROQ_API_KEY`.

Run:

```bash
python main.py
```

DeskPilot is intended to run on Windows.
