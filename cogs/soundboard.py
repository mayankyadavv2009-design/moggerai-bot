import discord
from discord.ext import commands
from discord import app_commands
from typing import Literal

SOUND_EFFECT_URLS = {
    "airhorn": "https://www.myinstants.com/media/sounds/mlg-airhorn.mp3",
    "scratch": "https://www.myinstants.com/media/sounds/scratch-sound-effect.mp3",
    "bassdrop": "https://www.myinstants.com/media/sounds/epic-bass-drop.mp3",
    "applause": "https://www.myinstants.com/media/sounds/crowd-cheering-sound-effect.mp3",
    "rewind": "https://www.myinstants.com/media/sounds/tape-rewind-sound-effect.mp3",
}

class Soundboard(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="soundboard", description="Trigger instant club DJ soundboard effects over audio stream")
    @app_commands.describe(effect="Select club sound effect drop")
    async def soundboard(self, interaction: discord.Interaction, effect: Literal["airhorn", "scratch", "bassdrop", "applause", "rewind"]):
        await interaction.response.defer(ephemeral=True)
        if not interaction.user.voice or not interaction.user.voice.channel:
            return await interaction.followup.send("❌ Connect to voice channel to trigger soundboard effects!")

        music_cog = self.bot.get_cog("Music")
        if not music_cog:
            return await interaction.followup.send("❌ Music module unavailable.")

        state = music_cog.get_state(interaction.guild_id)
        if not state.voice_client or not state.voice_client.is_connected():
            return await interaction.followup.send("❌ Bot is not currently in a voice channel.")

        # Intercept track playback to play instant sound effect drop
        effect_url = SOUND_EFFECT_URLS.get(effect)
        if effect_url:
            # If playing music, queue effect immediately at front
            state.queue.insert(0, {
                'title': f"🔊 FX DROP: {effect.upper()}",
                'url': effect_url,
                'duration': 3,
                'uploader': 'RESONANCE Soundboard',
                'thumbnail': '',
                'requester': interaction.user.display_name,
                'text_channel': interaction.channel
            })
            if state.voice_client.is_playing():
                state.voice_client.stop()
            else:
                await music_cog._play_next(interaction.guild)

            await interaction.followup.send(f"🎉 Triggered Soundboard Drop: **`{effect.upper()}`**")


async def setup(bot: commands.Bot):
    await bot.add_cog(Soundboard(bot))
