import os
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta, timezone
from flask import Flask
from threading import Thread

# ---------------- CONFIG ----------------
CONVERSION_RATE = 95.0  # divide or multiply by this rate
GUILD_ID = 785743682334752768  # Replace with your server ID
# ----------------------------------------

# ---------- Keep-Alive Web Server ----------
app = Flask('')

@app.route('/')
def home():
    return "✅ Gameclub Bot is alive and running!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# ---------- Discord Bot Setup ----------
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='.', intents=intents)
tree = bot.tree
IST = timezone(timedelta(hours=5, minutes=30))

# ---------- Helper Functions ----------
def pretty_num(value: float) -> str:
    """Format number with commas and two decimals."""
    if float(value).is_integer():
        return f"{int(value):,}"
    return f"{value:,.2f}"

def pick_color(amount: float) -> discord.Color:
    """Pick embed color based on value."""
    if amount < 500:
        return discord.Color.green()
    elif amount < 2000:
        return discord.Color.blue()
    else:
        return discord.Color.gold()

# ---------- On Ready ----------
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    await bot.change_presence(status=discord.Status.online, activity=discord.Game("💱 USD ⇄ INR"))
    try:
        synced = await tree.sync()
        print(f"🔹 Synced {len(synced)} global slash commands")
        print("🟢 Bot is online and ready!")
    except Exception as e:
        print(f"⚠️ Command sync failed: {e}")

# ---------- /ping Command ----------
@tree.command(name="ping", description="Check if the bot is alive.")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"Latency: {latency} ms",
        color=discord.Color.green(),
        timestamp=datetime.now(tz=IST)
    )
    await interaction.response.send_message(embed=embed)

# ---------- /i2c Command (Divide by 95) ----------
@tree.command(name="i2c", description="Convert INR → USD (Divide by 95).")
@app_commands.describe(amount="Enter the amount in INR")
async def i2c(interaction: discord.Interaction, amount: float):
    try:
        await interaction.response.defer(thinking=True)
        usd = amount / CONVERSION_RATE

        embed = discord.Embed(
            title="💱 INR → USD Conversion",
            color=pick_color(amount),
            timestamp=datetime.now(tz=IST)
        )
        embed.add_field(name="💸 Amount in INR", value=f"**₹ {pretty_num(amount)}**", inline=True)
        embed.add_field(name="💵 Converted USD", value=f"**$ {pretty_num(usd)}**", inline=True)
        embed.set_footer(text=f"Rate: 1 USD = ₹{CONVERSION_RATE} | Time (IST): {datetime.now(tz=IST).strftime('%I:%M %p, %d %b %Y')}")

        await interaction.followup.send(embed=embed)
    except Exception as e:
        print(f"❌ /i2c error: {e}")
        await interaction.followup.send("❌ Something went wrong. Please try again.", ephemeral=True)

# ---------- /c2i Command (Multiply by 95) ----------
@tree.command(name="c2i", description="Convert USD → INR (Multiply by 95).")
@app_commands.describe(amount="Enter the amount in USD")
async def c2i(interaction: discord.Interaction, amount: float):
    try:
        await interaction.response.defer(thinking=True)
        inr = amount * CONVERSION_RATE

        embed = discord.Embed(
            title="💱 USD → INR Conversion",
            color=pick_color(inr),
            timestamp=datetime.now(tz=IST)
        )
        embed.add_field(name="💵 Amount in USD", value=f"**$ {pretty_num(amount)}**", inline=True)
        embed.add_field(name="💸 Converted INR", value=f"**₹ {pretty_num(inr)}**", inline=True)
        embed.set_footer(text=f"Rate: 1 USD = ₹{CONVERSION_RATE} | Time (IST): {datetime.now(tz=IST).strftime('%I:%M %p, %d %b %Y')}")

        await interaction.followup.send(embed=embed)
    except Exception as e:
        print(f"❌ /c2i error: {e}")
        await interaction.followup.send("❌ Something went wrong. Please try again.", ephemeral=True)

# ---------- Run Bot ----------
if __name__ == "__main__":
    keep_alive()  # Keeps Railway service awake
    TOKEN = os.environ.get("TOKEN")
    if not TOKEN:
        print("❌ ERROR: TOKEN not found in environment variables.")
    else:
        print("🚀 Starting Gameclub Bot...")
        bot.run(TOKEN)
