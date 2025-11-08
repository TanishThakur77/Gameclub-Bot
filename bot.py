# bot.py
import os
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta, timezone

# ---------- CONFIG ----------
I2C_RATE = 95             # Crypto → INR multiplier
C2I_RATE_LOW = 91.0       # USD < 100
C2I_RATE_HIGH = 91.5      # USD >= 100
C2I_THRESHOLD = 100.0
MOD_ROLE_NAME = "Mods"     # Role allowed to change rates
GUILD_ID = 785743682334752768  # Replace with your server ID
# ----------------------------

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='.', intents=intents)
GUILD = discord.Object(id=GUILD_ID)

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

def is_mod(interaction: discord.Interaction):
    role_names = [role.name for role in interaction.user.roles]
    return MOD_ROLE_NAME in role_names or interaction.user.guild_permissions.administrator

# ---------- Bot Events ----------
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    await bot.tree.sync(guild=GUILD)  # Instant guild slash commands

# ---------- Slash Commands ----------
@bot.tree.command(name="i2c", description="Convert Crypto (USD value) → INR", guild=GUILD)
@app_commands.describe(crypto_usd="Enter the crypto value in USD")
async def i2c(interaction: discord.Interaction, crypto_usd: float):
    inr_amount = crypto_usd * I2C_RATE
    crypto_str = pretty_num(crypto_usd)
    inr_str = pretty_num(inr_amount)
    color = pick_color(inr_amount)
    ist_now = datetime.now(tz=IST)
    ist_formatted = ist_now.strftime("%I:%M %p, %d %b %Y")

    embed = discord.Embed(
        title=f"💱 Crypto → INR Conversion (Rate × {I2C_RATE})",
        color=color,
        timestamp=ist_now
    )
    embed.add_field(name="💸 You Pay (INR)", value=f"**₹ {inr_str}**", inline=True)
    embed.add_field(name="🔗 You Receive (Crypto)", value=f"**{crypto_str}**", inline=True)

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="c2i", description="Convert USD → INR", guild=GUILD)
@app_commands.describe(usd_amount="Enter USD amount")
async def c2i(interaction: discord.Interaction, usd_amount: float):
    rate = C2I_RATE_LOW if usd_amount < C2I_THRESHOLD else C2I_RATE_HIGH
    inr_amount = usd_amount * rate
    usd_str = pretty_num(usd_amount)
    inr_str = pretty_num(inr_amount)
    color = pick_color(inr_amount)
    ist_now = datetime.now(tz=IST)
    ist_formatted = ist_now.strftime("%I:%M %p, %d %b %Y")

    embed = discord.Embed(
        title=f"💸 USD → INR Conversion (Rate × {rate})",
        description="Conversion based on amount threshold",
        color=color,
        timestamp=ist_now
    )
    embed.add_field(name="💰 You Pay (USD)", value=f"**$ {usd_str}**", inline=True)
    embed.add_field(name="🇮🇳 You Receive (INR)", value=f"**₹ {inr_str}**", inline=True)

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="setrate", description="Set new conversion rate for I2C or C2I", guild=GUILD)
@app_commands.describe(command_type="i2c or c2i", new_rate="New rate value")
async def setrate(interaction: discord.Interaction, command_type: str, new_rate: float):
    if not is_mod(interaction):
        await interaction.response.send_message("❌ You don't have permission to change rates.", ephemeral=True)
        return

    global I2C_RATE, C2I_RATE_LOW, C2I_RATE_HIGH

    if command_type.lower() == "i2c":
        I2C_RATE = new_rate
        await interaction.response.send_message(f"✅ I2C rate updated to **{new_rate}**")
    elif command_type.lower() == "c2i":
        if new_rate < C2I_THRESHOLD:
            C2I_RATE_LOW = new_rate
            await interaction.response.send_message(f"✅ C2I rate for <$100 updated to **{new_rate}**")
        else:
            C2I_RATE_HIGH = new_rate
            await interaction.response.send_message(f"✅ C2I rate for ≥$100 updated to **{new_rate}**")
    else:
        await interaction.response.send_message("❌ Invalid command type. Use `i2c` or `c2i`.", ephemeral=True)

# ---------- Run Bot ----------
token = os.environ.get("TOKEN")  # Set your bot token in environment variables
if not token:
    print("ERROR: No token found. Set TOKEN in environment variables.")
else:
    bot.run(token)
