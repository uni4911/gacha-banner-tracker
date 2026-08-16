# Gacha Banner Tracker - Web GUI

Modern, simple, and responsive GUI for tracking active gacha banners across games (Genshin Impact, Honkai: Star Rail). Built with **React**, **TypeScript**, and **Vite**.

## Features

- 🎮 **Game Selector**: Click on a game (e.g. *Genshin Impact* or *Honkai: Star Rail*) to instantly fetch and display only its currently active banners.
- 🖼️ **Graphic Placeholder Slots**: Clean, styled placeholder slots for 16:9 banner artwork and character splash avatars.
- ⭐ **5★ Spotlight & 4★ Rate-Up Lineups**: Clear visual hierarchy highlighting featured limited characters and 4★ rate-up characters.
- ⏱️ **Real-Time Countdown & Duration**: Live calculation of remaining banner days/hours and formatted start/end dates.
- 🌐 **Region Filter**: Filter active banners by server region (All, Asia, Europe, America).
- ⚡ **Lightweight & Fast**: Built with React + TypeScript and vanilla CSS for smooth performance.

## Running the Application

### 1. Start the Backend API (FastAPI)
From the project root:
```bash
# Activate your venv if needed
.\.venv\Scripts\activate

# Run Uvicorn server on port 8000
uvicorn src.api.app:app --reload --port 8000
```

### 2. Start the Frontend (Vite)
In a new terminal window:
```bash
cd frontend
npm run dev
```
Open `http://localhost:5173` in your browser.
