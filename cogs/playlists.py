import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
from utils.database import Database
from utils.recommendation import RecommendationEngine
from config import EMBED_COLOR_MAIN, EMBED_COLOR_DJ

class Playlists(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    playlist_group = app_commands.Group(name="playlist", description="Manage personal, server, and AI-generated music playlists")

    @playlist_group.command(name="save", description="Save current active queue as a named custom playlist")
    @app_commands.describe(name="Name of the playlist (e.g. VIP_Club_Mix)")
    async def save(self, interaction: discord.Interaction, name: str):
        music_cog = self.bot.get_cog("Music")
        if not music_cog:
            return await interaction.response.send_message("❌ Music module unavailable.", ephemeral=True)

        state = music_cog.get_state(interaction.guild_id)
        all_tracks = []
        if state.current_track:
            all_tracks.append(state.current_track)
        all_tracks.extend(state.queue)

        if not all_tracks:
            return await interaction.response.send_message("❌ Queue is empty. Add songs to queue before saving a playlist!", ephemeral=True)

        success = Database.save_playlist(interaction.guild_id, interaction.user.id, name, all_tracks)
        if success:
            embed = discord.Embed(
                title="💾 Playlist Saved to Vault",
                description=f"Playlist **`{name}`** successfully stored with `{len(all_tracks)}` tracks!",
                color=EMBED_COLOR_MAIN
            )
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("❌ Failed to save playlist to database.", ephemeral=True)

    @playlist_group.command(name="load", description="Load a saved custom playlist into the queue")
    @app_commands.describe(name="Name of your saved playlist")
    async def load(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer()
        if not interaction.user.voice or not interaction.user.voice.channel:
            return await interaction.followup.send("❌ You must be connected to a voice channel to load playlists!")

        tracks = Database.load_playlist(interaction.guild_id, interaction.user.id, name)
        if not tracks:
            return await interaction.followup.send(f"❌ Playlist **`{name}`** not found in your vault.")

        music_cog = self.bot.get_cog("Music")
        if not music_cog:
            return await interaction.followup.send("❌ Music module unavailable.")

        state = music_cog.get_state(interaction.guild_id)

        try:
            state.voice_client = await music_cog.ensure_voice_connection(interaction.guild, interaction.user.voice.channel)
        except Exception as ve:
            return await interaction.followup.send(f"❌ Could not connect to voice channel: `{ve}`")

        for t in tracks:
            t['requester'] = interaction.user.display_name
            t['user_id'] = interaction.user.id
            t['text_channel'] = interaction.channel
            state.queue.append(t)

        await interaction.followup.send(f"✅ Loaded `{len(tracks)}` tracks from playlist **`{name}`** into queue!")

        if not state.voice_client.is_playing() and not state.voice_client.is_paused():
            await music_cog._play_next(interaction.guild)

    @playlist_group.command(name="mix_for_me", description="AI generates and saves a Spotify-style personalized Daily Mix based on your taste")
    @app_commands.describe(name="Optional custom name for your playlist (defaults to 'My_AI_Daily_Mix')")
    async def mix_for_me(self, interaction: discord.Interaction, name: Optional[str] = "My_AI_Daily_Mix"):
        await interaction.response.defer()
        tracks = await RecommendationEngine.generate_user_taste_mix(self.bot.loop, interaction.guild_id, interaction.user.id, count=15)
        if not tracks:
            return await interaction.followup.send("❌ Not enough listening history to generate a personalized mix. Listen to a few tracks with `/play` first!")

        success = Database.save_playlist(interaction.guild_id, interaction.user.id, name, tracks)
        if success:
            embed = discord.Embed(
                title="✨ Personalized Spotify Daily Mix Created!",
                description=f"Generated and saved **`{name}`** with `{len(tracks)}` curated tracks tailored to your music taste profile!\n\nUse `/playlist load name:{name}` to play it anytime.",
                color=EMBED_COLOR_DJ
            )
            preview_list = ""
            for i, t in enumerate(tracks[:5], start=1):
                preview_list += f"`{i}.` [{t['title']}]({t['url']})\n"
            if len(tracks) > 5:
                preview_list += f"*...and {len(tracks) - 5} more personalized tracks*"
            embed.add_field(name="🎶 Playlist Preview", value=preview_list, inline=False)
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send("❌ Failed to save AI mix to database.")

    @playlist_group.command(name="radio_seed", description="Generate and save a 10-track Spotify-style radio mix as a playlist")
    @app_commands.describe(query="Artist or song to seed the radio mix", name="Name for saved playlist")
    async def radio_seed(self, interaction: discord.Interaction, query: str, name: str):
        await interaction.response.defer()
        tracks = await RecommendationEngine.generate_radio_mix(self.bot.loop, query, count=10)
        if not tracks:
            return await interaction.followup.send(f"❌ Could not find tracks to build a radio mix for `{query}`.")

        success = Database.save_playlist(interaction.guild_id, interaction.user.id, name, tracks)
        if success:
            embed = discord.Embed(
                title="📻 Radio Mix Saved to Playlist Vault",
                description=f"Generated and saved **`{name}`** (`{len(tracks)}` tracks) based on **`{query}`**!\n\nLoad anytime with `/playlist load name:{name}`.",
                color=EMBED_COLOR_MAIN
            )
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send("❌ Failed to save radio playlist.")

    @playlist_group.command(name="list", description="List all your saved custom playlists")
    async def list_playlists(self, interaction: discord.Interaction):
        playlists = Database.get_user_playlists(interaction.guild_id, interaction.user.id)
        if not playlists:
            return await interaction.response.send_message("📂 You have no saved playlists in this server.", ephemeral=True)

        embed = discord.Embed(title=f"📂 {interaction.user.display_name}'s Playlist Vault", color=EMBED_COLOR_MAIN)
        desc = ""
        for i, name in enumerate(playlists, start=1):
            desc += f"`{i}.` **`{name}`**\n"
        embed.description = desc
        embed.set_footer(text="Use /playlist load name:<name> to play any playlist!")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @playlist_group.command(name="delete", description="Delete a saved custom playlist from your vault")
    @app_commands.describe(name="Name of playlist to delete")
    async def delete(self, interaction: discord.Interaction, name: str):
        success = Database.delete_playlist(interaction.guild_id, interaction.user.id, name)
        if success:
            await interaction.response.send_message(f"🗑️ Deleted playlist **`{name}`**.", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ Playlist **`{name}`** was not found.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Playlists(bot))
