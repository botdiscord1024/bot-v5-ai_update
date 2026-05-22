import discord
from discord.ext import commands
import os
import asyncio
import threading
from utils import load

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)
bot.cached_data = {'levels':{},'counting':{},'smashkarts':{},'story':{}}

def refresh_bot_cache():
    bot.cached_data['levels']     = load('levels.json')
    bot.cached_data['counting']   = load('counting.json')
    bot.cached_data['smashkarts'] = load('smashkarts.json')
    bot.cached_data['story']      = load('story.json')

# Make refresh accessible globally
import builtins
builtins.refresh_bot_cache = refresh_bot_cache

COGS = ['cogs.moderation', 'cogs.leveling', 'cogs.counting',
        'cogs.story', 'cogs.games', 'cogs.smashkarts', 'cogs.ai_assistant']
@bot.event
async def on_ready():
    print(f"✅ {bot.user} is online!")
    refresh_bot_cache()
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash commands")
    except Exception as e:
        print(f"❌ Sync error: {e}")
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.playing, name="/help 🎮")
    )

async def start_bot():
    async with bot:
        for cog in COGS:
            try:
                await bot.load_extension(cog)
                print(f"✅ Loaded {cog}")
            except Exception as e:
                print(f"❌ Failed to load {cog}: {e}")
        TOKEN = os.environ.get('BOT_TOKEN')
        if not TOKEN:
            print("❌ BOT_TOKEN not set!")
            return
        await bot.start(TOKEN)

def run_bot():
    # Create a brand new event loop for the bot thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(start_bot())
    finally:
        loop.close()

# Start bot in its own thread with its own event loop
bot_thread = threading.Thread(target=run_bot, daemon=True)
bot_thread.start()

# Flask runs in main thread — Render detects the port
from dashboard import app
app.config['BOT'] = bot
port = int(os.environ.get('PORT', 5000))
print(f"🌐 Dashboard on port {port}")
app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
