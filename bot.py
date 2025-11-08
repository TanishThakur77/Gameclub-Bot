# bot.py
import os
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta, timezone

# ---------- CONFIG ----------
I2C_RATE = 95               # INR → Crypto
C2I_RATE_LOW = 91.0         # USD < 100
C2I_RATE_HIGH = 91.5        # USD >= 100
C2I_THRESHOLD = 100.0

GUILD_ID = 785743682334752768  # Your server ID
GUILD = discord.Object(id=GUILD_ID)
# ----------------------------

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=".", intents=intents)

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

# ---------- Slash Commands ----------
@bot.tree.command(name="i2c", description="Convert INR → Crypto")
@app_commands.describe(amount="Amount in INR you want to pay")
async def i2c(interaction: discord.Interaction, amount: float):
    try:
        crypto_amount = amount / I2C_RATE
    except:
        await interaction.response.send_message("❌ Something went wrong.", ephemeral=True)
        return

    inr_str = f"**₹ {pretty_num(amount)}**"
    crypto_str = f"**{pretty_num(crypto_amount)}**"
    color = pick_color(amount)

    embed = discord.Embed(
        title="💱 INR → Crypto Conversion",
        color=color
    )
    embed.add_field(name=f"⚖️ Rate used: ÷ {I2C_RATE}", value=inr_str, inline=True)
    embed.add_field(name="🔗 You Receive (Crypto)", value=crypto_str, inline=True)

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="c2i", description="Convert Crypto (USD) → INR")
@app_commands.describe(usd_amount="Amount of crypto in USD")
async def c2i(interaction: discord.Interaction, usd_amount: float):
    try:
        rate = C2I_RATE_LOW if usd_amount < C2I_THRESHOLD else C2I_RATE_HIGH
        inr_amount = usd_amount * rate
    except:
        await interaction.response.send_message("❌ Something went wrong.", ephemeral=True)
        return

    usd_str = f"**$ {pretty_num(usd_amount)}**"
    inr_str = f"**₹ {pretty_num(inr_amount)}**"
    rate_str = f"{rate:g}"
    color = pick_color(inr_amount)

    embed = discord.Embed(
        title="💸 Crypto (USD) → INR Conversion",
        color=color
    )
    embed.add_field(name="💰 You Pay (Crypto in USD)", value=usd_str, inline=True)
    embed.add_field(name="🇮🇳 You Receive (INR)", value=inr_str, inline=True)
    embed.add_field(name="⚖️ Rate used", value=f"{rate_str} INR per $", inline=False)

    await interaction.response.send_message(embed=embed)

# ---------- Events ----------
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    await bot.tree.sync(guild=GUILD)
    print("🌐 Slash commands synced!")

# ---------- Run bot ----------
token = os.environ.get("TOKEN")
if not token:
    print("ERROR: No token found. Set TOKEN in environment variables.")
else:
    bot.run(token)
