# bot.py
import os
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta, timezone

# ---------------- CONFIG ----------------
I2C_RATE = 95             # Crypto → INR
C2I_RATE_LOW = 91.0       # USD < 100
C2I_RATE_HIGH = 91.5      # USD >= 100
C2I_THRESHOLD = 100.0

GUILD_ID = 785743682334752768  # Your server ID here
GUILD = discord.Object(id=GUILD_ID)

# ----------------------------------------

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='.', intents=intents)

IST = timezone(timedelta(hours=5, minutes=30))

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

# ---------- Bot Ready ----------
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    # Sync slash commands for your guild
    await bot.tree.sync(guild=GUILD)
    print("🔹 Slash commands synced for guild.")

# ---------- I2C Slash Command ----------
@bot.tree.command(name="i2c", description="Convert crypto USD → INR", guild=GUILD)
@app_commands.describe(crypto_usd="Amount in USD for crypto")
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
        title=f"💱 Crypto → INR | Rate: ÷ {I2C_RATE}",
        color=color,
        timestamp=ist_now
    )
    embed.add_field(name="💸 You Pay (INR)", value=f"**₹ {inr_str}**", inline=True)
    embed.add_field(name="🔗 You Receive (Crypto USD)", value=f"**{crypto_str}**", inline=True)
    embed.set_footer(text=f"Time (IST): {ist_formatted}")

    await interaction.response.send_message(embed=embed)

# ---------- C2I Slash Command ----------
@bot.tree.command(name="c2i", description="Convert crypto USD → INR for clients", guild=GUILD)
@app_commands.describe(usd_amount="Amount in USD")
async def c2i(interaction: discord.Interaction, usd_amount: float):
    rate = C2I_RATE_LOW if usd_amount < C2I_THRESHOLD else C2I_RATE_HIGH
    inr_amount = usd_amount * rate

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

# ---------- Error Handling ----------
@i2c.error
@c2i.error
async def conversion_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.MissingRequiredArgument):
        await interaction.response.send_message("❗ Missing argument.", ephemeral=True)
    elif isinstance(error, app_commands.TransformError):
        await interaction.response.send_message("❗ Please enter a valid number.", ephemeral=True)
    else:
        await interaction.response.send_message("❌ An error occurred. Try again.", ephemeral=True)

# ---------- Run Bot ----------
token = os.environ.get("TOKEN")
if not token:
    print("ERROR: No token found. Set TOKEN in Railway Environment Variables.")
else:
    bot.run(token)
