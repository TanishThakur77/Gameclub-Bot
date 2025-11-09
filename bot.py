import os
import discord
from discord import app_commands
from discord.ext import commands
from flask import Flask
from threading import Thread
from datetime import datetime, timedelta, timezone

# ---------- CONFIG ----------
GUILD_ID = 785743682334752768  # 🔹 Replace with your server's ID
IST = timezone(timedelta(hours=5, minutes=30))

# ---------- KEEP-ALIVE SERVER ----------
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Gameclub Bot is alive and connected to Railway!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# ---------- DISCORD BOT SETUP ----------
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='.', intents=intents)
GUILD = discord.Object(id=GUILD_ID)

# ---------- /ping COMMAND ----------
@app_commands.command(name="ping", description="Check if the bot is online and responding")
async def ping(interaction: discord.Interaction):
    """Test if bot is alive."""
    latency = bot.latency * 1000  # in milliseconds
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"Latency: **{latency:.2f} ms**",
        color=discord.Color.green(),
        timestamp=datetime.now(tz=IST)
    )
    await interaction.response.send_message(embed=embed)

# ---------- ON_READY EVENT ----------
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    await bot.change_presence(status=discord.Status.online, activity=discord.Game("Testing connection 🛰️"))

    try:
        # Clear any old commands and re-register /ping fresh
        bot.tree.clear_commands(guild=GUILD)
        bot.tree.add_command(ping)
        await bot.tree.sync(guild=GUILD)
        print(f"🔹 Slash commands synced successfully for guild {GUILD_ID}")
        print("🟢 Bot is online and ready to respond!")
    except Exception as e:
        print(f"⚠️ Command sync failed: {e}")

# ---------- RUN BOT ----------
if __name__ == "__main__":
    keep_alive()
    token = os.getenv("TOKEN")

    if not token:
        print("❌ ERROR: TOKEN not found in environment variables.")
    else:
        print("🚀 Starting Gameclub Bot...")
        bot.run(token)
