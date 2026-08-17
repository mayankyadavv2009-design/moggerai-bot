# ⚡ RESONANCE APEX — The Ultimate Discord Audio Engine & Club DJ Bot

**RESONANCE APEX** is a next-generation high-fidelity Discord Music Bot and Club DJ platform engineered with interactive Discord UI component dashboards, 15+ real-time FFmpeg DSP audio filters (8D Spatial Surround, Bassboost 1-3, Nightcore, Vaporwave, Reverb, Vocal Remover), SQLite playlist vaults, instant soundboard audio drops, AI Autoplay recommendations, and an integrated Web Remote Controller.

---

## 🌟 Key Features & Capabilities

- 🎛️ **Interactive Discord Control Dashboard**: Live-updating message embed with ASCII audio spectrum equalizer animation, progress bar, track metadata, and one-click Discord UI Buttons (`Play/Pause`, `Skip`, `Previous`, `Shuffle`, `Loop`, `Audio FX`, `Queue`, `Volume`, `Stop`).
- 🔊 **Master Club DJ Engine (Pro DSP Audio Filters)**:
  - **8D Surround** (360° Rotating Spatial Audio)
  - **Bassboost** (Low, Med, High, Extreme Sub-Woofer)
  - **Nightcore** / **Vaporwave**
  - **Reverb** (Room, Concert Hall, Arena)
  - **Karaoke** (Center Vocal Isolation Filter)
  - **Lowpass / Highpass / Vibrato / Tremolo / Flanger**
- 🎧 **Club DJ Controls**: 24/7 stay-in-voice mode, DJ role assignment, vote-skipping, and autoplay recommendation engine.
- 📂 **SQLite Playlist Vault**: Save active queues as custom playlists, load, share, and manage them anytime.
- 🔊 **Instant Soundboard FX**: Trigger live DJ audio drops (`airhorn`, `scratch`, `bassdrop`, `applause`, `rewind`) over active playback.
- 📜 **Synced Lyrics Engine**: Real-time lyrics fetcher powered by LrcLib.
- 🌐 **Web Remote Controller**: Integrated Flask web dashboard accessible from any desktop/mobile browser at `http://localhost:5000`.

---

## 🚀 Quick Setup & Installation Guide

### Step 1: Get Your Discord Bot Token
1. Open the [Discord Developer Portal](https://discord.com/developers/applications).
2. Click **New Application**, name your bot (e.g. `Resonance Apex`), and click **Create**.
3. In the left sidebar, click **Bot**:
   - Click **Reset Token** and copy your **Bot Token**.
   - Under **Privileged Gateway Intents**, enable:
     - ✅ **Message Content Intent**
     - ✅ **Server Members Intent** (Optional)
4. In the left sidebar, click **OAuth2 -> URL Generator**:
   - Under **Scopes**, check `bot` and `applications.commands`.
   - Under **Bot Permissions**, check:
     - `Connect`, `Speak`, `Use Voice Activity`, `Send Messages`, `Embed Links`, `Attach Files`, `Read Message History`, `Use External Emojis`.
   - Copy the generated URL and paste it in your browser to invite the bot to your Discord server!

### Step 2: Configure Your Token
1. Open the file `.env` inside `C:\Users\mayan\.gemini\antigravity\scratch\resonance_dj_bot\.env`.
2. Replace `YOUR_DISCORD_BOT_TOKEN_HERE` with your copied Bot Token:
   ```env
   DISCORD_TOKEN=your_actual_token_here
   DEFAULT_PREFIX=!
   WEB_PORT=5000
   ```

### Step 3: Launch the Bot
Simply double-click **`launch_resonance.bat`** or execute in terminal:
```bash
python main.py
```

---

## 🎮 Command Manual

### 🎵 Music & AI Recommendation Commands
| Command | Description |
|---|---|
| `/live` (or `/join`) | Join your voice channel and stream your YouTube Live Broadcast directly |
| `/play query:<str>` | Play song title, YouTube URL, Spotify link, or playlist |
| `/radio query:<str>` | Generate an instant 10-track Spotify-style Radio Mix for any artist/song |
| `/taste [user:<Member>]` | Display your music taste profile, top artists, and listening stats |
| `/nowplaying` | Display live dynamic dashboard embed with buttons |
| `/queue` | View current queue list |
| `/clear` | Clear all pending tracks in queue |

### 🎛️ DSP Audio Equalizers
| Command | Description |
|---|---|
| `/filter preset:<name>` | Toggle FFmpeg DSP Audio Filter (`8d`, `bassboost_extreme`, `nightcore`, `vaporwave`, `reverb_arena`, `karaoke`, `lowpass`) |

### 🎧 DJ & Autoplay Commands
| Command | Description |
|---|---|
| `/dj_autoplay enabled:<bool> [mode:<str>]` | Configure Spotify-style Autoplay (`smart`, `transition`, `taste`, `radio`) |
| `/dj_setrole role:<Role>` | Assign server DJ role |
| `/dj_247 enabled:<bool>` | Toggle 24/7 stay-in-voice mode |
| `/voteskip` | Vote skip current song (50% listener threshold) |
| `/status url:<str> title:<str>` | View or dynamically change bot's live streaming status & YouTube link |

### 📂 Custom Playlist Vault & AI Mixes
| Command | Description |
|---|---|
| `/playlist mix_for_me [name:<str>]` | Generate and save a personalized 15-track Spotify Daily Mix from your taste profile |
| `/playlist radio_seed query:<str> name:<str>` | Generate a 10-track radio mix and save it directly into your vault |
| `/playlist save name:<str>` | Save current queue to database |
| `/playlist load name:<str>` | Load saved playlist into queue |
| `/playlist list` | List all your saved playlists |
| `/playlist delete name:<str>` | Remove playlist from vault |

### 🔊 Instant Soundboard
| Command | Description |
|---|---|
| `/soundboard effect:<name>` | Trigger audio drops (`airhorn`, `scratch`, `bassdrop`, `applause`, `rewind`) |

---

## 🌐 Web Remote Controller Interface
While the bot is running, navigate to `http://localhost:5000` in your web browser to control playback, search tracks, and adjust equalizers visually!
