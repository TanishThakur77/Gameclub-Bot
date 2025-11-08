# bot.py
import os
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta, timezone

# ---------- CONFIG ----------
I2C_RATE = 95             # Crypto → INR multiplier
C2I_RATE_LOW = 91.0       # USD < 100
C2I_RATE_HIGH = 91.5      # USD >= 100
C2I_THRESHOLD = 100.0
GUILD_ID = 785743682334752768  # Your server ID
# ----------------------------

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='.', intents=intents)

# IST timezone
IST = timezone(timedelta(hours=5, minutes=30))

# ---------- Helpers ----------
def pretty_num(value):
    if float(value).is_integer():
        return f"{int(value):,}"
    return f"{value:,.2f}"

def pick_color(amount):
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
    guild = discord.Object(id=GUILD_ID)
    await bot.tree.sync(guild=guild)
    print("🔹 Slash commands synced for guild.")

# ---------- Slash Commands ----------
GUILD = discord.Object(id=GUILD_ID)

@bot.tree.command(name="i2c", description="Convert Crypto (USD) → INR", guild=GUILD)
@app_commands.describe(crypto_usd="Enter crypto value in USD")
async def i2c(interaction: discord.Interaction, crypto_usd: float):
    try:
        inr_amount = crypto_usd * I2C_RATE
    except:
        await interaction.response.send_message("❌ Something went wrong.", ephemeral=True)
        return

    crypto_str = pretty_num(crypto_usd)
    inr_str = pretty_num(inr_amount)
    color = pick_color(inr_amount)
    ist_now = datetime.now(tz=IST)
    ist_formatted = ist_now.strftime("%I:%M %p, %d %b %Y")

    embed = discord.Embed(
        title="💱 Crypto → INR Conversion",
        color=color,
        timestamp=ist_now
    )
    embed.add_field(name="⚖️ Rate used", value=f"÷ {I2C_RATE}", inline=False)
    embed.add_field(name="💸 You Pay (INR)", value=f"**₹ {inr_str}**", inline=True)
    embed.add_field(name="🔗 You Receive (Crypto)", value=f"**{crypto_str}**", inline=True)
    embed.set_footer(text=f"Time (IST): {ist_formatted}")

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="c2i", description="Convert USD → INR", guild=GUILD)
@app_commands.describe(usd_amount="Enter USD amount")
async def c2i(interaction: discord.Interaction, usd_amount: float):
    try:
        rate = C2I_RATE_LOW if usd_amount < C2I_THRESHOLD else C2I_RATE_HIGH
        inr_amount = usd_amount * rate
    except:
        await interaction.response.send_message("❌ Something went wrong.", ephemeral=True)
        return

    usd_str = pretty_num(usd_amount)
    inr_str = pretty_num(inr_amount)
    rate_str = f"{rate:g}"
    color = pick_color(inr_amount)
    ist_now = datetime.now(tz=IST)
    ist_formatted = ist_now.strftime("%I:%M %p, %d %b %Y")

    embed = discord.Embed(
        title="💸 USD → INR Conversion",
        description="Conversion based on amount threshold",
        color=color,
        timestamp=ist_now
    )
    embed.add_field(name="💰 You Pay (USD)", value=f"**$ {usd_str}**", inline=True)
    embed.add_field(name="🇮🇳 You Receive (INR)", value=f"**₹ {inr_str}**", inline=True)
    embed.add_field(name="⚖️ Rate used", value=f"**{rate_str} INR per $**", inline=False)
    embed.set_footer(text=f"Threshold: ${C2I_THRESHOLD} | Time (IST): {ist_formatted}")

    await interaction.response.send_message(embed=embed)

# ---------- Run bot ----------
token = os.environ.get("TOKEN")
if not token:
    print("ERROR: No token found. Set TOKEN in environment variables.")
else:
    bot.run(token)
