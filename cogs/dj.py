import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
from utils.database import Database
from config import EMBED_COLOR_DJ, EMBED_COLOR_MAIN, BOT_NAME, save_youtube_status_url, YOUTUBE_STATUS_URL
import config

class DJ(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.skip_votes = {} # guild_id -> set(user_ids)

    @app_commands.command(name="dj_setrole", description="Configure DJ Role required for server audio settings")
    @app_commands.describe(role="The role to grant DJ permissions")
    @app_commands.checks.has_permissions(administrator=True)
    async def dj_setrole(self, interaction: discord.Interaction, role: discord.Role):
        Database.update_guild_setting(interaction.guild_id, "dj_role_id", role.id)
        embed = discord.Embed(
            title="🎧 DJ Role Assigned",
            description=f"Successfully set {role.mention} as the official **RESONANCE DJ Role**.",
            color=EMBED_COLOR_DJ
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="dj_247", description="Toggle 24/7 mode (Bot stays connected in voice channel continuously)")
    @app_commands.describe(enabled="Enable or disable 24/7 stay-in-voice mode")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def dj_247(self, interaction: discord.Interaction, enabled: bool):
        Database.update_guild_setting(interaction.guild_id, "stay_247", 1 if enabled else 0)
        music_cog = self.bot.get_cog("Music")
        if music_cog:
            state = music_cog.get_state(interaction.guild_id)
            state.stay_247 = enabled

        status_str = "ENABLED 🟢" if enabled else "DISABLED 🔴"
        await interaction.response.send_message(f"📡 24/7 Voice Channel Stay Mode is now **{status_str}**.")

    @app_commands.command(name="dj_autoplay", description="Configure Spotify-style AI Autoplay recommendation mode")
    @app_commands.describe(
        enabled="Enable or disable autoplay",
        mode="Autoplay intelligence mode (smart = transition + taste + radio discovery)"
    )
    async def dj_autoplay(
        self,
        interaction: discord.Interaction,
        enabled: bool,
        mode: Optional[str] = "smart"
    ):
        Database.update_guild_setting(interaction.guild_id, "autoplay", 1 if enabled else 0)
        Database.update_guild_setting(interaction.guild_id, "autoplay_mode", mode)
        music_cog = self.bot.get_cog("Music")
        if music_cog:
            state = music_cog.get_state(interaction.guild_id)
            state.autoplay = enabled
            state.autoplay_mode = mode

        status_str = f"ENABLED 🤖 (Mode: `{mode.upper()}`)" if enabled else "DISABLED 🚫"
        embed = discord.Embed(
            title="📻 AI Autoplay Engine Configuration",
            description=(
                f"Status: **{status_str}**\n\n"
                f"**Available Modes:**\n"
                f"• `smart`: Multi-tier Spotify-style (Transitions ➔ Listener Taste ➔ Radio)\n"
                f"• `transition`: Plays songs most frequently queued after current track\n"
                f"• `taste`: Prioritizes active voice room listeners' favorite music\n"
                f"• `radio`: Artist & track radio discovery mix\n"
            ),
            color=EMBED_COLOR_DJ
        )
        await interaction.response.send_message(embed=embed)

    @commands.command(name="autoplay", aliases=["dj_autoplay"])
    async def prefix_autoplay(self, ctx: commands.Context, enabled: Optional[str] = "on", mode: Optional[str] = "smart"):
        """Configure AI Autoplay (!autoplay on/off [smart|transition|taste|radio])"""
        is_on = enabled.lower() in ("on", "true", "1", "yes", "enable")
        Database.update_guild_setting(ctx.guild.id, "autoplay", 1 if is_on else 0)
        Database.update_guild_setting(ctx.guild.id, "autoplay_mode", mode)
        music_cog = self.bot.get_cog("Music")
        if music_cog:
            state = music_cog.get_state(ctx.guild.id)
            state.autoplay = is_on
            state.autoplay_mode = mode

        status_str = f"ENABLED 🤖 (`{mode.upper()}`)" if is_on else "DISABLED 🚫"
        await ctx.send(f"📻 Auto-play Recommendation Mode is now **{status_str}**.")

    @app_commands.command(name="voteskip", description="Vote to skip the current track (Requires 50% listener consensus)")
    async def voteskip(self, interaction: discord.Interaction):
        if not interaction.user.voice or not interaction.user.voice.channel:
            return await interaction.response.send_message("❌ You must be in the voice channel to vote skip!", ephemeral=True)

        channel = interaction.user.voice.channel
        listeners = [m for m in channel.members if not m.bot]
        if not listeners:
            return await interaction.response.send_message("❌ No listeners in channel.", ephemeral=True)

        guild_id = interaction.guild_id
        if guild_id not in self.skip_votes:
            self.skip_votes[guild_id] = set()

        self.skip_votes[guild_id].add(interaction.user.id)
        votes_count = len(self.skip_votes[guild_id])
        required_votes = (len(listeners) // 2) + 1

        if votes_count >= required_votes:
            self.skip_votes[guild_id].clear()
            music_cog = self.bot.get_cog("Music")
            if music_cog and music_cog.get_state(guild_id).voice_client:
                music_cog.get_state(guild_id).voice_client.stop()
            await interaction.response.send_message(f"🗳️ Vote Skip passed! (`{votes_count}/{required_votes}` votes). Skipping track...")
        else:
            await interaction.response.send_message(f"🗳️ Vote recorded! (`{votes_count}/{required_votes}` votes needed to skip).")

    @app_commands.command(name="status", description="View or change bot's live streaming presence & YouTube link")
    @app_commands.describe(title="Status activity title (e.g. '🔴 LIVE • RESONANCE APEX ⚡')", url="YouTube video/stream URL")
    async def status_cmd(self, interaction: discord.Interaction, title: Optional[str] = None, url: Optional[str] = None):
        if title or url:
            new_url, new_title = config.save_status(new_url=url, new_text=title)
            activity = discord.Streaming(name=new_title, url=new_url)
            await self.bot.change_presence(activity=activity, status=discord.Status.online)
            
            embed = discord.Embed(
                title="📡 Live Streaming Presence Updated",
                description=f"Successfully updated live stream status and saved to `.env`!\n\n**🏷️ Status Text:** `{new_title}`\n**🔗 Stream URL:** [{new_url}]({new_url})",
                color=EMBED_COLOR_MAIN
            )
            await interaction.response.send_message(embed=embed)
        else:
            embed = discord.Embed(
                title="📡 Active Live Streaming Presence",
                description=(
                    f"**🏷️ Current Title:** `{config.STATUS_TEXT}`\n"
                    f"**🔗 Stream URL:** [{config.YOUTUBE_STATUS_URL}]({config.YOUTUBE_STATUS_URL})\n\n"
                    f"💡 *To change: `/status title:<text> url:<youtube_link>` or visit `http://localhost:5000`*"
                ),
                color=EMBED_COLOR_MAIN
            )
            await interaction.response.send_message(embed=embed)

    @commands.command(name="status", aliases=["setstatus", "youtubestatus"])
    async def prefix_status_cmd(self, ctx: commands.Context, *, args: Optional[str] = None):
        """View or update bot's YouTube streaming status (e.g. !status 🔴 LIVE • RESONANCE | https://youtube.com/...)"""
        if args:
            url = None
            title = None
            for part in args.split():
                if part.startswith("http://") or part.startswith("https://"):
                    url = part
                    break
            
            if url:
                title_parts = [p for p in args.split() if p != url and p != "|"]
                title = " ".join(title_parts) if title_parts else None
            else:
                title = args
                
            new_url, new_title = config.save_status(new_url=url, new_text=title)
            activity = discord.Streaming(name=new_title, url=new_url)
            await self.bot.change_presence(activity=activity, status=discord.Status.online)
            
            embed = discord.Embed(
                title="📡 Live Streaming Presence Updated",
                description=f"Successfully updated live streaming presence!\n\n**🏷️ Status Text:** `{new_title}`\n**🔗 Stream URL:** [{new_url}]({new_url})",
                color=EMBED_COLOR_MAIN
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="📡 Active Live Streaming Presence",
                description=(
                    f"**🏷️ Current Title:** `{config.STATUS_TEXT}`\n"
                    f"**🔗 Stream URL:** [{config.YOUTUBE_STATUS_URL}]({config.YOUTUBE_STATUS_URL})\n\n"
                    f"💡 *To change: `{ctx.prefix}status <title> [youtube_url]` or `/status`*"
                ),
                color=EMBED_COLOR_MAIN
            )
            await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(DJ(bot))
