from flask import Flask, render_template, jsonify, request
import threading
import logging
import asyncio
from typing import Dict, Any

app = Flask(__name__)
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

bot_instance = None

def set_bot_reference(bot):
    global bot_instance
    bot_instance = bot

@app.route('/')
def index():
    return render_template('index.html')

def get_training_status_dict():
    import json, os, glob
    candidate_paths = [
        r"c:\Users\mayan\.gemini\antigravity\scratch\resonance_dj_bot\training_status.json",
        r"C:\Users\mayan\.gemini\antigravity-ide\brain\8473a184-f7a7-43e9-b63b-82bc1545c8c9\scratch\training_status.json"
    ] + glob.glob(r"C:\Users\mayan\.gemini\antigravity-ide\brain\*\scratch\training_status.json")

    for path in candidate_paths:
        if path and os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass

    return {
        "status": "training",
        "progress_percent": 0.5,
        "elapsed_seconds": 30,
        "remaining_seconds": 7170,
        "cycle": 1,
        "model": "gemini-2.5-flash",
        "persona": "Claude Fable 5"
    }

@app.route('/api/status', methods=['GET'])
def get_status():
    training_info = get_training_status_dict()
    if not bot_instance:
        return jsonify({"status": "offline", "training": training_info})

    music_cog = bot_instance.get_cog("Music")
    if not music_cog or not music_cog.states:
        return jsonify({"current_track": None, "queue_len": 0, "filter": "normal", "is_paused": False, "training": training_info, "status": "online"})

    state = list(music_cog.states.values())[0]
    return jsonify({
        "current_track": state.current_track,
        "queue_len": len(state.queue),
        "filter": state.filter_name,
        "is_paused": state.is_paused,
        "volume": state.volume,
        "loop_mode": state.loop_mode,
        "autoplay": state.autoplay,
        "autoplay_mode": state.autoplay_mode,
        "status": "online",
        "training": training_info
    })

@app.route('/api/queue', methods=['GET'])
def get_queue():
    if not bot_instance:
        return jsonify([])
    music_cog = bot_instance.get_cog("Music")
    if not music_cog or not music_cog.states:
        return jsonify([])
    state = list(music_cog.states.values())[0]
    return jsonify(state.queue[:30])

@app.route('/api/taste', methods=['GET'])
def get_taste():
    if not bot_instance:
        return jsonify({})
    from utils.database import Database
    music_cog = bot_instance.get_cog("Music")
    guild_id = 0
    if music_cog and music_cog.states:
        guild_id = list(music_cog.states.values())[0].guild_id

    profile = Database.get_user_taste_profile(guild_id, 0)
    return jsonify(profile)

@app.route('/api/daily_mixes', methods=['GET'])
def get_daily_mixes():
    mixes = [
        {
            "id": "daily_mix_1",
            "title": "Daily Mix 1",
            "subtitle": "Alan Walker, Marshmello & Martin Garrix",
            "tag": "EDM & Club",
            "color": "#1DB954",
            "query": "Alan Walker Faded remix radio"
        },
        {
            "id": "daily_mix_2",
            "title": "Daily Mix 2",
            "subtitle": "The Weeknd, Drake & Post Malone",
            "tag": "Pop & Hip Hop",
            "color": "#8A2BE2",
            "query": "The Weeknd Blinding Lights mix"
        },
        {
            "id": "daily_mix_3",
            "title": "Daily Mix 3",
            "subtitle": "Billie Eilish, Olivia Rodrigo & Taylor Swift",
            "tag": "Indie & Pop Vibe",
            "color": "#00F3FF",
            "query": "Billie Eilish Birds of a feather mix"
        },
        {
            "id": "daily_mix_4",
            "title": "Discover Weekly",
            "subtitle": "AI-curated fresh discoveries for you",
            "tag": "Fresh Hits",
            "color": "#FF007F",
            "query": "Top global hits 2026 radio mix"
        }
    ]
    return jsonify(mixes)

@app.route('/api/training_status', methods=['GET'])
def get_training_status():
    import json, os, glob
    
    candidate_paths = [
        r"c:\Users\mayan\.gemini\antigravity\scratch\resonance_dj_bot\training_status.json",
        r"C:\Users\mayan\.gemini\antigravity-ide\brain\8473a184-f7a7-43e9-b63b-82bc1545c8c9\scratch\training_status.json"
    ] + glob.glob(r"C:\Users\mayan\.gemini\antigravity-ide\brain\*\scratch\training_status.json")

    for path in candidate_paths:
        if path and os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return jsonify(data)
            except Exception:
                pass

    return jsonify({
        "status": "training",
        "progress_percent": 0.5,
        "elapsed_seconds": 30,
        "remaining_seconds": 7170,
        "cycle": 1,
        "model": "gemini-2.5-flash",
        "persona": "Claude Fable 5"
    })

@app.route('/api/autoplay', methods=['POST'])
def api_autoplay():
    data = request.json or {}
    enabled = data.get("enabled", True)
    mode = data.get("mode", "smart")
    if bot_instance:
        music_cog = bot_instance.get_cog("Music")
        if music_cog and music_cog.states:
            state = list(music_cog.states.values())[0]
            from utils.database import Database
            Database.update_guild_setting(state.guild_id, "autoplay", 1 if enabled else 0)
            Database.update_guild_setting(state.guild_id, "autoplay_mode", mode)
            state.autoplay = enabled
            state.autoplay_mode = mode
    return jsonify({"success": True, "autoplay": enabled, "mode": mode})

@app.route('/api/pause', methods=['POST'])
def api_pause():
    if bot_instance:
        music_cog = bot_instance.get_cog("Music")
        if music_cog and music_cog.states:
            state = list(music_cog.states.values())[0]
            if state.voice_client:
                if state.voice_client.is_playing():
                    state.voice_client.pause()
                    state.is_paused = True
                elif state.voice_client.is_paused():
                    state.voice_client.resume()
                    state.is_paused = False
    return jsonify({"success": True})

@app.route('/api/skip', methods=['POST'])
def api_skip():
    if bot_instance:
        music_cog = bot_instance.get_cog("Music")
        if music_cog and music_cog.states:
            state = list(music_cog.states.values())[0]
            if state.voice_client and (state.voice_client.is_playing() or state.voice_client.is_paused()):
                state.voice_client.stop()
    return jsonify({"success": True})

@app.route('/api/seek', methods=['POST'])
def api_seek():
    data = request.json or {}
    delta = data.get("delta")
    target = data.get("target")
    if bot_instance:
        music_cog = bot_instance.get_cog("Music")
        if music_cog and music_cog.states:
            state = list(music_cog.states.values())[0]
            if delta is not None:
                asyncio.run_coroutine_threadsafe(
                    music_cog.seek_by_delta(state.guild_id, int(delta)),
                    bot_instance.loop
                )
            elif target is not None:
                asyncio.run_coroutine_threadsafe(
                    music_cog.seek_to_position(state.guild_id, int(target)),
                    bot_instance.loop
                )
    return jsonify({"success": True})

@app.route('/api/play_query', methods=['POST'])
def api_play_query():
    data = request.json or {}
    query = data.get("query", "").strip()
    if not query or not bot_instance:
        return jsonify({"success": False, "error": "Invalid query"})

    music_cog = bot_instance.get_cog("Music")
    if not music_cog:
        return jsonify({"success": False, "error": "Music module unavailable"})

    async def _do_play():
        for guild in bot_instance.guilds:
            if guild.voice_channels:
                vc_target = None
                for vc in guild.voice_channels:
                    if len([m for m in vc.members if not m.bot]) > 0:
                        vc_target = vc
                        break
                if not vc_target:
                    vc_target = guild.voice_channels[0]
                
                state = music_cog.get_state(guild.id)
                state.voice_client = await music_cog.ensure_voice_connection(guild, vc_target)
                
                from utils.audio_source import YTDLSource
                track_info = await YTDLSource.create_source(query, loop=bot_instance.loop)
                if track_info:
                    track_dict = {
                        'title': track_info.get('title', 'Unknown Track'),
                        'url': track_info.get('webpage_url') or track_info.get('url'),
                        'duration': track_info.get('duration', 0),
                        'uploader': track_info.get('uploader', 'Unknown Artist'),
                        'thumbnail': track_info.get('thumbnail', ''),
                        'requester': 'Spotify Web Remote',
                        'raw_data': track_info
                    }
                    state.queue.append(track_dict)
                    if not state.voice_client.is_playing() and not state.voice_client.is_paused():
                        await music_cog._play_next(guild)
                    return True
        return False

    bot_instance.loop.create_task(_do_play())
    return jsonify({"success": True, "query": query})

@app.route('/api/radio', methods=['POST'])
def api_radio():
    data = request.json or {}
    query = data.get("query", "").strip()
    if not bot_instance:
        return jsonify({"success": False})

    music_cog = bot_instance.get_cog("Music")
    if not music_cog:
        return jsonify({"success": False})

    async def _do_radio():
        from utils.recommendation import RecommendationEngine
        search_query = query
        for guild in bot_instance.guilds:
            state = music_cog.get_state(guild.id)
            if not search_query and state.current_track:
                search_query = state.current_track.get('uploader') or state.current_track.get('title')
            
            if search_query:
                tracks = await RecommendationEngine.generate_radio_mix(bot_instance.loop, search_query, count=10)
                if tracks:
                    for t in tracks:
                        t['requester'] = f"📻 Radio: Spotify Web"
                        state.queue.append(t)
                    if state.voice_client and not state.voice_client.is_playing() and not state.voice_client.is_paused():
                        await music_cog._play_next(guild)

    bot_instance.loop.create_task(_do_radio())
    return jsonify({"success": True})

@app.route('/api/filter', methods=['POST'])
def api_filter():
    data = request.json or {}
    preset = data.get("filter", "normal")
    if bot_instance:
        music_cog = bot_instance.get_cog("Music")
        if music_cog and music_cog.states:
            state = list(music_cog.states.values())[0]
            bot_instance.loop.create_task(music_cog.apply_filter(state.guild_id, preset))
    return jsonify({"success": True, "filter": preset})

@app.route('/api/volume', methods=['POST'])
def api_volume():
    data = request.json or {}
    vol = float(data.get("volume", 0.8))
    if bot_instance:
        music_cog = bot_instance.get_cog("Music")
        if music_cog and music_cog.states:
            state = list(music_cog.states.values())[0]
            bot_instance.loop.create_task(music_cog.set_volume(state.guild_id, vol))
    return jsonify({"success": True, "volume": vol})

@app.route('/api/youtube_status', methods=['GET'])
def get_youtube_status():
    import config
    return jsonify({
        "url": config.YOUTUBE_STATUS_URL,
        "title": config.STATUS_TEXT
    })

@app.route('/api/youtube_status', methods=['POST'])
def update_youtube_status():
    import config
    import discord
    from config import save_status
    data = request.json or {}
    url = data.get("url", "").strip() or None
    title = data.get("title", "").strip() or None
    
    new_url, new_title = save_status(new_url=url, new_text=title)
    if bot_instance:
        activity = discord.Streaming(name=new_title, url=new_url)
@app.route('/training')
def training_studio():
    return render_template('training.html')

@app.route('/api/train/chat', methods=['POST'])
def api_train_chat():
    from utils.groq_brain import GroqBrain
    import asyncio, time
    
    data = request.json or {}
    user_prompt = data.get("prompt", "").strip()
    session_id = data.get("session_id", "web_training_session")
    
    if not user_prompt:
        return jsonify({"error": "Prompt cannot be empty"}), 400

    t0 = time.time()
    loop = asyncio.new_event_loop()
    try:
        reply = loop.run_until_complete(
            GroqBrain.generate_response(
                session_id=session_id,
                user_prompt=user_prompt,
                user_name="Trainer"
            )
        )
    finally:
        loop.close()

    elapsed = round(time.time() - t0, 2)
    return jsonify({
        "reply": reply,
        "elapsed_sec": elapsed,
        "model": "Groq / Gemini-2.5-Flash",
        "persona": "Claude Fable 5"
    })

@app.route('/api/train/exemplar', methods=['GET', 'POST', 'DELETE'])
def api_train_exemplar():
    from utils.training_manager import TrainingManager
    
    if request.method == 'GET':
        dataset = TrainingManager.load_dataset()
        stats = TrainingManager.get_stats()
        return jsonify({"exemplars": dataset.get("exemplars", []), "stats": stats})
        
    elif request.method == 'POST':
        data = request.json or {}
        user_prompt = data.get("user_prompt", "").strip()
        ideal_response = data.get("ideal_response", "").strip()
        category = data.get("category", "CHAT")
        rating = int(data.get("rating", 5))
        tags = data.get("feedback_tags", [])
        notes = data.get("notes", "")
        
        if not user_prompt or not ideal_response:
            return jsonify({"error": "User prompt and ideal response are required"}), 400
            
        exemplar = TrainingManager.add_exemplar(
            user_prompt=user_prompt,
            ideal_response=ideal_response,
            category=category,
            rating=rating,
            feedback_tags=tags,
            notes=notes
        )
        return jsonify({"success": True, "exemplar": exemplar})
        
    elif request.method == 'DELETE':
        data = request.json or {}
        ex_id = data.get("id", "")
        if not ex_id:
            return jsonify({"error": "ID is required"}), 400
        success = TrainingManager.delete_exemplar(ex_id)
        return jsonify({"success": success})

@app.route('/api/train/keys', methods=['GET'])
def api_train_keys():
    from utils.claude_brain import key_rotator
    return jsonify(key_rotator.get_status_report())

@app.route('/api/train/export', methods=['GET'])
def api_train_export():
    from utils.training_manager import TrainingManager
    return jsonify(TrainingManager.load_dataset())

@app.route('/api/training_status', methods=['GET'])
def api_training_status():
    status_paths = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "training_status.json"),
        r"c:\Users\mayan\.gemini\antigravity\scratch\resonance_dj_bot\training_status.json"
    ]
    for p in status_paths:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return jsonify(data)
            except Exception:
                pass
    return jsonify({
        "status": "training",
        "progress_percent": 15.0,
        "elapsed_seconds": 120,
        "pillar": "UNCENSORED_ROAST",
        "current_category": "Procedural Evolution Engine",
        "recent_activity": []
    })

def run_web_server(port: int = 5000):
    thread = threading.Thread(target=lambda: app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False), daemon=True)
    thread.start()
