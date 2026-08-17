import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Select
from config import EMBED_COLOR_MAIN, BOT_NAME, BOT_VERSION


class HelpSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Game Dev & Roblox AI", value="gamedev", description="Roblox 3D/2D Luau, AAA engines, WebGPU, Pygame, C++", emoji="🎮"),
            discord.SelectOption(label="Core Music Engine", value="music", description="Play, pause, skip, queue, loop, volume", emoji="🎵"),
            discord.SelectOption(label="DSP Equalizers & Filters", value="fx", description="8D Surround, Bassboost 1-3, Nightcore, Reverb, Karaoke", emoji="🎛️"),
            discord.SelectOption(label="Club DJ Controls", value="dj", description="DJ role, 24/7 mode, autoplay, vote skip", emoji="🎧"),
            discord.SelectOption(label="Playlist Vault", value="playlist", description="Save, load, list, delete custom server playlists", emoji="📂"),
            discord.SelectOption(label="Soundboard Drops", value="soundboard", description="Airhorn, vinyl scratch, bassdrop sound drops", emoji="🔊"),
            discord.SelectOption(label="Web Remote Controller", value="web", description="Browser web dashboard access & controls", emoji="🌐"),
        ]
        super().__init__(placeholder="🔍 Select Command Category...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        cat = self.values[0]
        embed = discord.Embed(color=EMBED_COLOR_MAIN)

        if cat == "gamedev":
            embed.title = "🎮 Game Dev & Roblox Studio AI Commands"
            embed.description = (
                "`/roblox system:<type> details:<str>` - Generate ultra-realistic 3D/2D Roblox Luau scripts:\n"
                "• `3D Spring Camera Recoil & Sway`\n"
                "• `Raycast Gun & Ballistics with Drop`\n"
                "• `Server Lag Compensation Rewind Buffer`\n"
                "• `Procedural Foot Inverse Kinematics (IK)`\n"
                "• `2D Drag-and-Drop Grid Inventory`\n"
                "• `Raycast Vehicle Chassis Suspension`\n\n"
                "`/gamedev engine:<type> task:<str>` - Generate AAA mechanics, 60FPS physics, shaders:\n"
                "• `Roblox Luau (3D/2D)`\n"
                "• `HTML5 Canvas / WebGPU Shaders`\n"
                "• `Python (Pygame & Ursina 3D)`\n"
                "• `Java (LibGDX & Minecraft)`\n"
                "• `C++ (Unreal Engine & Raylib)`\n\n"
                "`/ask prompt:<str>` - Chat with MoggerAI on any coding, music theory, or banter topic."
            )
        elif cat == "music":
            embed.title = "🎵 Core Music Engine Commands"
            embed.description = (
                "`/live` (or `/join`) - Connect to voice and stream your YouTube Live Broadcast directly\n"
                "`/play query:<str>` - Play song title, YouTube URL, Spotify link, or playlist\n"
                "`/nowplaying` - Display active interactive audio dashboard embed\n"
                "`/queue` - View up-to-date queue list & current track\n"
                "`/clear` - Clear all pending tracks in queue\n"
                "`!live` / `!play` - Support for prefix commands"
            )
        elif cat == "fx":
            embed.title = "🎛️ DSP Equalizer & Audio FX Commands"
            embed.description = (
                "`/filter preset:<name>` - Apply dynamic FFmpeg audio DSP filter:\n"
                "• `8D` (360° Spatial Surround)\n"
                "• `BASSBOOST_EXTREME` (+24dB Sub-woofer punch)\n"
                "• `NIGHTCORE` (Speed up & pitch shift)\n"
                "• `VAPORWAVE` (Slowed + reverb aesthetic)\n"
                "• `REVERB_ARENA` (Stadium resonance)\n"
                "• `KARAOKE` (Vocal isolation filter)\n"
                "• `LOWPASS` (Muffled outside party room effect)"
            )
        elif cat == "dj":
            embed.title = "🎧 Club DJ Permissions & Controls"
            embed.description = (
                "`/dj_setrole role:<Role>` - Set required DJ role\n"
                "`/dj_247 enabled:<bool>` - Keep bot in voice channel 24/7\n"
                "`/dj_autoplay enabled:<bool>` - AI recommended auto-queue when queue ends\n"
                "`/voteskip` - Vote to skip song (50% listener consensus)\n"
                "`/status url:<link> title:<text>` - View or update live YouTube streaming status"
            )
        elif cat == "playlist":
            embed.title = "📂 Custom Playlist Vault Commands"
            embed.description = (
                "`/playlist save name:<str>` - Save active queue to SQLite database\n"
                "`/playlist load name:<str>` - Load saved playlist directly to queue\n"
                "`/playlist list` - View your saved playlists\n"
                "`/playlist delete name:<str>` - Remove playlist from vault"
            )
        elif cat == "soundboard":
            embed.title = "🔊 Instant Club Soundboard FX"
            embed.description = (
                "`/soundboard effect:<name>` - Trigger audio drops over stream:\n"
                "• `airhorn` (Classic DJ airhorn blast)\n"
                "• `scratch` (Turntable vinyl scratch)\n"
                "• `bassdrop` (Sub-bass explosion)\n"
                "• `applause` (Crowd cheer)\n"
                "• `rewind` (Tape rewind drop)"
            )
        elif cat == "web":
            embed.title = "🌐 Instant Web Remote Controller"
            embed.description = (
                "**Local Browser Access:** `http://localhost:5000`\n"
                "Control music, adjust equalizers, view queue, and search tracks directly from any browser on desktop or mobile device!"
            )

        embed.set_footer(text=f"{BOT_NAME} v{BOT_VERSION}")
        await interaction.response.send_message(embed=embed, ephemeral=True)


class HelpView(View):
    def __init__(self):
        super().__init__(timeout=120)
        self.add_item(HelpSelect())


class Help(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="help", description="Interactive guide for all RESONANCE APEX commands & features")
    async def help_cmd(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=f"⚡ {BOT_NAME} - Command Center",
            description=f"Welcome to **{BOT_NAME}** (`v{BOT_VERSION}`). Select a category from the dropdown menu below to view specific command details.",
            color=EMBED_COLOR_MAIN
        )
        embed.add_field(name="🚀 Quickstart", value="1. Join a voice channel\n2. Run `/play query:<song title or URL>`\n3. Use interactive message buttons to control playback & audio FX!", inline=False)
        embed.set_thumbnail(url=self.bot.user.display_avatar.url if self.bot.user else "")
        await interaction.response.send_message(embed=embed, view=HelpView())


async def setup(bot: commands.Bot):
    await bot.add_cog(Help(bot))
