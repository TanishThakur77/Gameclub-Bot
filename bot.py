import os
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta, timezone

# ---------------- CONFIG ----------------
I2C_RATE = 95.0             # Crypto → INR
C2I_RATE_LOW = 91.0         # USD < 100
C2I_RATE_HIGH = 91.5        # USD >= 100
C2I_THRESHOLD = 100.0

GUILD_ID = 785743682334752768  # 🔹 Your Discord server (guild) ID
# ----------------------------------------

# ---------- Bot Setup ----------
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='.', intents=intents)
GUILD = discord.Object(id=GUILD_ID)

# ---------- Timezone ----------
IST = timezone(timedelta(hours=5, minutes=30))

# ---------- Helper Functions ----------
def pretty_num(value: float) -> str:
    """Format a number with commas and 2 decimals if needed."""
    if float(value).is_integer():
        return f"{int(value):,}"
    return f"{value:,.2f}"

def pick_color(amount: float) -> discord.Color:
    """Pick embed color based on INR amount."""
    if amount < 500:
        return discord.Color.green()
    elif amount < 2000:
        return discord.Color.blue()
    else:
        return discord.Color.gold()

# ---------- On Bot Ready ----------
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    try:
        await bot.tree.sync(guild=GUILD)
        print(f"🔹 Slash commands synced successfully for guild {GUILD_ID}")
    except Exception as e:
        print(f"⚠️ Failed to sync slash commands: {e}")

# ---------- /i2c Command ----------
@bot.tree.command(name="i2c", description="Convert Crypto USD → INR", guild=GUILD)
@app_commands.describe(crypto_usd="Enter the crypto amount in USD")
async def i2c(interaction: discord.Interaction, crypto_usd: float):
    try:
        inr_amount = crypto_usd * I2C_RATE
    except Exception:
        await interaction.response.send_message("❌ Something went wrong. Please try again.", ephemeral=True)
        return

    embed = discord.Embed(
        title=f"💱 Crypto → INR | Rate: ₹{I2C_RATE}",
        color=pick_color(inr_amount),
        timestamp=datetime.now(tz=IST)
    )
    embed.add_field(name="💸 You Pay (INR)", value=f"**₹ {pretty_num(inr_amount)}**", inline=True)
    embed.add_field(name="🔗 You Receive (Crypto USD)", value=f"**$ {pretty_num(crypto_usd)}**", inline=True)
    embed.set_footer(text=datetime.now(tz=IST).strftime("Time (IST): %I:%M %p, %d %b %Y"))

    await interaction.response.send_message(embed=embed)

# ---------- /c2i Command ----------
@bot.tree.command(name="c2i", description="Convert Client USD → INR", guild=GUILD)
@app_commands.describe(usd_amount="Enter the amount in USD")
async def c2i(interaction: discord.Interaction, usd_amount: float):
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

    await interaction.response.send_message(embed=embed)

# ---------- Error Handling ----------
@i2c.error
@c2i.error
async def conversion_error(interaction: discord.Interaction, error):
    try:
        if isinstance(error, app_commands.MissingRequiredArgument):
            await interaction.response.send_message("❗ Missing argument.", ephemeral=True)
        elif isinstance(error, app_commands.TransformError):
            await interaction.response.send_message("❗ Please enter a valid number.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ An unexpected error occurred. Try again.", ephemeral=True)
    except Exception:
        pass  # Avoid double-response errors

# ---------- Run Bot ----------
token = os.getenv("TOKEN")
if not token:
    print("❌ ERROR: TOKEN not found in environment variables.")
else:
    bot.run(token)
