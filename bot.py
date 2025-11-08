# bot.py
import os
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta, timezone

# ---------- CONFIG ----------
I2C_RATE = 95             # Crypto → INR
C2I_RATE_LOW = 91.0       # USD < 100
C2I_RATE_HIGH = 91.5      # USD >= 100
C2I_THRESHOLD = 100.0
GUILD_ID = 785743682334752768  # Your Discord server ID
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
GUILD = discord.Object(id=GUILD_ID)

@app_commands.command(name="i2c", description="Convert Crypto (USD) → INR")
@app_commands.describe(crypto_usd="Amount of crypto in USD")
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
    embed.add_field(name=f"⚖️ Rate used: ÷ {I2C_RATE}", value="\u200b", inline=False)
    embed.add_field(name="💸 You Pay (INR)", value=f"**₹ {inr_str}**", inline=True)
    embed.add_field(name="🔗 You Receive (Crypto)", value=f"**{crypto_str}**", inline=True)
    embed.set_footer(text=f"Time (IST): {ist_formatted}")

    await interaction.response.send_message(embed=embed)

@app_commands.command(name="c2i", description="Convert USD → INR")
@app_commands.describe(usd_amount="Amount in USD")
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

# ---------- Rate setting (admin only) ----------
@app_commands.command(name="setrate", description="Set conversion rates (Admin only)")
@app_commands.describe(command_name="Command to set rate for (i2c/c2i)",
                       new_rate="New rate value")
async def setrate(interaction: discord.Interaction, command_name: str, new_rate: float):
    # Check if user has admin (Manage Guild) permission
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("❌ You need admin privileges to use this.", ephemeral=True)
        return

    global I2C_RATE, C2I_RATE_LOW, C2I_RATE_HIGH

    if command_name.lower() == "i2c":
        I2C_RATE = new_rate
        await interaction.response.send_message(f"✅ I2C rate updated to {new_rate}")
    elif command_name.lower() == "c2i":
        # For simplicity, change both low/high same value
        C2I_RATE_LOW = C2I_RATE_HIGH = new_rate
        await interaction.response.send_message(f"✅ C2I rate updated to {new_rate}")
    else:
        await interaction.response.send_message("❌ Invalid command name. Use `i2c` or `c2i`.", ephemeral=True)

# ---------- Bot Events ----------
@bot.event
async def on_ready():
    # Clear old guild commands & sync fresh ones
    await bot.tree.clear_commands(guild=GUILD)
    await bot.tree.add_command(i2c, guild=GUILD)
    await bot.tree.add_command(c2i, guild=GUILD)
    await bot.tree.add_command(setrate, guild=GUILD)
    await bot.tree.sync(guild=GUILD)

    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    print("🔹 Slash commands cleared and synced for guild.")

# ---------- Run Bot ----------
token = os.environ.get("TOKEN")
if not token:
    print("ERROR: No token found. Set TOKEN in environment variables.")
else:
    bot.run(token)
