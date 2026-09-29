## Preview
<img width="1366" height="728" alt="image" src="https://github.com/user-attachments/assets/ff3c4206-f554-478e-a48f-6721ec1a36d7" />


## Added Windows controls

- Show currently open windows
- Minimize/maximize/restore/activate a specific window
- Minimize all windows
- Restore all windows
- Take a full desktop screenshot
- Open direct HTTP/HTTPS URLs

File deletion is intentionally not exposed as a DeskPilot tool to reduce accidental data loss.
\n## Screenshot\n\nScreenshots use the Windows virtual desktop APIs directly and do not require Pillow.\nEOF
rm -f /tmp/DeskPilot_screenshot_fixed_no_pillow.zip
cd /tmp/dpfix && zip -qr /tmp/DeskPilot_screenshot_fixed_no_pillow.zip . -x '*.pyc' '*__pycache__*' '*.env'
unzip -t /tmp/DeskPilot_screenshot_fixed_no_pillow.zip | tail -2
ls -lh /tmp/DeskPilot_screenshot_fixed_no_pillow.zip
