import discord
from discord.ui import View, Button, Select, Modal, TextInput
from typing import Dict, Any, Optional
from config import EMBED_COLOR_MAIN, EMBED_COLOR_PLAY, EMBED_COLOR_PAUSE, EMBED_COLOR_EQ, BOT_NAME, AUDIO_FILTERS
from utils.visualizer import create_progress_bar, get_animated_spectrum, format_duration
from utils.database import Database

SPOTIFY_GREEN = 0x1DB954
SPOTIFY_BLACK = 0x121212
SPOTIFY_PURPLE = 0x8A2BE2

def build_now_playing_embed(track: Dict[str, Any], current_sec: int, loop_mode: str, filter_name: str, is_paused: bool, queue_len: int, volume: float) -> discord.Embed:
    status_icon = "⏸️ PAUSED" if is_paused else "▶️ NOW PLAYING"
    color = 0xFFA500 if is_paused else SPOTIFY_GREEN

    raw_title = track.get('title', 'Unknown Track')
    raw_artist = track.get('uploader', 'Unknown Artist').replace(' - Topic', '')

    embed = discord.Embed(
        title=f"{status_icon} • {raw_title}",
        url=track.get('webpage_url') or track.get('url', ''),
        color=color
    )

    total_sec = track.get('duration', 0)
    progress_bar = create_progress_bar(current_sec, total_sec)
    wave = get_animated_spectrum()

    # Spotify AI DJ Insight Pill
    recom_type = track.get('recommendation_type')
    if recom_type == 'transition':
        ai_insight = "🤖 **Spotify AI DJ**: *Spun via Song Transition Graph (Markov Intelligence)*"
    elif recom_type in ('user_taste', 'artist_taste'):
        ai_insight = "🎧 **Spotify AI DJ**: *Curated for Live Voice Room Taste*"
    elif recom_type == 'radio_discovery':
        ai_insight = "📻 **Spotify AI DJ**: *Algorithmic Song Radio Discovery*"
    else:
        ai_insight = f"👤 **Requested by**: `{track.get('requester', 'DJ')}`"

    embed.description = f"{ai_insight}\n\n{progress_bar}\n`{wave}` **SPOTIFY 320K ULTRA HQ** `{wave}`"

    # Clean Metadata Fields
    embed.add_field(name="🎙️ Artist", value=f"`{raw_artist}`", inline=True)
    embed.add_field(name="🎛️ Equalizer", value=f"`{filter_name.upper()}`", inline=True)
    embed.add_field(name="🔊 Volume", value=f"`{int(volume * 100)}%`", inline=True)

    embed.add_field(name="🔁 Loop Mode", value=f"`{loop_mode.upper()}`", inline=True)
    embed.add_field(name="📜 Queue", value=f"`{queue_len} Tracks`", inline=True)
    embed.add_field(name="⚡ Audio Stream", value="`Lossless Opus`", inline=True)

    if track.get('thumbnail'):
        embed.set_thumbnail(url=track['thumbnail'])

    embed.set_footer(text="Spotify AI DJ • Use buttons below to seek & control")
    return embed


class VolumeModal(Modal, title="🔊 Adjust Master Volume"):
    volume_input = TextInput(
        label="Enter Volume (0 to 200%)",
        placeholder="e.g. 80, 100, 150",
        min_length=1,
        max_length=4,
        required=True
    )

    def __init__(self, music_cog, guild_id: int):
        super().__init__()
        self.music_cog = music_cog
        self.guild_id = guild_id

    async def on_submit(self, interaction: discord.Interaction):
        try:
            val = float(self.volume_input.value)
            if val < 0 or val > 200:
                return await interaction.response.send_message("❌ Volume must be between 0% and 200%.", ephemeral=True)
            
            vol_normalized = val / 100.0
            await self.music_cog.set_volume(interaction.guild_id, vol_normalized)
            await interaction.response.send_message(f"🔊 Master volume set to `{int(val)}%`", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Invalid volume input. Please enter a number.", ephemeral=True)


class FilterSelect(Select):
    def __init__(self, music_cog):
        options = [
            discord.SelectOption(label="Normal (Flat EQ)", value="normal", description="Default balanced studio audio", emoji="🎵"),
            discord.SelectOption(label="8D Surround", value="8d", description="360° rotating spatial surround sound", emoji="🎧"),
            discord.SelectOption(label="Bassboost Low", value="bassboost_low", description="+6dB Sub-bass boost", emoji="🔊"),
            discord.SelectOption(label="Bassboost Med", value="bassboost_med", description="+12dB Club punchy bass", emoji="🎛️"),
            discord.SelectOption(label="Bassboost Extreme", value="bassboost_extreme", description="+24dB Heavy subwoofer rumble", emoji="💥"),
            discord.SelectOption(label="Nightcore", value="nightcore", description="Speed up tempo and pitch shift", emoji="⚡"),
            discord.SelectOption(label="Vaporwave", value="vaporwave", description="Slowed + reverb aesthetic", emoji="🌊"),
            discord.SelectOption(label="Reverb Room", value="reverb_room", description="Club room acoustic resonance", emoji="🏛️"),
            discord.SelectOption(label="Reverb Arena", value="reverb_arena", description="Massive stadium echo", emoji="🏟️"),
            discord.SelectOption(label="Karaoke", value="karaoke", description="Center vocal remover filter", emoji="🎤"),
            discord.SelectOption(label="Lowpass (Club Next Door)", value="lowpass", description="Muffled party outside room effect", emoji="🚪"),
            discord.SelectOption(label="Vibrato", value="vibrato", description="Wavy pitch modulation", emoji="〰️"),
        ]
        super().__init__(placeholder="🎛️ Choose DSP Audio Filter / Equalizer...", min_values=1, max_values=1, options=options)
        self.music_cog = music_cog

    async def callback(self, interaction: discord.Interaction):
        selected_filter = self.values[0]
        await interaction.response.defer(ephemeral=True)
        await self.music_cog.apply_filter(interaction.guild_id, selected_filter)
        await interaction.followup.send(f"🎛️ Applied Audio Filter: `{selected_filter.upper()}`", ephemeral=True)


class FilterSelectView(View):
    def __init__(self, music_cog):
        super().__init__(timeout=120)
        self.add_item(FilterSelect(music_cog))


class MusicControlView(View):
    def __init__(self, music_cog, guild_id: int):
        super().__init__(timeout=None) # Persistent view
        self.music_cog = music_cog
        self.guild_id = guild_id

    @discord.ui.button(label="Prev", style=discord.ButtonStyle.secondary, emoji="⏮️", custom_id="spotify_prev", row=0)
    async def prev_button(self, interaction: discord.Interaction, button: Button):
        await self.music_cog.prev_track(interaction)

    @discord.ui.button(label="Play/Pause", style=discord.ButtonStyle.primary, emoji="⏯️", custom_id="spotify_pause", row=0)
    async def pause_button(self, interaction: discord.Interaction, button: Button):
        await self.music_cog.toggle_pause(interaction)

    @discord.ui.button(label="Skip", style=discord.ButtonStyle.secondary, emoji="⏭️", custom_id="spotify_skip", row=0)
    async def skip_button(self, interaction: discord.Interaction, button: Button):
        await self.music_cog.skip_track(interaction)

    @discord.ui.button(label="Like", style=discord.ButtonStyle.success, emoji="💚", custom_id="spotify_like", row=0)
    async def like_button(self, interaction: discord.Interaction, button: Button):
        state = self.music_cog.get_state(interaction.guild_id)
        if not state.current_track:
            return await interaction.response.send_message("❌ Nothing currently playing to like!", ephemeral=True)
        
        # Save to user's Liked Songs playlist
        track = state.current_track
        liked_tracks = Database.load_playlist(interaction.guild_id, interaction.user.id, "Liked_Songs")
        if not any(t.get('url') == track.get('url') for t in liked_tracks):
            liked_tracks.append({
                'title': track.get('title', 'Unknown Track'),
                'url': track.get('webpage_url') or track.get('url', ''),
                'duration': track.get('duration', 0),
                'thumbnail': track.get('thumbnail', '')
            })
            Database.save_playlist(interaction.guild_id, interaction.user.id, "Liked_Songs", liked_tracks)
            await interaction.response.send_message(f"💚 Added **{track.get('title')}** to your **Liked Songs** vault! (`/playlist load name:Liked_Songs`)", ephemeral=True)
        else:
            await interaction.response.send_message("💚 This track is already in your Liked Songs vault!", ephemeral=True)

    @discord.ui.button(label="Radio Mix", style=discord.ButtonStyle.secondary, emoji="📻", custom_id="spotify_radio", row=0)
    async def radio_button(self, interaction: discord.Interaction, button: Button):
        state = self.music_cog.get_state(interaction.guild_id)
        if not state.current_track:
            return await interaction.response.send_message("❌ No active track to build a Radio Mix from.", ephemeral=True)
        
        query = state.current_track.get('uploader') or state.current_track.get('title')
        await interaction.response.defer(ephemeral=True)
        from utils.recommendation import RecommendationEngine
        tracks = await RecommendationEngine.generate_radio_mix(self.music_cog.bot.loop, query, count=8)
        if not tracks:
            return await interaction.followup.send("❌ Could not generate Radio Mix.", ephemeral=True)

        for t in tracks[1:]: # Skip current seed if already playing
            t['requester'] = f"📻 Radio ({interaction.user.display_name})"
            t['user_id'] = interaction.user.id
            t['text_channel'] = interaction.channel
            state.queue.append(t)

        await interaction.followup.send(f"📻 **Spotify Radio Mix Queued!** Added `{len(tracks)-1}` tracks inspired by **{query}** to the queue!", ephemeral=True)

    @discord.ui.button(label="-10s", style=discord.ButtonStyle.secondary, emoji="⏪", custom_id="spotify_rewind_10", row=1)
    async def rewind_button(self, interaction: discord.Interaction, button: Button):
        await self.music_cog.rewind_10s(interaction)

    @discord.ui.button(label="+10s", style=discord.ButtonStyle.secondary, emoji="⏩", custom_id="spotify_forward_10", row=1)
    async def forward_button(self, interaction: discord.Interaction, button: Button):
        await self.music_cog.forward_10s(interaction)

    @discord.ui.button(label="Shuffle", style=discord.ButtonStyle.secondary, emoji="🔀", custom_id="spotify_shuffle", row=1)
    async def shuffle_button(self, interaction: discord.Interaction, button: Button):
        await self.music_cog.shuffle_queue(interaction)

    @discord.ui.button(label="Loop", style=discord.ButtonStyle.secondary, emoji="🔁", custom_id="spotify_loop", row=1)
    async def loop_button(self, interaction: discord.Interaction, button: Button):
        await self.music_cog.cycle_loop_mode(interaction)

    @discord.ui.button(label="Audio FX", style=discord.ButtonStyle.secondary, emoji="🎛️", custom_id="spotify_fx", row=1)
    async def fx_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message(
            "**RESONANCE DSP Audio Filter Console**\nSelect an audio equalizer preset below:",
            view=FilterSelectView(self.music_cog),
            ephemeral=True
        )

    @discord.ui.button(label="Queue", style=discord.ButtonStyle.secondary, emoji="📜", custom_id="spotify_queue", row=2)
    async def queue_button(self, interaction: discord.Interaction, button: Button):
        await self.music_cog.show_queue(interaction)

    @discord.ui.button(label="Stop", style=discord.ButtonStyle.danger, emoji="⏹️", custom_id="spotify_stop", row=2)
    async def stop_button(self, interaction: discord.Interaction, button: Button):
        await self.music_cog.stop_playback(interaction)
