import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import time
import random
from typing import Dict, List, Optional, Any
from utils.audio_source import YTDLSource
from utils.UI_components import build_now_playing_embed, MusicControlView
from utils.database import Database
from utils.recommendation import RecommendationEngine
from config import DEFAULT_VOLUME, EMBED_COLOR_MAIN, EMBED_COLOR_ERROR, EMBED_COLOR_DJ, BOT_NAME


def parse_time_str(time_input: str) -> Optional[int]:
    """Parse time string like '90', '1:30', or '01:15:30' into integer seconds"""
    if not time_input:
        return None
    time_input = str(time_input).strip()
    if ":" in time_input:
        parts = time_input.split(":")
        try:
            if len(parts) == 2:
                return int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        except ValueError:
            return None
    try:
        return int(float(time_input))
    except ValueError:
        return None


class GuildAudioState:
    def __init__(self, guild_id: int):
        self.guild_id = guild_id
        self.voice_client: Optional[discord.VoiceClient] = None
        self.queue: List[Dict[str, Any]] = []
        self.history: List[Dict[str, Any]] = []
        self.recent_history_urls: List[str] = []
        self.current_track: Optional[Dict[str, Any]] = None
        self.current_source: Optional[YTDLSource] = None
        
        # Real-time Listener Attendance & Active Listening Tracking
        self.listener_sessions: Dict[int, Dict[str, Any]] = {}
        
        # Zero-gap Autoplay pre-buffering
        self.prefetched_autoplay_track: Optional[Dict[str, Any]] = None
        self.is_prefetching: bool = False
        self.is_seeking: bool = False

        self.loop_mode: str = "off"  # "off", "track", "queue"
        self.volume: float = Database.get_guild_setting(guild_id, "volume", DEFAULT_VOLUME)
        self.filter_name: str = Database.get_guild_setting(guild_id, "active_filter", "normal")
        self.autoplay: bool = bool(Database.get_guild_setting(guild_id, "autoplay", 1))
        self.autoplay_mode: str = Database.get_guild_setting(guild_id, "autoplay_mode", "smart")
        self.stay_247: bool = bool(Database.get_guild_setting(guild_id, "stay_247", 0))

        self.dashboard_message: Optional[discord.Message] = None
        self.start_time: float = 0.0
        self.pause_start: float = 0.0
        self.total_paused_duration: float = 0.0
        self.is_paused: bool = False
        self.is_processing: bool = False


class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.states: Dict[int, GuildAudioState] = {}

    def get_state(self, guild_id: int) -> GuildAudioState:
        if guild_id not in self.states:
            self.states[guild_id] = GuildAudioState(guild_id)
        return self.states[guild_id]

    def cog_load(self):
        self.dashboard_updater.start()

    def cog_unload(self):
        self.dashboard_updater.cancel()

    async def ensure_voice_connection(self, guild: discord.Guild, voice_channel: discord.VoiceChannel) -> discord.VoiceClient:
        state = self.get_state(guild.id)
        
        # Already connected to the right channel
        if state.voice_client and state.voice_client.is_connected():
            if state.voice_client.channel != voice_channel:
                await state.voice_client.move_to(voice_channel)
            return state.voice_client

        # Clean up stale connection references
        if state.voice_client:
            try:
                await state.voice_client.disconnect(force=True)
            except Exception:
                pass
            state.voice_client = None

        if guild.voice_client:
            try:
                await guild.voice_client.disconnect(force=True)
            except Exception:
                pass

        # Resilient retry connection loop
        last_err = None
        for attempt in range(1, 4):
            try:
                voice_client = await voice_channel.connect(timeout=20.0, reconnect=True, self_deaf=True)
                state.voice_client = voice_client
                return voice_client
            except Exception as e:
                last_err = e
                print(f"[VOICE CONNECT ATTEMPT {attempt}/3] {e}")
                await asyncio.sleep(1.2)

        raise RuntimeError(f"Failed to connect to voice channel: {last_err}")

    # ------------------- Real-time Attendance & Dashboard Updater -------------------
    @tasks.loop(seconds=3.0)
    async def dashboard_updater(self):
        now = time.time()
        for guild_id, state in list(self.states.items()):
            if not state.voice_client or not state.voice_client.is_connected():
                continue

            # Real-Time Listener Attendance & Listening Time Tracking
            if state.voice_client.is_playing() and not state.is_paused and state.voice_client.channel:
                for member in state.voice_client.channel.members:
                    if member.bot:
                        continue
                    # Exclude deafened users (they are not actively listening)
                    if member.voice and (member.voice.self_deaf or member.voice.deaf):
                        continue

                    if member.id not in state.listener_sessions:
                        state.listener_sessions[member.id] = {
                            'user_name': member.display_name,
                            'seconds_listened': 0,
                            'last_tick': now
                        }
                    else:
                        dt = int(now - state.listener_sessions[member.id].get('last_tick', now))
                        if 0 < dt <= 8:
                            state.listener_sessions[member.id]['seconds_listened'] += dt
                        state.listener_sessions[member.id]['last_tick'] = now

            # Dynamic Dashboard Embed Updates
            if state.dashboard_message and state.current_track and state.voice_client.is_playing():
                try:
                    elapsed = self._get_elapsed_time(state)
                    embed = build_now_playing_embed(
                        track=state.current_track,
                        current_sec=elapsed,
                        loop_mode=state.loop_mode,
                        filter_name=state.filter_name,
                        is_paused=state.is_paused,
                        queue_len=len(state.queue),
                        volume=state.volume
                    )
                    await state.dashboard_message.edit(embed=embed)
                except discord.NotFound:
                    state.dashboard_message = None
                except Exception:
                    pass

    @dashboard_updater.before_loop
    async def before_dashboard_updater(self):
        try:
            await self.bot.wait_until_ready()
        except Exception:
            pass

    def _get_elapsed_time(self, state: GuildAudioState) -> int:
        if not state.start_time:
            return 0
        if state.is_paused:
            return int(state.pause_start - state.start_time - state.total_paused_duration)
        return max(0, int(time.time() - state.start_time - state.total_paused_duration))

    def _flush_listener_sessions(self, state: GuildAudioState, track: Optional[Dict[str, Any]]):
        """Flushes exact accumulated listened seconds for every real person in the voice channel to SQLite"""
        if not track or not state.listener_sessions:
            state.listener_sessions.clear()
            return
        
        for user_id, session in list(state.listener_sessions.items()):
            sec = session.get('seconds_listened', 0)
            if sec >= 5: # At least 5 real seconds listened
                Database.record_real_listen(
                    guild_id=state.guild_id,
                    user_id=user_id,
                    user_name=session.get('user_name', 'Listener'),
                    title=track.get('title', 'Unknown Track'),
                    artist=track.get('uploader', 'Unknown Artist'),
                    url=track.get('webpage_url') or track.get('url', ''),
                    duration_sec=sec,
                    thumbnail=track.get('thumbnail', '')
                )
        state.listener_sessions.clear()

    # ------------------- Voice State Listener (Real-Time Leave / Deafen Tracking) -------------------
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.bot or not member.guild:
            return
        state = self.get_state(member.guild.id)
        if not state.voice_client or not state.voice_client.channel:
            return

        bot_channel = state.voice_client.channel
        left_channel = (before.channel == bot_channel and after.channel != bot_channel)
        deafened = (not before.self_deaf and after.self_deaf) or (not before.deaf and after.deaf)

        if (left_channel or deafened) and member.id in state.listener_sessions and state.current_track:
            session = state.listener_sessions.pop(member.id, None)
            if session:
                sec = session.get('seconds_listened', 0)
                if sec >= 5:
                    Database.record_real_listen(
                        guild_id=state.guild_id,
                        user_id=member.id,
                        user_name=session.get('user_name', member.display_name),
                        title=state.current_track.get('title', 'Unknown Track'),
                        artist=state.current_track.get('uploader', 'Unknown Artist'),
                        url=state.current_track.get('webpage_url') or state.current_track.get('url', ''),
                        duration_sec=sec,
                        thumbnail=state.current_track.get('thumbnail', '')
                    )

    # ------------------- Zero-Gap Autoplay Pre-Buffering -------------------
    async def _prefetch_autoplay(self, state: GuildAudioState):
        if state.is_prefetching or not state.autoplay or not state.current_track:
            return
        state.is_prefetching = True
        try:
            track = await self._fetch_autoplay_recommendation(state, state.current_track)
            if track:
                if not track.get('raw_data') or not track.get('raw_data', {}).get('url'):
                    track_data = await YTDLSource.create_source(track['url'], loop=self.bot.loop, volume=state.volume, filter_name=state.filter_name)
                    if track_data:
                        track['raw_data'] = track_data
                state.prefetched_autoplay_track = track
        except Exception as e:
            print(f"[PREFETCH ERROR] {e}")
        finally:
            state.is_prefetching = False

    # ------------------- Core Playback Engine -------------------
    async def _play_next(self, guild: discord.Guild):
        state = self.get_state(guild.id)
        if state.is_processing:
            return

        state.is_processing = True
        try:
            if not state.voice_client or not state.voice_client.is_connected():
                state.is_processing = False
                return

            # Flush previous track's real listened seconds for all active room members
            if state.current_track:
                self._flush_listener_sessions(state, state.current_track)

            # Handle Loop Modes
            if state.loop_mode == "track" and state.current_track:
                next_track = state.current_track
            elif not state.queue:
                if state.loop_mode == "queue" and state.history:
                    state.queue = list(state.history)
                    state.history.clear()
                    next_track = state.queue.pop(0)
                elif state.autoplay and state.current_track:
                    if state.prefetched_autoplay_track:
                        next_track = state.prefetched_autoplay_track
                        state.prefetched_autoplay_track = None
                    else:
                        next_track = await self._fetch_autoplay_recommendation(state, state.current_track)

                    if not next_track:
                        state.current_track = None
                        state.current_source = None
                        state.is_processing = False
                        return
                else:
                    state.current_track = None
                    state.current_source = None
                    state.is_processing = False
                    if not state.stay_247:
                        await asyncio.sleep(60) # Inactivity disconnect
                        if not state.queue and state.voice_client and not state.voice_client.is_playing():
                            await state.voice_client.disconnect()
                            state.voice_client = None
                    return
            else:
                if state.current_track:
                    state.history.append(state.current_track)
                next_track = state.queue.pop(0)

            # Record song transition (Markov graph)
            if state.current_track and state.current_track != next_track:
                Database.record_transition(guild.id, state.current_track, next_track)

            state.current_track = next_track

            # Update recent history sliding window (to prevent repetition)
            url_to_add = next_track.get('webpage_url') or next_track.get('url')
            if url_to_add:
                if url_to_add in state.recent_history_urls:
                    state.recent_history_urls.remove(url_to_add)
                state.recent_history_urls.append(url_to_add)
                if len(state.recent_history_urls) > 30:
                    state.recent_history_urls.pop(0)

            # Check if we have pre-extracted raw data or need fresh stream URL
            track_data = next_track.get('raw_data')
            if not track_data or not track_data.get('url'):
                track_data = await YTDLSource.create_source(
                    next_track['url'],
                    loop=self.bot.loop,
                    volume=state.volume,
                    filter_name=state.filter_name
                )

            if not track_data or not track_data.get('url'):
                channel = next_track.get('text_channel')
                if channel:
                    await channel.send(f"⚠️ Stream unavailable for `{next_track.get('title', 'track')}`. Skipping smoothly to next...")
                state.is_processing = False
                await self._play_next(guild)
                return

            if 'title' not in track_data or track_data['title'] == 'Unknown Title':
                track_data['title'] = next_track.get('title', 'Audio Track')
            track_data['requester'] = next_track.get('requester', 'DJ')

            source = YTDLSource.build_ffmpeg_source(track_data, volume=state.volume, filter_name=state.filter_name)
            state.current_source = source
            state.start_time = time.time()
            state.total_paused_duration = 0.0
            state.is_paused = False

            # Initialize active listening sessions for all current voice channel members
            if state.voice_client.channel:
                now = time.time()
                for member in state.voice_client.channel.members:
                    if not member.bot and (not member.voice or (not member.voice.self_deaf and not member.voice.deaf)):
                        state.listener_sessions[member.id] = {
                            'user_name': member.display_name,
                            'seconds_listened': 0,
                            'last_tick': now
                        }

            def after_playing(error):
                if state.is_seeking:
                    return
                if error:
                    print(f"[PLAYBACK ERROR] {error}")
                asyncio.run_coroutine_threadsafe(self._play_next(guild), self.bot.loop)

            state.voice_client.play(source, after=after_playing)

            # Trigger background pre-buffering for the next autoplay track!
            if state.autoplay and not state.queue:
                self.bot.loop.create_task(self._prefetch_autoplay(state))

            # Send / Update Control Dashboard via Live Slide (Seamlessly Edit Existing Message)
            channel = next_track.get('text_channel')
            if channel:
                embed = build_now_playing_embed(
                    track=next_track,
                    current_sec=0,
                    loop_mode=state.loop_mode,
                    filter_name=state.filter_name,
                    is_paused=False,
                    queue_len=len(state.queue),
                    volume=state.volume
                )
                view = MusicControlView(self, guild.id)
                
                # Smooth Slide: Edit existing dashboard message if available
                slid = False
                if state.dashboard_message:
                    try:
                        await state.dashboard_message.edit(embed=embed, view=view)
                        slid = True
                    except (discord.NotFound, discord.HTTPException):
                        state.dashboard_message = None

                if not slid:
                    try:
                        msg = await channel.send(embed=embed, view=view)
                        state.dashboard_message = msg
                    except Exception as me:
                        print(f"[DASHBOARD SEND ERROR] {me}")

        except Exception as e:
            print(f"[ENGINE ERROR] Failed play_next: {e}")
            await asyncio.sleep(1)
            state.is_processing = False
            await self._play_next(guild)
            return

        state.is_processing = False

    async def _fetch_autoplay_recommendation(self, state: GuildAudioState, seed_track: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        active_user_ids = []
        if state.voice_client and state.voice_client.channel:
            active_user_ids = [m.id for m in state.voice_client.channel.members if not m.bot]

        mode = Database.get_guild_setting(state.guild_id, "autoplay_mode", "smart")
        
        return await RecommendationEngine.get_autoplay_track(
            bot_loop=self.bot.loop,
            guild_id=state.guild_id,
            current_track=seed_track,
            active_user_ids=active_user_ids,
            recent_urls=state.recent_history_urls,
            autoplay_mode=mode
        )

    # ------------------- Seeking & Scrubbing Engine -------------------
    async def seek_to_position(self, guild_id: int, target_seconds: int) -> int:
        """Instantly seek current track to target_seconds using FFmpeg stream positioning"""
        state = self.get_state(guild_id)
        if not state.voice_client or not state.current_track:
            return -1

        target_seconds = max(0, int(target_seconds))
        track_data = state.current_track.get('raw_data')
        if not track_data or not track_data.get('url'):
            track_data = await YTDLSource.create_source(
                state.current_track['url'],
                loop=self.bot.loop,
                volume=state.volume,
                filter_name=state.filter_name
            )
            state.current_track['raw_data'] = track_data

        if not track_data or not track_data.get('url'):
            return -1

        source = YTDLSource.build_ffmpeg_source(
            track_data,
            volume=state.volume,
            filter_name=state.filter_name,
            seek_seconds=target_seconds
        )

        state.is_seeking = True
        if state.voice_client.is_playing() or state.voice_client.is_paused():
            state.voice_client.stop()

        await asyncio.sleep(0.06)
        state.current_source = source
        state.start_time = time.time() - target_seconds
        state.total_paused_duration = 0.0
        state.is_paused = False
        state.is_seeking = False

        def after_playing(error):
            if state.is_seeking:
                return
            if error:
                print(f"[PLAYBACK ERROR] {error}")
            guild = self.bot.get_guild(guild_id)
            if guild:
                asyncio.run_coroutine_threadsafe(self._play_next(guild), self.bot.loop)

        state.voice_client.play(source, after=after_playing)
        return target_seconds

    async def seek_by_delta(self, guild_id: int, delta_seconds: int) -> int:
        """Seek forward or backward by delta_seconds (+10s, -10s, etc.)"""
        state = self.get_state(guild_id)
        if not state.voice_client or not state.current_track:
            return -1

        current_elapsed = self._get_elapsed_time(state)
        total_duration = state.current_track.get('duration', 0)
        target_pos = max(0, current_elapsed + delta_seconds)

        if total_duration > 0 and target_pos >= total_duration:
            state.voice_client.stop()
            return total_duration

        return await self.seek_to_position(guild_id, target_pos)

    async def rewind_10s(self, interaction: discord.Interaction):
        state = self.get_state(interaction.guild_id)
        if not state.voice_client or not state.current_track or (not state.voice_client.is_playing() and not state.voice_client.is_paused()):
            return await interaction.response.send_message("❌ Nothing currently playing to rewind.", ephemeral=True)

        new_pos = await self.seek_by_delta(interaction.guild_id, -10)
        if new_pos < 0:
            return await interaction.response.send_message("❌ Failed to rewind audio.", ephemeral=True)

        mins, secs = divmod(new_pos, 60)
        await interaction.response.send_message(f"⏪ **Rewound 10s** (Current Position: `{mins:02d}:{secs:02d}`)", ephemeral=True)

    async def forward_10s(self, interaction: discord.Interaction):
        state = self.get_state(interaction.guild_id)
        if not state.voice_client or not state.current_track or (not state.voice_client.is_playing() and not state.voice_client.is_paused()):
            return await interaction.response.send_message("❌ Nothing currently playing to fast-forward.", ephemeral=True)

        new_pos = await self.seek_by_delta(interaction.guild_id, 10)
        if new_pos < 0:
            return await interaction.response.send_message("❌ Failed to fast-forward audio.", ephemeral=True)

        mins, secs = divmod(new_pos, 60)
        await interaction.response.send_message(f"⏩ **Fast-Forwarded +10s** (Current Position: `{mins:02d}:{secs:02d}`)", ephemeral=True)

    # ------------------- Interactivity Methods for Views -------------------
    async def toggle_pause(self, interaction: discord.Interaction):
        state = self.get_state(interaction.guild_id)
        if not state.voice_client or not state.voice_client.is_playing():
            if state.voice_client and state.voice_client.is_paused():
                state.voice_client.resume()
                state.is_paused = False
                state.total_paused_duration += (time.time() - state.pause_start)
                await interaction.response.send_message("▶️ Resumed music playback.", ephemeral=True)
            else:
                await interaction.response.send_message("❌ Nothing is currently playing.", ephemeral=True)
            return

        state.voice_client.pause()
        state.is_paused = True
        state.pause_start = time.time()
        await interaction.response.send_message("⏸️ Paused music playback.", ephemeral=True)

    async def skip_track(self, interaction: discord.Interaction):
        state = self.get_state(interaction.guild_id)
        if not state.voice_client or (not state.voice_client.is_playing() and not state.voice_client.is_paused()):
            return await interaction.response.send_message("❌ No track to skip.", ephemeral=True)

        state.voice_client.stop()
        await interaction.response.send_message("⏭️ Skipped to the next track.", ephemeral=True)

    async def prev_track(self, interaction: discord.Interaction):
        state = self.get_state(interaction.guild_id)
        if not state.history:
            return await interaction.response.send_message("❌ No previous track history available.", ephemeral=True)

        prev = state.history.pop()
        state.queue.insert(0, prev)
        if state.current_track:
            state.queue.insert(1, state.current_track)
        
        if state.voice_client:
            state.voice_client.stop()
        await interaction.response.send_message(f"⏮️ Playing previous track: `{prev.get('title')}`", ephemeral=True)

    async def shuffle_queue(self, interaction: discord.Interaction):
        state = self.get_state(interaction.guild_id)
        if len(state.queue) < 2:
            return await interaction.response.send_message("❌ Need at least 2 tracks in queue to shuffle.", ephemeral=True)
        random.shuffle(state.queue)
        await interaction.response.send_message(f"🔀 Shuffled `{len(state.queue)}` tracks in queue!", ephemeral=True)

    async def cycle_loop_mode(self, interaction: discord.Interaction):
        state = self.get_state(interaction.guild_id)
        modes = ["off", "track", "queue"]
        next_idx = (modes.index(state.loop_mode) + 1) % len(modes)
        state.loop_mode = modes[next_idx]
        await interaction.response.send_message(f"🔁 Loop mode set to: `{state.loop_mode.upper()}`", ephemeral=True)

    async def apply_filter(self, guild_id: int, filter_name: str):
        state = self.get_state(guild_id)
        state.filter_name = filter_name
        Database.update_guild_setting(guild_id, "active_filter", filter_name)
        
        if state.voice_client and state.current_track and (state.voice_client.is_playing() or state.voice_client.is_paused()):
            elapsed = self._get_elapsed_time(state)
            await self.seek_to_position(guild_id, elapsed)

    async def set_volume(self, guild_id: int, volume: float):
        state = self.get_state(guild_id)
        state.volume = volume
        Database.update_guild_setting(guild_id, "volume", volume)
        if state.current_source:
            state.current_source.volume = volume

    async def show_queue(self, interaction: discord.Interaction):
        state = self.get_state(interaction.guild_id)
        if not state.queue and not state.current_track:
            return await interaction.response.send_message("📜 The music queue is currently empty.", ephemeral=True)

        embed = discord.Embed(title="📜 RESONANCE APEX Audio Queue", color=EMBED_COLOR_MAIN)
        if state.current_track:
            embed.add_field(name="▶️ Currently Playing", value=f"[{state.current_track.get('title')}]({state.current_track.get('url')}) | Requested by {state.current_track.get('requester')}", inline=False)

        if state.queue:
            queue_list = ""
            for i, t in enumerate(state.queue[:10], start=1):
                queue_list += f"`{i}.` [{t.get('title')}]({t.get('url')}) (`{t.get('requester')}`)\n"
            if len(state.queue) > 10:
                queue_list += f"\n*...and {len(state.queue) - 10} more tracks in queue*"
            embed.add_field(name="Up Next", value=queue_list, inline=False)
        else:
            embed.add_field(name="Up Next", value="*No upcoming tracks. Autoplay will seamlessly spin next track!*", inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def stop_playback(self, interaction: discord.Interaction):
        state = self.get_state(interaction.guild_id)
        if state.current_track:
            self._flush_listener_sessions(state, state.current_track)

        state.queue.clear()
        state.current_track = None
        state.prefetched_autoplay_track = None
        if state.voice_client:
            state.voice_client.stop()
            await state.voice_client.disconnect()
            state.voice_client = None
        await interaction.response.send_message("⏹️ Playback stopped and disconnected from voice channel.", ephemeral=True)

    async def stream_live_broadcast(self, guild: discord.Guild, voice_channel: discord.VoiceChannel, text_channel: Optional[discord.TextChannel], requester_name: str) -> Dict[str, Any]:
        import config
        state = self.get_state(guild.id)
        state.voice_client = await self.ensure_voice_connection(guild, voice_channel)
        
        live_url = config.YOUTUBE_STATUS_URL
        track_info = await YTDLSource.create_source(live_url, loop=self.bot.loop)
        
        if not track_info or not track_info.get('url'):
            if text_channel:
                await text_channel.send(f"⚠️ The live stream event at `{live_url}` is currently offline. Update using `/status url:<new_stream_url>`!")
            return {
                'title': '🔴 Live Stream (Offline/Standby)',
                'url': live_url,
                'duration': 0,
                'uploader': 'Live Broadcast',
                'thumbnail': '',
                'requester': requester_name,
                'text_channel': text_channel,
                'is_live': True
            }

        track_dict = {
            'title': track_info.get('title', '🔴 Live Broadcast'),
            'url': track_info.get('webpage_url') or live_url,
            'duration': track_info.get('duration', 0),
            'uploader': track_info.get('uploader', 'Live Stream'),
            'thumbnail': track_info.get('thumbnail', ''),
            'requester': requester_name,
            'text_channel': text_channel,
            'is_live': True,
            'raw_data': track_info
        }
        
        state.queue.clear()
        if state.voice_client.is_playing() or state.voice_client.is_paused():
            state.voice_client.stop()
            
        state.queue.append(track_dict)
        await self._play_next(guild)
        return track_dict

    # ------------------- Commands -------------------
    @app_commands.command(name="forward", description="Fast forward the currently playing song (+10s or custom seconds)")
    @app_commands.describe(seconds="Number of seconds to skip forward (default: 10)")
    async def forward_slash(self, interaction: discord.Interaction, seconds: Optional[int] = 10):
        await interaction.response.defer(ephemeral=True)
        sec = seconds if (seconds and seconds > 0) else 10
        pos = await self.seek_by_delta(interaction.guild_id, sec)
        if pos < 0:
            return await interaction.followup.send("❌ Nothing currently playing to fast-forward.")
        mins, s = divmod(pos, 60)
        await interaction.followup.send(f"⏩ **Fast-Forwarded +{sec}s** (Current Position: `{mins:02d}:{s:02d}`)")

    @app_commands.command(name="rewind", description="Rewind the currently playing song (-10s or custom seconds)")
    @app_commands.describe(seconds="Number of seconds to rewind (default: 10)")
    async def rewind_slash(self, interaction: discord.Interaction, seconds: Optional[int] = 10):
        await interaction.response.defer(ephemeral=True)
        sec = seconds if (seconds and seconds > 0) else 10
        pos = await self.seek_by_delta(interaction.guild_id, -sec)
        if pos < 0:
            return await interaction.followup.send("❌ Nothing currently playing to rewind.")
        mins, s = divmod(pos, 60)
        await interaction.followup.send(f"⏪ **Rewound -{sec}s** (Current Position: `{mins:02d}:{s:02d}`)")

    @app_commands.command(name="seek", description="Seek to a specific timestamp in the current song (e.g. 90 or 1:30)")
    @app_commands.describe(timestamp="Target position in seconds (e.g. 45) or mm:ss format (e.g. 1:30)")
    async def seek_slash(self, interaction: discord.Interaction, timestamp: str):
        await interaction.response.defer(ephemeral=True)
        target_sec = parse_time_str(timestamp)
        if target_sec is None or target_sec < 0:
            return await interaction.followup.send("❌ Invalid timestamp format. Use seconds (e.g. `90`) or `mm:ss` (e.g. `1:30`).")

        pos = await self.seek_to_position(interaction.guild_id, target_sec)
        if pos < 0:
            return await interaction.followup.send("❌ Nothing currently playing to seek.")
        mins, s = divmod(pos, 60)
        await interaction.followup.send(f"⏩ **Jumped to `{mins:02d}:{s:02d}`**")

    @app_commands.command(name="live", description="Join your voice channel and stream your YouTube Live Broadcast directly")
    async def live(self, interaction: discord.Interaction):
        await interaction.response.defer()
        if not interaction.user.voice or not interaction.user.voice.channel:
            return await interaction.followup.send("❌ You must be connected to a voice channel to start the live stream!")

        voice_channel = interaction.user.voice.channel
        try:
            track = await self.stream_live_broadcast(
                guild=interaction.guild,
                voice_channel=voice_channel,
                text_channel=interaction.channel,
                requester_name=interaction.user.display_name
            )
            embed = discord.Embed(
                title="🔴 Streaming Live Broadcast",
                description=f"Now streaming: [{track['title']}]({track['url']})\n\n🎧 *Exclusively tuned into your live broadcast.*",
                color=EMBED_COLOR_MAIN
            )
            if track.get('thumbnail'):
                embed.set_thumbnail(url=track['thumbnail'])
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to stream live broadcast: `{e}`")

    @app_commands.command(name="join", description="Connect bot to your voice channel and stream your live broadcast")
    async def join(self, interaction: discord.Interaction):
        await self.live(interaction)

    @app_commands.command(name="play", description="Play any song, YouTube link, Spotify track, or playlist!")
    @app_commands.describe(query="Song title, YouTube URL, Spotify link, or Radio stream")
    async def play(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()

        if not interaction.user.voice or not interaction.user.voice.channel:
            return await interaction.followup.send("❌ You must be connected to a voice channel to play music!")

        voice_channel = interaction.user.voice.channel
        state = self.get_state(interaction.guild_id)

        try:
            state.voice_client = await self.ensure_voice_connection(interaction.guild, voice_channel)
        except Exception as ve:
            return await interaction.followup.send(f"❌ Could not connect to voice channel: `{ve}`")

        # Handle Playlist URL
        if "playlist" in query or "album" in query:
            await interaction.followup.send("🔎 Fetching playlist metadata...")
            tracks = await YTDLSource.fetch_playlist_tracks(query, loop=self.bot.loop)
            if not tracks:
                return await interaction.followup.send("❌ Failed to parse playlist tracks.")
            
            for t in tracks:
                t['requester'] = interaction.user.display_name
                t['user_id'] = interaction.user.id
                t['text_channel'] = interaction.channel
                state.queue.append(t)

            await interaction.followup.send(f"✅ Added `{len(tracks)}` tracks from playlist to queue!")
            if not state.voice_client.is_playing() and not state.voice_client.is_paused():
                await self._play_next(interaction.guild)
            return

        # Single track search
        track_info = await YTDLSource.create_source(query, loop=self.bot.loop)
        if not track_info:
            return await interaction.followup.send(f"❌ Could not find track for query: `{query}`")

        track_dict = {
            'title': track_info.get('title', 'Unknown Track'),
            'url': track_info.get('webpage_url') or track_info.get('url'),
            'duration': track_info.get('duration', 0),
            'uploader': track_info.get('uploader', 'Unknown Artist'),
            'thumbnail': track_info.get('thumbnail', ''),
            'requester': interaction.user.display_name,
            'user_id': interaction.user.id,
            'text_channel': interaction.channel,
            'raw_data': track_info
        }

        if state.voice_client.is_playing() or state.voice_client.is_paused():
            state.queue.append(track_dict)
            embed = discord.Embed(
                title="➕ Added to Queue",
                description=f"[{track_dict['title']}]({track_dict['url']})",
                color=EMBED_COLOR_MAIN
            )
            embed.set_thumbnail(url=track_dict['thumbnail'])
            embed.add_field(name="Position in Queue", value=f"`#{len(state.queue)}`", inline=True)
            embed.add_field(name="Duration", value=f"`{track_dict['duration']}s`", inline=True)
            await interaction.followup.send(embed=embed)
        else:
            state.queue.append(track_dict)
            await interaction.followup.send(f"🎶 Starting playback: **{track_dict['title']}**")
            await self._play_next(interaction.guild)

    @app_commands.command(name="radio", description="Generate and play an instant 10-track Spotify-style Radio Mix for any artist or song")
    @app_commands.describe(query="Artist name or song title to base the radio mix on")
    async def radio_cmd(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()
        if not interaction.user.voice or not interaction.user.voice.channel:
            return await interaction.followup.send("❌ You must be connected to a voice channel to start radio mode!")

        voice_channel = interaction.user.voice.channel
        state = self.get_state(interaction.guild_id)

        try:
            state.voice_client = await self.ensure_voice_connection(interaction.guild, voice_channel)
        except Exception as ve:
            return await interaction.followup.send(f"❌ Could not connect to voice channel: `{ve}`")

        await interaction.followup.send(f"📻 Generating **Spotify-style Radio Mix** for `{query}`...")
        tracks = await RecommendationEngine.generate_radio_mix(self.bot.loop, query, count=10)
        if not tracks:
            return await interaction.followup.send("❌ Could not find tracks to build a radio mix.")

        for t in tracks:
            t['requester'] = f"📻 Radio: {interaction.user.display_name}"
            t['user_id'] = interaction.user.id
            t['text_channel'] = interaction.channel
            state.queue.append(t)

        embed = discord.Embed(
            title="📻 Radio Mix Engaged",
            description=f"Generated `{len(tracks)}` smart radio tracks based on **`{query}`**!\n\n**Up First:** [{tracks[0]['title']}]({tracks[0]['url']})",
            color=EMBED_COLOR_MAIN
        )
        if tracks[0].get('thumbnail'):
            embed.set_thumbnail(url=tracks[0]['thumbnail'])
        await interaction.followup.send(embed=embed)

        if not state.voice_client.is_playing() and not state.voice_client.is_paused():
            await self._play_next(interaction.guild)

    @app_commands.command(name="taste", description="View your personal or server listening stats, top artists, and music profile")
    @app_commands.describe(user="The user whose music taste profile to view (defaults to you)")
    async def taste_cmd(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        target = user or interaction.user
        profile = Database.get_user_taste_profile(interaction.guild_id, target.id)
        
        total_plays = profile.get("total_plays", 0)
        formatted_time = profile.get("formatted_total_time", "0 mins")
        top_artists = profile.get("top_artists", [])
        top_songs = profile.get("top_songs", [])
        recent = profile.get("recent", [])

        embed = discord.Embed(
            title=f"🎧 {target.display_name}'s Music Taste Profile",
            description=f"**🔥 Total Plays:** `{total_plays}` tracks | **⏱️ Total Time:** `{formatted_time}` listened\n\n*Smart Autoplay uses this profile to adapt music to your taste in real-time!*",
            color=EMBED_COLOR_DJ
        )
        if target.avatar:
            embed.set_thumbnail(url=target.avatar.url)

        # Top Artists
        if top_artists:
            artist_str = ""
            for i, a in enumerate(top_artists, start=1):
                artist_str += f"`#{i}` **{a['artist']}** (`{a['count']}` plays)\n"
            embed.add_field(name="🌟 Favorite Artists", value=artist_str, inline=False)
        else:
            embed.add_field(name="🌟 Favorite Artists", value="*No listening history recorded yet. Play more songs with `/play`!*", inline=False)

        # Top Tracks
        if top_songs:
            song_str = ""
            for i, s in enumerate(top_songs, start=1):
                song_str += f"`#{i}` [{s['title']}]({s['url']}) (`{s['count']}` plays)\n"
            embed.add_field(name="🎵 Most Played Tracks", value=song_str, inline=False)

        # Recently Listened
        if recent:
            recent_str = ""
            for s in recent[:3]:
                recent_str += f"• [{s['title']}]({s['url']})\n"
            embed.add_field(name="🕒 Recently Listened", value=recent_str, inline=False)

        embed.set_footer(text="RESONANCE APEX • Real Listener Attendance Engine")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="nowplaying", description="Display the dynamic now playing dashboard")
    async def nowplaying(self, interaction: discord.Interaction):
        state = self.get_state(interaction.guild_id)
        if not state.current_track:
            return await interaction.response.send_message("❌ Nothing is currently playing.", ephemeral=True)
        
        elapsed = self._get_elapsed_time(state)
        embed = build_now_playing_embed(
            track=state.current_track,
            current_sec=elapsed,
            loop_mode=state.loop_mode,
            filter_name=state.filter_name,
            is_paused=state.is_paused,
            queue_len=len(state.queue),
            volume=state.volume
        )
        view = MusicControlView(self, interaction.guild_id)
        msg = await interaction.response.send_message(embed=embed, view=view)
        state.dashboard_message = await interaction.original_response()

    @app_commands.command(name="clear", description="Clear all tracks in the queue")
    async def clear(self, interaction: discord.Interaction):
        state = self.get_state(interaction.guild_id)
        count = len(state.queue)
        state.queue.clear()
        state.prefetched_autoplay_track = None
        await interaction.response.send_message(f"🗑️ Cleared `{count}` tracks from the queue.", ephemeral=True)

    # ------------------- Prefix Commands (!play, !forward, !rewind, !seek, etc) -------------------
    @commands.command(name="forward", aliases=["fwd", "+10", "f"])
    async def prefix_forward(self, ctx: commands.Context, seconds: Optional[str] = "10"):
        sec = parse_time_str(seconds) or 10
        pos = await self.seek_by_delta(ctx.guild.id, sec)
        if pos < 0:
            return await ctx.send("❌ Nothing currently playing to fast-forward.")
        mins, s = divmod(pos, 60)
        await ctx.send(f"⏩ **Fast-Forwarded +{sec}s** (Current Position: `{mins:02d}:{s:02d}`)")

    @commands.command(name="rewind", aliases=["rwd", "-10", "r"])
    async def prefix_rewind(self, ctx: commands.Context, seconds: Optional[str] = "10"):
        sec = parse_time_str(seconds) or 10
        pos = await self.seek_by_delta(ctx.guild.id, -sec)
        if pos < 0:
            return await ctx.send("❌ Nothing currently playing to rewind.")
        mins, s = divmod(pos, 60)
        await ctx.send(f"⏪ **Rewound -{sec}s** (Current Position: `{mins:02d}:{s:02d}`)")

    @commands.command(name="seek")
    async def prefix_seek(self, ctx: commands.Context, timestamp: str):
        target_sec = parse_time_str(timestamp)
        if target_sec is None or target_sec < 0:
            return await ctx.send("❌ Invalid timestamp format. Use seconds (e.g. `!seek 90`) or `mm:ss` (e.g. `!seek 1:30`).")

        pos = await self.seek_to_position(ctx.guild.id, target_sec)
        if pos < 0:
            return await ctx.send("❌ Nothing currently playing to seek.")
        mins, s = divmod(pos, 60)
        await ctx.send(f"⏩ **Jumped to `{mins:02d}:{s:02d}`**")

    @commands.command(name="live", aliases=["stream", "join"])
    async def prefix_live(self, ctx: commands.Context):
        if not ctx.author.voice or not ctx.author.voice.channel:
            return await ctx.send("❌ You must be connected to a voice channel to start the live stream!")

        voice_channel = ctx.author.voice.channel
        msg = await ctx.send("🔴 Connecting & loading your live broadcast...")
        try:
            track = await self.stream_live_broadcast(
                guild=ctx.guild,
                voice_channel=voice_channel,
                text_channel=ctx.channel,
                requester_name=ctx.author.display_name
            )
            embed = discord.Embed(
                title="🔴 Streaming Live Broadcast",
                description=f"Now streaming: [{track['title']}]({track['url']})\n\n🎧 *Exclusively streaming your live broadcast.*",
                color=EMBED_COLOR_MAIN
            )
            if track.get('thumbnail'):
                embed.set_thumbnail(url=track['thumbnail'])
            await msg.edit(content="", embed=embed)
        except Exception as e:
            await msg.edit(content=f"❌ Failed to stream live broadcast: `{e}`")

    @commands.command(name="play", aliases=["p"])
    async def prefix_play(self, ctx: commands.Context, *, query: Optional[str] = None):
        if not query:
            return await self.prefix_live(ctx)
        if not ctx.author.voice or not ctx.author.voice.channel:
            return await ctx.send("❌ You must be connected to a voice channel to play music!")

        voice_channel = ctx.author.voice.channel
        state = self.get_state(ctx.guild.id)

        try:
            state.voice_client = await self.ensure_voice_connection(ctx.guild, voice_channel)
        except Exception as ve:
            return await ctx.send(f"❌ Could not connect to voice channel: `{ve}`")

        msg = await ctx.send(f"🔎 Searching for `{query}`...")
        track_info = await YTDLSource.create_source(query, loop=self.bot.loop)
        if not track_info:
            return await msg.edit(content=f"❌ Could not find track for query: `{query}`")

        track_dict = {
            'title': track_info.get('title', 'Unknown Track'),
            'url': track_info.get('webpage_url') or track_info.get('url'),
            'duration': track_info.get('duration', 0),
            'uploader': track_info.get('uploader', 'Unknown Artist'),
            'thumbnail': track_info.get('thumbnail', ''),
            'requester': ctx.author.display_name,
            'user_id': ctx.author.id,
            'text_channel': ctx.channel,
            'raw_data': track_info
        }

        if state.voice_client.is_playing() or state.voice_client.is_paused():
            state.queue.append(track_dict)
            await msg.edit(content=f"➕ Added to Queue: **{track_dict['title']}** (`#{len(state.queue)}`)")
        else:
            state.queue.append(track_dict)
            await msg.edit(content=f"🎶 Starting playback: **{track_dict['title']}**")
            await self._play_next(ctx.guild)

    @commands.command(name="radio")
    async def prefix_radio(self, ctx: commands.Context, *, query: str):
        if not ctx.author.voice or not ctx.author.voice.channel:
            return await ctx.send("❌ You must be connected to a voice channel to start radio mode!")

        voice_channel = ctx.author.voice.channel
        state = self.get_state(ctx.guild.id)

        try:
            state.voice_client = await self.ensure_voice_connection(ctx.guild, voice_channel)
        except Exception as ve:
            return await ctx.send(f"❌ Could not connect to voice channel: `{ve}`")

        msg = await ctx.send(f"📻 Generating **Spotify-style Radio Mix** for `{query}`...")
        tracks = await RecommendationEngine.generate_radio_mix(self.bot.loop, query, count=10)
        if not tracks:
            return await msg.edit(content="❌ Could not find tracks to build a radio mix.")

        for t in tracks:
            t['requester'] = f"📻 Radio: {ctx.author.display_name}"
            t['user_id'] = ctx.author.id
            t['text_channel'] = ctx.channel
            state.queue.append(t)

        embed = discord.Embed(
            title="📻 Radio Mix Engaged",
            description=f"Generated `{len(tracks)}` smart radio tracks based on **`{query}`**!\n\n**Up First:** [{tracks[0]['title']}]({tracks[0]['url']})",
            color=EMBED_COLOR_MAIN
        )
        if tracks[0].get('thumbnail'):
            embed.set_thumbnail(url=tracks[0]['thumbnail'])
        await msg.edit(content="", embed=embed)

        if not state.voice_client.is_playing() and not state.voice_client.is_paused():
            await self._play_next(ctx.guild)

    @commands.command(name="taste", aliases=["profile", "stats"])
    async def prefix_taste(self, ctx: commands.Context, user: Optional[discord.Member] = None):
        target = user or ctx.author
        profile = Database.get_user_taste_profile(ctx.guild.id, target.id)
        
        total_plays = profile.get("total_plays", 0)
        formatted_time = profile.get("formatted_total_time", "0 mins")
        top_artists = profile.get("top_artists", [])
        top_songs = profile.get("top_songs", [])
        recent = profile.get("recent", [])

        embed = discord.Embed(
            title=f"🎧 {target.display_name}'s Music Taste Profile",
            description=f"**🔥 Total Plays:** `{total_plays}` tracks | **⏱️ Total Time:** `{formatted_time}` listened\n\n*Smart Autoplay uses this profile to adapt music to your taste in real-time!*",
            color=EMBED_COLOR_DJ
        )
        if target.avatar:
            embed.set_thumbnail(url=target.avatar.url)

        if top_artists:
            artist_str = ""
            for i, a in enumerate(top_artists, start=1):
                artist_str += f"`#{i}` **{a['artist']}** (`{a['count']}` plays)\n"
            embed.add_field(name="🌟 Favorite Artists", value=artist_str, inline=False)
        else:
            embed.add_field(name="🌟 Favorite Artists", value="*No listening history recorded yet. Play more songs with !play!*", inline=False)

        if top_songs:
            song_str = ""
            for i, s in enumerate(top_songs, start=1):
                song_str += f"`#{i}` [{s['title']}]({s['url']}) (`{s['count']}` plays)\n"
            embed.add_field(name="🎵 Most Played Tracks", value=song_str, inline=False)

        if recent:
            recent_str = ""
            for s in recent[:3]:
                recent_str += f"• [{s['title']}]({s['url']})\n"
            embed.add_field(name="🕒 Recently Listened", value=recent_str, inline=False)

        embed.set_footer(text="RESONANCE APEX • Real Listener Attendance Engine")
        await ctx.send(embed=embed)

    @commands.command(name="np", aliases=["nowplaying"])
    async def prefix_np(self, ctx: commands.Context):
        state = self.get_state(ctx.guild.id)
        if not state.current_track:
            return await ctx.send("❌ Nothing is currently playing.")
        
        elapsed = self._get_elapsed_time(state)
        embed = build_now_playing_embed(
            track=state.current_track,
            current_sec=elapsed,
            loop_mode=state.loop_mode,
            filter_name=state.filter_name,
            is_paused=state.is_paused,
            queue_len=len(state.queue),
            volume=state.volume
        )
        view = MusicControlView(self, ctx.guild.id)
        msg = await ctx.send(embed=embed, view=view)
        state.dashboard_message = msg

    @commands.command(name="skip", aliases=["s"])
    async def prefix_skip(self, ctx: commands.Context):
        state = self.get_state(ctx.guild.id)
        if state.voice_client and (state.voice_client.is_playing() or state.voice_client.is_paused()):
            state.voice_client.stop()
            await ctx.send("⏭️ Skipped current track.")
        else:
            await ctx.send("❌ Nothing playing to skip.")

    @commands.command(name="queue", aliases=["q"])
    async def prefix_queue(self, ctx: commands.Context):
        state = self.get_state(ctx.guild.id)
        if not state.queue and not state.current_track:
            return await ctx.send("📜 The queue is empty.")

        embed = discord.Embed(title="📜 RESONANCE APEX Audio Queue", color=EMBED_COLOR_MAIN)
        if state.current_track:
            embed.add_field(name="▶️ Currently Playing", value=f"[{state.current_track.get('title')}]({state.current_track.get('url')}) | Requested by {state.current_track.get('requester')}", inline=False)

        if state.queue:
            queue_list = ""
            for i, t in enumerate(state.queue[:10], start=1):
                queue_list += f"`{i}.` [{t.get('title')}]({t.get('url')}) (`{t.get('requester')}`)\n"
            embed.add_field(name="Up Next", value=queue_list, inline=False)

        await ctx.send(embed=embed)

    @commands.command(name="stop")
    async def prefix_stop(self, ctx: commands.Context):
        state = self.get_state(ctx.guild.id)
        if state.current_track:
            self._flush_listener_sessions(state, state.current_track)

        state.queue.clear()
        state.current_track = None
        state.prefetched_autoplay_track = None
        if state.voice_client:
            state.voice_client.stop()
            await state.voice_client.disconnect()
            state.voice_client = None
        await ctx.send("⏹️ Stopped playback and disconnected from voice channel.")


async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))
