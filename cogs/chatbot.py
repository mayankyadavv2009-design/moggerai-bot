import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, Literal
import re
from utils.claude_brain import ClaudeBrain, KeyRotator
from config import BOT_NAME, EMBED_COLOR_DJ, EMBED_COLOR_MAIN, EMBED_COLOR_ERROR


def split_message(text: str, max_len: int = 1950) -> list[str]:
    """Splits a long message cleanly into chunks without breaking words or exceeding Discord limit"""
    if not text:
        return [""]
    if len(text) <= max_len:
        return [text]
    
    chunks = []
    current_chunk = ""
    lines = text.split("\n")
    
    for line in lines:
        if len(current_chunk) + len(line) + 1 > max_len:
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = ""
            
            if len(line) > max_len:
                for i in range(0, len(line), max_len):
                    part = line[i:i+max_len]
                    if len(part) == max_len:
                        chunks.append(part)
                    else:
                        current_chunk = part + "\n"
            else:
                current_chunk = line + "\n"
        else:
            current_chunk += line + "\n"
            
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
        
    return chunks


class Chatbot(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _get_session_id(self, message: discord.Message) -> str:
        """Unique session ID per channel/user for contextual conversation memory"""
        if isinstance(message.channel, discord.DMChannel):
            return f"dm_{message.author.id}"
        return f"guild_{message.guild.id}_chan_{message.channel.id}_user_{message.author.id}"

    # ------------------- Natural Conversational Message Listener -------------------
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        guild_id = message.guild.id if message.guild else 0
        channel_name = message.channel.name if hasattr(message.channel, 'name') else "DM"
        
        # 🧠 Record & learn from EVERY Discord message in the channel
        from utils.server_memory import ServerMemoryManager
        ServerMemoryManager.record_message(
            guild_id=guild_id,
            channel_id=message.channel.id,
            channel_name=channel_name,
            user_id=message.author.id,
            user_name=message.author.display_name,
            message_text=message.content
        )

        is_dm = isinstance(message.channel, discord.DMChannel)
        is_mentioned = self.bot.user in message.mentions
        is_reply_to_bot = False

        if message.reference and message.reference.resolved:
            resolved = message.reference.resolved
            if isinstance(resolved, discord.Message) and resolved.author.id == self.bot.user.id:
                is_reply_to_bot = True

        # Only reply if explicitly mentioned, replied to, or in direct message
        if not (is_mentioned or is_reply_to_bot or is_dm):
            return

        # Strip bot mention from the prompt
        clean_content = message.content
        if self.bot.user:
            clean_content = re.sub(rf'<@!?{self.bot.user.id}>', '', clean_content).strip()

        # Ignore if prompt is completely empty or is a prefix command
        if not clean_content or clean_content.startswith(('!', '/', '$', '%', '&', '.')):
            return

        session_id = self._get_session_id(message)

        # 🧠 Build learned neural memory & channel context
        memory_context = ServerMemoryManager.build_neural_memory_prompt(
            guild_id=guild_id,
            channel_id=message.channel.id,
            user_id=message.author.id,
            user_name=message.author.display_name
        )

        full_prompt = clean_content
        if memory_context:
            full_prompt = f"{memory_context}\n\n[Message directed to you by {message.author.display_name}]:\n{clean_content}"

        try:
            async with message.channel.typing():
                response = await ClaudeBrain.generate_response(
                    session_id=session_id,
                    user_prompt=full_prompt,
                    user_name=message.author.display_name
                )
                
                chunks = split_message(response)
                for chunk in chunks:
                    await message.reply(chunk, mention_author=False)
        except Exception as e:
            print(f"[CHATBOT ERROR] {e}")

    # ------------------- Conversational Slash Commands -------------------
    @app_commands.command(name="ask", description="Talk to MoggerAI (Claude Fable 5 neural persona) about any topic, code, or music")
    @app_commands.describe(prompt="What would you like to ask or talk about?")
    async def ask_slash(self, interaction: discord.Interaction, prompt: str):
        await interaction.response.defer()
        session_id = f"guild_{interaction.guild_id}_user_{interaction.user.id}" if interaction.guild_id else f"dm_{interaction.user.id}"
        
        response = await ClaudeBrain.generate_response(
            session_id=session_id,
            user_prompt=prompt,
            user_name=interaction.user.display_name
        )
        
        chunks = split_message(response)
        await interaction.followup.send(chunks[0])
        for chunk in chunks[1:]:
            if interaction.channel:
                await interaction.channel.send(chunk)

    @app_commands.command(name="chat", description="Chat with MoggerAI with continuous conversational memory")
    @app_commands.describe(message="Your message to MoggerAI")
    async def chat_slash(self, interaction: discord.Interaction, message: str):
        await self.ask_slash(interaction, message)

    @app_commands.command(name="clearchat", description="Clear your conversation history with MoggerAI to start a fresh topic")
    async def clearchat_slash(self, interaction: discord.Interaction):
        session_id = f"guild_{interaction.guild_id}_user_{interaction.user.id}" if interaction.guild_id else f"dm_{interaction.user.id}"
        ClaudeBrain.clear_history(session_id)
        await interaction.response.send_message("🧹 **Conversation memory cleared!** Starting with a fresh context.", ephemeral=True)

    # ------------------- API Key Rotation Management Commands -------------------
    @app_commands.command(name="ai_keys", description="Manage Gemini API Key Rotation pool (add, list, remove, or clear keys)")
    @app_commands.describe(
        action="Action to perform on the key rotation pool",
        key="The API key(s) to add or index/key to remove (comma-separated for multiple)"
    )
    async def ai_keys_slash(
        self,
        interaction: discord.Interaction,
        action: Literal["list", "add", "remove", "clear"],
        key: Optional[str] = None
    ):
        if not interaction.user.guild_permissions.administrator and interaction.user.id != 864889563401814019:
            return await interaction.response.send_message("❌ Only server administrators can manage AI keys.", ephemeral=True)

        rotator = ClaudeBrain.get_key_rotator()

        if action == "list":
            report = rotator.get_status_report()
            embed = discord.Embed(
                title="🔑 MoggerAI Gemini Key Rotation Pool",
                description=f"**Total Keys in Rotation:** `{len(report)}`\n*Keys automatically rotate round-robin and auto-failover on rate limits (429)!*",
                color=EMBED_COLOR_DJ
            )
            if not report:
                embed.description += "\n\n⚠️ *No keys currently in rotation! Add keys with `/ai_keys action:add key:<your_key>`.*"
            else:
                key_list_str = ""
                for r in report:
                    key_list_str += f"`#{r['index']}` **`{r['masked']}`** • {r['status']}\n"
                embed.add_field(name="Active Key Pool", value=key_list_str, inline=False)
            
            embed.set_footer(text="MoggerAI Claude Brain • Automated Zero-Downtime Load Balancing")
            await interaction.response.send_message(embed=embed, ephemeral=True)

        elif action == "add":
            if not key:
                return await interaction.response.send_message("❌ Please provide a key to add (e.g. `AIzaSy...` or comma-separated).", ephemeral=True)
            
            new_keys = [k.strip() for k in key.replace(';', ',').replace('\n', ',').split(',') if k.strip()]
            all_keys = rotator.add_keys(new_keys)
            await interaction.response.send_message(
                f"✅ **Added `{len(new_keys)}` key(s) to rotation!** Total active keys in pool: `{len(all_keys)}`.\n"
                f"*MoggerAI will now load-balance and auto-rotate across all keys seamlessly!*",
                ephemeral=True
            )

        elif action == "remove":
            if not key:
                return await interaction.response.send_message("❌ Please provide the key or key # index to remove (e.g. `1` or `AIza...`).", ephemeral=True)
            
            success = rotator.remove_key(key)
            if success:
                await interaction.response.send_message(f"🗑️ Successfully removed key from rotation pool.", ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ Key `{key}` not found in rotation pool.", ephemeral=True)

        elif action == "clear":
            rotator.clear_all()
            await interaction.response.send_message("🧹 **Cleared all keys from rotation pool.**", ephemeral=True)

    # ------------------- Prefix Commands -------------------
    @commands.command(name="ask", aliases=["chat", "ai", "claude"])
    async def prefix_ask(self, ctx: commands.Context, *, prompt: str):
        session_id = f"guild_{ctx.guild.id}_user_{ctx.author.id}" if ctx.guild else f"dm_{ctx.author.id}"
        async with ctx.channel.typing():
            response = await ClaudeBrain.generate_response(
                session_id=session_id,
                user_prompt=prompt,
                user_name=ctx.author.display_name
            )
            chunks = split_message(response)
            for chunk in chunks:
                await ctx.reply(chunk, mention_author=False)

    @commands.command(name="clearchat", aliases=["resetchat", "wipechat"])
    async def prefix_clearchat(self, ctx: commands.Context):
        session_id = f"guild_{ctx.guild.id}_user_{ctx.author.id}" if ctx.guild else f"dm_{ctx.author.id}"
        ClaudeBrain.clear_history(session_id)
        await ctx.reply("🧹 **Conversation memory cleared!** Starting with a fresh context.", mention_author=False)

    @commands.command(name="addkey", aliases=["addkeys", "setkey"])
    @commands.has_permissions(administrator=True)
    async def prefix_addkey(self, ctx: commands.Context, *, keys: str):
        rotator = ClaudeBrain.get_key_rotator()
        new_keys = [k.strip() for k in keys.replace(';', ',').replace('\n', ',').split(',') if k.strip()]
        all_keys = rotator.add_keys(new_keys)
        try:
            await ctx.message.delete() # Security: delete message containing raw API keys
        except Exception:
            pass
        await ctx.send(f"✅ **Added `{len(new_keys)}` key(s) to rotation!** Total keys in pool: `{len(all_keys)}`.")

    @commands.command(name="listkeys", aliases=["keys", "keylist"])
    @commands.has_permissions(administrator=True)
    async def prefix_listkeys(self, ctx: commands.Context):
        rotator = ClaudeBrain.get_key_rotator()
        report = rotator.get_status_report()
        embed = discord.Embed(
            title="🔑 MoggerAI Gemini Key Rotation Pool",
            description=f"**Total Keys in Rotation:** `{len(report)}`\n*Keys automatically rotate round-robin and auto-failover on rate limits (429)!*",
            color=EMBED_COLOR_DJ
        )
        if not report:
            embed.description += "\n\n⚠️ *No keys in rotation! Add keys with `!addkey <your_key>`.*"
        else:
            key_list_str = ""
            for r in report:
                key_list_str += f"`#{r['index']}` **`{r['masked']}`** • {r['status']}\n"
            embed.add_field(name="Active Key Pool", value=key_list_str, inline=False)
        
        await ctx.send(embed=embed)

    @commands.command(name="delkey", aliases=["removekey"])
    @commands.has_permissions(administrator=True)
    async def prefix_delkey(self, ctx: commands.Context, identifier: str):
        rotator = ClaudeBrain.get_key_rotator()
        if rotator.remove_key(identifier):
            await ctx.send(f"🗑️ Removed key `{identifier}` from rotation.")
        else:
            await ctx.send(f"❌ Key `{identifier}` not found.")


async def setup(bot: commands.Bot):
    await bot.add_cog(Chatbot(bot))
