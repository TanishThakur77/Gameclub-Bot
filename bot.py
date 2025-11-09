import os
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta, timezone
from flask import Flask
from threading import Thread

# ---------------- CONFIG ----------------
GUILD_ID = 785743682334752768  # Replace with your Discord Server ID
I2C_RATE = 95.0                # Crypto → INR
C2I_RATE_LOW = 91.0            # USD < 100
C2I_RATE_HIGH = 91.5           # USD ≥ 100
C2I_THRESHOLD = 100.0
IST = timezone(timedelta(hours=5, minutes=30))
# ----------------------------------------

# ---------- KEEP-ALIVE WEB SERVER ----------
app = Flask('')

@app.route('/')
def home():
    return "✅ The Gameclub Bot is alive and running on Railway!"

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
guild = discord.Object(id=GUILD_ID)

# ---------- HELPER FUNCTIONS ----------
def pretty_num(value: float) -> str:
    """Format a number with commas and decimals."""
    return f"{value:,.2f}".rstrip('0').rstrip('.') if '.' in f"{value:,.2f}" else f"{int(value):,}"

def pick_color(amount: float) -> discord.Color:
    """Color code based on amount."""
    if amount < 500:
        return discord.Color.green()
    elif amount < 2000:
        return discord.Color.blue()
    return discord.Color.gold()

# ---------- /PING ----------
@app_commands.command(name="ping", description="Check bot latency and uptime")
async def ping(interaction: discord.Interaction):
    latency = bot.latency * 1000
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"Latency: **{latency:.2f} ms**",
        color=discord.Color.green(),
        timestamp=datetime.now(tz=IST)
    )
    embed.set_footer(text=datetime.now(tz=IST).strftime("Time (IST): %I:%M %p, %d %b %Y"))
    await interaction.response.send_message(embed=embed)

# ---------- /I2C ----------
@app_commands.command(name="i2c", description="Convert Crypto USD → INR")
@app_commands.describe(crypto_usd="Enter the crypto amount in USD")
async def i2c(interaction: discord.Interaction, crypto_usd: float):
    try:
        await interaction.response.defer(thinking=True)
        inr_amount = crypto_usd * I2C_RATE
        embed = discord.Embed(
            title=f"💱 Crypto → INR | Rate: ₹{I2C_RATE}",
            color=pick_color(inr_amount),
            timestamp=datetime.now(tz=IST)
        )
        embed.add_field(name="💸 You Pay (INR)", value=f"**₹ {pretty_num(inr_amount)}**", inline=True)
        embed.add_field(name="🔗 You Receive (Crypto USD)", value=f"**$ {pretty_num(crypto_usd)}**", inline=True)
        embed.set_footer(text=datetime.now(tz=IST).strftime("Time (IST): %I:%M %p, %d %b %Y"))
        await interaction.followup.send(embed=embed)
    except Exception as e:
        print(f"❌ /i2c error: {e}")
        await interaction.followup.send("❌ Something went wrong.", ephemeral=True)

# ---------- /C2I ----------
@app_commands.command(name="c2i", description="Convert Client USD → INR")
@app_commands.describe(usd_amount="Enter the client amount in USD")
async def c2i(interaction: discord.Interaction, usd_amount: float):
    try:
        await interaction.response.defer(thinking=True)
        rate = C2I_RATE_LOW if usd_amount < C2I_THRESHOLD else C2I_RATE_HIGH
        inr_amount = usd_amount * rate
        embed = discord.Embed(
            title="💸 USD → INR Conversion",
            description="Conversion based on client threshold",
            color=pick_color(inr_amount),
            timestamp=datetime.now(tz=IST)
        )
        embed.add_field(name="💰 You Pay (USD)", value=f"**$ {pretty_num(usd_amount)}**", inline=True)
        embed.add_field(name="🇮🇳 You Receive (INR)", value=f"**₹ {pretty_num(inr_amount)}**", inline=True)
        embed.add_field(name="⚖️ Rate Used", value=f"**₹{rate:g} per $**", inline=False)
        embed.set_footer(text=f"Threshold: ${C2I_THRESHOLD} | Time (IST): {datetime.now(tz=IST).strftime('%I:%M %p, %d %b %Y')}")
        await interaction.followup.send(embed=embed)
    except Exception as e:
        print(f"❌ /c2i error: {e}")
        await interaction.followup.send("❌ Something went wrong.", ephemeral=True)

# ---------- ON_READY ----------
@bot.event
async def on_ready():
   @bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    await bot.change_presence(status=discord.Status.online, activity=discord.Game("Syncing Commands..."))

    try:
        # Clear any previous commands (optional safety)
        bot.tree.clear_commands(guild=guild)

        # Add all commands again
        bot.tree.add_command(ping)
        bot.tree.add_command(i2c)
        bot.tree.add_command(c2i)

        # Now sync them
        synced = await bot.tree.sync(guild=guild)
        print(f"🔹 Force-synced {len(synced)} command(s) for guild {guild.id}")

        if len(synced) == 0:
            print("⚠️ No commands were registered! Check TOKEN, intents, or permissions.")
        else:
            for cmd in synced:
                print(f"✅ Registered: /{cmd.name}")

        await bot.change_presence(status=discord.Status.online, activity=discord.Game("USD ⇄ INR Converter 💱"))
        print("🟢 Bot is online and ready!")
    except Exception as e:
        print(f"⚠️ Command sync failed: {e}")

# ---------- RUN ----------
if __name__ == "__main__":
    keep_alive()
    token = os.getenv("TOKEN")
    if not token:
        print("❌ ERROR: TOKEN not found in environment variables.")
    else:
        print("🚀 Starting The Gameclub Bot...")
        bot.run(token)
