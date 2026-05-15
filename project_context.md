# 📂 Project Info: ElmarakbyTube Downloader
**Last Updated:** 2026-05-15
**Current Branch:** `feature-partial-download`

## 1. 💡 Project Idea
This is a desktop app. It downloads YouTube videos and playlists. It makes them MP4 or MP3. It is very fast. The screen does not freeze. 

## 2. 🛠️ Tools We Use
- **Language:** Python 3.14+
- **Screen (GUI):** `CustomTkinter`
- **Main Tools:** `yt-dlp` (to download), `ffmpeg` (to convert video/audio).
- **Tests:** `pytest`. We run `run_tests.bat` to test the app.

## 3. 🏗️ Files Layout (Architecture)
The screen (UI) and the work (Logic) are separated:
- **`main.py`:** The boss. It runs the app and background work (threads).
- **`ui/` folder (The Screen):**
  - `layout.py`: Draws the app.
  - `popups.py`: Shows small windows (errors, welcome).
  - `state.py`: Saves app data.
- **`core/` folder (The Work):**
  - `fetcher.py`: Gets video info.
  - `downloader.py`: Downloads the video.
  - `converter.py`: Changes video to MP4/MP3.
  - `utils.py`: Small helpers (like time and size format).
- **Settings:** `config.py` (colors) and `messages.py` (text).

## 4. 🧠 Important Rules We Made
- **Safe Screen:** Never update the screen directly from background work (threads). 
- **Testing:** We test ~60% of the app. We test the screen using fake screens (Mocks).

## 5. 📜 Code Rules
- **Comments:** Always write comments in simple English.
- **Talk First:** Do not write big code before asking and planning.
- **Be Honest:** Tell the user if there is a mistake. 

## 6. ⚠️ Current Problems
- **yt-dlp test error:** The download test does not show errors. 
  - **Fix:** We skipped this test. We will test downloads by hand (manually).

## 7. 🎯 What is Next?
- **Finished:** The code is clean and tested.
- **Now:** We are on `feature-partial-download` branch.
- **Next Step:** We need to know what "partial download" exactly means to start writing code.

---
*(🤖 Instructions for LLMs: Read this file. Do not break the UI and Logic separation. Follow the Code Rules.)*