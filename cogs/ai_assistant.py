import discord
from discord.ext import commands
import aiohttp
import io
from utils import load, save, err, ok

class AIAssistant(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_guild_config(self, gid):
        return load('config.json').get(str(gid), {})

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        gid = str(message.guild.id)
        cfg = self.get_guild_config(gid)

        # 1. Check if AI module is globally enabled
        if not cfg.get('ai_enabled', True):
            return

        # 2. Check for replies or pings targeting the bot
        is_reply_to_bot = False
        if message.reference and message.reference.cached_message:
            if message.reference.cached_message.author.id == self.bot.user.id:
                is_reply_to_bot = True

        is_mentioning_bot = self.bot.user in message.mentions

        if (is_reply_to_bot or is_mentioning_bot) and cfg.get('ai_reply_on_mention', True):
            ctx_content = message.content.lower()
            
            # Default fallback English response
            response = "?? Hello! I am your AI assistant. My dashboard features are fully operational! ??"
            
            # Smart conversational triggers
            if "level" in ctx_content or "rank" in ctx_content or "xp" in ctx_content:
                response = "?? The level system is up and running! Check your position on our Web Dashboard leaderboards."
            elif "hello" in ctx_content or "hi " in ctx_content or "hey" in ctx_content:
                response = f"Greetings, {message.author.mention}! How can I assist you on the server today? ??"
            elif "help" in ctx_content:
                response = "?? Need help? Use our slash commands or visit the dashboard to manage server features!"

            try:
                await message.reply(response)
            except:
                pass

        # 3. Automated Smart Emoji Reactions (English triggers)
        if cfg.get('ai_auto_emojis', True):
            content = message.content.lower()
            if any(word in content for word in ["gg", "win", "nice", "up", "level", "awesome"]):
                try: await message.add_reaction("??")
                except: pass
            elif any(word in content for word in ["lol", "xd", "haha", "lmao", "funny"]):
                try: await message.add_reaction("??")
                except: pass

    # -- Command to output external custom web emoji -----------------
    @discord.app_commands.command(name="ai_emoji", description="Use an external custom emoji from the web dashboard")
    @discord.app_commands.describe(name="The custom name of the emoji assigned on the dashboard")
    async def ai_emoji(self, interaction: discord.Interaction, name: str):
        gid = str(interaction.guild.id)
        cfg = self.get_guild_config(gid)
        custom_emojis = cfg.get('custom_external_emojis', {})

        if name not in custom_emojis:
            return await interaction.response.send_message(embed=err(f"Emoji named `:{name}:` was not found on the web dashboard!"), ephemeral=True)

        await interaction.response.defer()
        url = custom_emojis[name]

        # Fetch image from web link and post it as a file payload bypass
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    img_data = await resp.read()
                    img_file = discord.File(io.BytesIO(img_data), filename=f"{name}.png")
                    await interaction.followup.send(file=img_file)
                else:
                    await interaction.followup.send(embed=err("Failed to download the custom emoji asset from the provided link."), ephemeral=True)

async def setup(bot):
    await bot.add_cog(AIAssistant(bot))