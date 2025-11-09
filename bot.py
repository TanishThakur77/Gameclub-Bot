import os
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta, timezone
from flask import Flask
from threading import Thread

# ---------------- CONFIG ----------------
I2C_RATE = 95.0             # Crypto → INR
C2I_RATE_LOW = 91.0         # USD < 100
C2I_RATE_HIGH = 91.5        # USD >= 100
C2I_THRESHOLD = 100.0
# ----------------------------------------

# ---------- Keep-Alive Web Server ----------
app = Flask('')

@app.route('/')
def home():
    return "✅ Gameclub Bot is alive and running on Railway!"

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
    """Format a number with commas and decimals."""
    if float(value).is_integer():
        return f"{int(value):,}"
    return f"{value:,.2f}"

def pick_color(amount: float) -> discord.Color:
    """Choose an embed color based on INR value."""
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
    await bot.change_presence(status=discord.Status.online, activity=discord.Game("💱 Converting USD ⇄ INR"))
    try:
        synced = await tree.sync()  # 🌍 Global sync
        print(f"🔹 Synced {len(synced)} global commands: {[cmd.name for cmd in synced]}")
        print("🟢 Bot is online and ready!")
    except Exception as e:
        print(f"⚠️ Command sync failed: {e}")

# ---------- /i2c Command ----------
@tree.command(name="i2c", description="Convert Crypto USD → INR")
@app_commands.describe(crypto_usd="Enter the crypto amount in USD")
async def i2c(interaction: discord.Interaction, crypto_usd: float):
    """Convert crypto USD to INR based on fixed rate."""
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
        await interaction.followup.send("❌ Something went wrong. Please try again.", ephemeral=True)

# ---------- /c2i Command ----------
@tree.command(name="c2i", description="Convert Client USD → INR")
@app_commands.describe(usd_amount="Enter the amount in USD")
async def c2i(interaction: discord.Interaction, usd_amount: float):
    """Convert client USD to INR using tiered rate."""
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
        await interaction.followup.send("❌ Something went wrong. Please try again.", ephemeral=True)

# ---------- Run Bot ----------
if __name__ == "__main__":
    keep_alive()  # Keeps Railway service awake
    token = os.getenv("TOKEN")
    if not token:
        print("❌ ERROR: TOKEN not found in environment variables.")
    else:
        print("🚀 Starting Gameclub Bot...")
        bot.run(token)


# ---- Run ----
keep_alive()
bot.run(TOKEN)

