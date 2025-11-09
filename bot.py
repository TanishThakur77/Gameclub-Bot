import discord
from discord import app_commands
from discord.ext import commands
from flask import Flask
import threading
import os

TOKEN = os.getenv("TOKEN")  # your Railway variable name
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ---- Keep-alive Flask ----
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run():
    app.run(host="0.0.0.0", port=8080)

def keep_alive():
    t = threading.Thread(target=run)
    t.start()

# ---- Slash Commands ----
@tree.command(name="ping", description="Check if the bot is alive.")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Pong! The bot is active and responding.", ephemeral=True)

@tree.command(name="i2c", description="Convert INR to USD")
async def i2c(interaction: discord.Interaction, amount: float):
    converted = amount / 83.0
    await interaction.response.send_message(f"💱 ₹{amount} = ${converted:.2f}", ephemeral=True)

@tree.command(name="c2i", description="Convert USD to INR")
async def c2i(interaction: discord.Interaction, amount: float):
    converted = amount * 83.0
    await interaction.response.send_message(f"💱 ${amount} = ₹{converted:.2f}", ephemeral=True)

# ---- Ready Event ----
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    try:
        synced = await tree.sync()  # 🌍 Global sync
        print(f"✅ Synced {len(synced)} global commands: {[cmd.name for cmd in synced]}")
        await bot.change_presence(activity=discord.Game("💱 Currency Converter Active"))
        print("🟢 Bot is online and ready!")
    except Exception as e:
        print(f"⚠️ Sync failed: {e}")

# ---- Run ----
keep_alive()
bot.run(TOKEN)

