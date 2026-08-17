import discord
from discord.ext import commands
from discord import app_commands
from typing import Literal
from config import AUDIO_FILTERS, EMBED_COLOR_EQ

class AudioFX(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="filter", description="Set or reset real-time FFmpeg DSP audio filters & equalizers")
    @app_commands.describe(preset="Select an audio DSP filter preset")
    async def filter_cmd(self, interaction: discord.Interaction, preset: Literal[
        "normal", "8d", "bassboost_low", "bassboost_med", "bassboost_high", "bassboost_extreme",
        "nightcore", "vaporwave", "reverb_room", "reverb_hall", "reverb_arena", "karaoke",
        "vibrato", "tremolo", "speed_fast", "speed_slow", "flanger", "phaser", "lowpass", "highpass"
    ]):
        await interaction.response.defer()
        music_cog = self.bot.get_cog("Music")
        if not music_cog:
            return await interaction.followup.send("❌ Music module is currently disabled.")

        await music_cog.apply_filter(interaction.guild_id, preset)

        embed = discord.Embed(
            title="🎛️ RESONANCE Audio DSP Equalizer Engaged",
            description=f"Applied Filter Preset: **`{preset.upper()}`**\nFilter String: `{AUDIO_FILTERS.get(preset, 'Direct Audio Pass-through')}`",
            color=EMBED_COLOR_EQ
        )
        embed.set_footer(text="Equalizer changes will seamlessly reload the active track.")
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(AudioFX(bot))
