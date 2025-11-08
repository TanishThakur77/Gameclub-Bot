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

GUILD_ID = 785743682334752768  # Replace with your server ID
MOD_ROLE_NAME = "Mods"          # Role allowed to change rates
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

# ---------- Bot Events ----------
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    guild = discord.Object(id=GUILD_ID)
    await bot.tree.sync(guild=guild)
    print("🔹 Slash commands synced for guild.")

# ---------- Slash Commands ----------
GUILD = discord.Object(id=GUILD_ID)

# I2C: INR → Crypto
@bot.tree.command(name="i2c", description="Convert INR to crypto (measured in USD)")
@app_commands.describe(amount="Amount you pay in INR")
async def i2c(interaction: discord.Interaction, amount: float):
    crypto_amount = amount / I2C_RATE
    color = pick_color(amount)
    ist_now = datetime.now(tz=IST)
    ist_formatted = ist_now.strftime("%I:%M %p, %d %b %Y")

    embed = discord.Embed(
        title=f"💱 INR → Crypto Conversion (Rate ÷ {I2C_RATE})",
        color=color,
        timestamp=ist_now
    )
    embed.add_field(name="💸 You Pay (INR)", value=f"**₹ {pretty_num(amount)}**", inline=True)
    embed.add_field(name="🔗 You Receive (Crypto USD)", value=f"**{pretty_num(crypto_amount)}**", inline=True)
    embed.set_footer(text=f"Time (IST): {ist_formatted}")

    await interaction.response.send_message(embed=embed)

# C2I: Crypto → INR
@bot.tree.command(name="c2i", description="Convert crypto USD → INR")
@app_commands.describe(amount="Amount in crypto USD")
async def c2i(interaction: discord.Interaction, amount: float):
    rate = C2I_RATE_LOW if amount < C2I_THRESHOLD else C2I_RATE_HIGH
    inr_amount = amount * rate
    color = pick_color(inr_amount)
    ist_now = datetime.now(tz=IST)
    ist_formatted = ist_now.strftime("%I:%M %p, %d %b %Y")

    embed = discord.Embed(
        title=f"💸 Crypto USD → INR Conversion (Rate × {rate})",
        color=color,
        timestamp=ist_now
    )
    embed.add_field(name="💰 You Pay (Crypto USD)", value=f"**$ {pretty_num(amount)}**", inline=True)
    embed.add_field(name="🇮🇳 You Receive (INR)", value=f"**₹ {pretty_num(inr_amount)}**", inline=True)
    embed.set_footer(text=f"Time (IST): {ist_formatted}")

    await interaction.response.send_message(embed=embed)

# Set rate command
@bot.tree.command(name="setrate", description="Set conversion rates (admin only)")
@app_commands.describe(type="Type: i2c or c2i", rate="New rate value")
async def setrate(interaction: discord.Interaction, type: str, rate: float):
    # Check for admin or Mods role
    if not (interaction.user.guild_permissions.administrator or any(role.name == MOD_ROLE_NAME for role in interaction.user.roles)):
        await interaction.response.send_message("❌ You do not have permission to change rates.", ephemeral=True)
        return

    global I2C_RATE, C2I_RATE_LOW, C2I_RATE_HIGH

    if type.lower() == "i2c":
        I2C_RATE = rate
        await interaction.response.send_message(f"✅ I2C rate updated to {I2C_RATE}", ephemeral=True)
    elif type.lower() == "c2i":
        C2I_RATE_LOW = rate if C2I_RATE_LOW < C2I_THRESHOLD else C2I_RATE_LOW
        C2I_RATE_HIGH = rate if C2I_RATE_HIGH >= C2I_THRESHOLD else C2I_RATE_HIGH
        await interaction.response.send_message(f"✅ C2I rate updated to {rate}", ephemeral=True)
    else:
        await interaction.response.send_message("❌ Invalid type. Use `i2c` or `c2i`.", ephemeral=True)

# ---------- Run Bot ----------
token = os.environ.get("TOKEN")
if not token:
    print("ERROR: No token found. Set TOKEN in environment variables.")
else:
    bot.run(token)
