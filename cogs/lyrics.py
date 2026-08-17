import discord
from discord.ext import commands
from discord import app_commands
import requests
from typing import Optional
from config import EMBED_COLOR_MAIN

class Lyrics(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="lyrics", description="Fetch real-time synced lyrics for the playing track")
    @app_commands.describe(search="Optional track name to search for lyrics")
    async def lyrics(self, interaction: discord.Interaction, search: Optional[str] = None):
        await interaction.response.defer()

        target_title = search
        if not target_title:
            music_cog = self.bot.get_cog("Music")
            if music_cog:
                state = music_cog.get_state(interaction.guild_id)
                if state.current_track:
                    target_title = state.current_track.get('title')

        if not target_title:
            return await interaction.followup.send("❌ No track currently playing. Please provide a track title: `/lyrics search:<title>`")

        # Query LrcLib API (free synced lyrics API)
        try:
            cleaned_title = target_title.split("(")[0].split("[")[0].strip()
            resp = requests.get(f"https://lrclib.net/api/search?q={cleaned_title}", timeout=5).json()

            if not resp or not isinstance(resp, list) or len(resp) == 0:
                return await interaction.followup.send(f"❌ No lyrics found for `{target_title}`.")

            match = resp[0]
            lyrics_plain = match.get("plainLyrics") or match.get("syncedLyrics")
            track_name = match.get("trackName", target_title)
            artist_name = match.get("artistName", "Unknown Artist")

            if not lyrics_plain:
                return await interaction.followup.send(f"❌ Lyrics empty for `{target_title}`.")

            # Truncate if exceeds embed length
            if len(lyrics_plain) > 3500:
                lyrics_plain = lyrics_plain[:3500] + "\n\n*...[Lyrics Truncated]*"

            embed = discord.Embed(
                title=f"📜 Lyrics | {track_name}",
                description=lyrics_plain,
                color=EMBED_COLOR_MAIN
            )
            embed.set_footer(text=f"Artist: {artist_name} • RESONANCE Lyrics Search Engine")
            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(f"❌ Error fetching lyrics: {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(Lyrics(bot))
