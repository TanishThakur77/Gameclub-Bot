import os
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta, timezone
from flask import Flask
from threading import Thread

# ---------- CONFIG ----------
I2C_RATE = 95.0           # INR → USD (crypto)
C2I_RATE_LOW = 91.0       # USD < 100 → INR
C2I_RATE_HIGH = 91.5      # USD ≥ 100 → INR
C2I_THRESHOLD = 100.0     # Threshold for low/high C2I
GUILD_ID = 785743682334752768  # Replace with your Discord server ID
IST = timezone(timedelta(hours=5, minutes=30))  # India Standard Time
# ----------------------------

# ---------- Helper Functions ----------
def pretty_num(value):
    """Format number with commas and two decimals."""
    if float(value).is_integer():
        return f"{int(value):,}"
    return f"{value:,.2f}"

def pick_color(amount):
    """Pick embed color based on value."""
    if amount < 500:
        return discord.Color.green()
    elif amount < 2000:
        return discord.Color.blue()
    else:
        return discord.Color.gold()

# ---------- Bot Setup ----------
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ---------- Keep-alive Flask ----------
app = Flask("")

@app.route("/")
def home():
    return "✅ Gameclub Bot is running!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

Thread(target=run_web).start()

# ---------- Bot Events ----------
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    await bot.change_presence(activity=discord.Game("💱 USD ⇄ INR"))
    try:
        await tree.sync()
        print("🟢 Slash commands synced successfully!")
    except Exception as e:
        print(f"⚠️ Failed to sync commands: {e}")

# ---------- /ping ----------
@tree.command(name="ping", description="Check if the bot is alive")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"Latency: {latency} ms",
        color=discord.Color.green(),
        timestamp=datetime.now(tz=IST)
    )
    await interaction.response.send_message(embed=embed)

# ---------- /i2c ----------
@tree.command(name="i2c", description="Convert INR → USD")
@app_commands.describe(amount="Enter amount in INR")
async def i2c(interaction: discord.Interaction, amount: float):
    try:
        await interaction.response.defer(thinking=True)
        usd = amount / I2C_RATE
        color = pick_color(amount)
        ist_now = datetime.now(tz=IST)
        embed = discord.Embed(
            title="💱 INR → USD Conversion",
            color=color,
            timestamp=ist_now
        )
        embed.add_field(name="💸 Amount in INR", value=f"**₹ {pretty_num(amount)}**", inline=True)
        embed.add_field(name="💵 Converted USD", value=f"**$ {pretty_num(usd)}**", inline=True)
        embed.add_field(name="⚖️ Rate Used", value=f"**{I2C_RATE} INR per $**", inline=False)
        embed.set_footer(text=f"Time (IST): {ist_now.strftime('%I:%M %p, %d %b %Y')}")
        await interaction.followup.send(embed=embed)
    except Exception as e:
        print(f"❌ /i2c error: {e}")
        await interaction.followup.send("❌ Something went wrong.", ephemeral=True)

# ---------- /c2i ----------
@tree.command(name="c2i", description="Convert USD → INR")
@app_commands.describe(amount="Enter amount in USD")
async def c2i(interaction: discord.Interaction, amount: float):
    try:
        await interaction.response.defer(thinking=True)
        rate = C2I_RATE_LOW if amount < C2I_THRESHOLD else C2I_RATE_HIGH
        inr = amount * rate
        color = pick_color(inr)
        ist_now = datetime.now(tz=IST)
        embed = discord.Embed(
            title="💱 USD → INR Conversion",
            color=color,
            timestamp=ist_now
        )
        embed.add_field(name="💵 Amount in USD", value=f"**$ {pretty_num(amount)}**", inline=True)
        embed.add_field(name="💸 Converted INR", value=f"**₹ {pretty_num(inr)}**", inline=True)
        embed.add_field(name="⚖️ Rate Used", value=f"**{rate} INR per $**", inline=False)
        embed.set_footer(text=f"Threshold: ${C2I_THRESHOLD} | Time (IST): {ist_now.strftime('%I:%M %p, %d %b %Y')}")
        await interaction.followup.send(embed=embed)
    except Exception as e:
        print(f"❌ /c2i error: {e}")
        await interaction.followup.send("❌ Something went wrong.", ephemeral=True)

# ---------- /setrate with dropdown ----------
@tree.command(name="setrate", description="Set conversion rates (Admin only)")
@app_commands.describe(new_rate="Enter the new rate value")
@app_commands.choices(rate_type=[
    app_commands.Choice(name="I2C (INR → USD)", value="i2c"),
    app_commands.Choice(name="C2I Low (USD < 100)", value="c2i_low"),
    app_commands.Choice(name="C2I High (USD ≥ 100)", value="c2i_high")
])
async def setrate(interaction: discord.Interaction, rate_type: app_commands.Choice[str], new_rate: float):
    global I2C_RATE, C2I_RATE_LOW, C2I_RATE_HIGH
    admin_roles = ["Mods"]

    if not (interaction.user.guild_permissions.administrator or any(role.name in admin_roles for role in interaction.user.roles)):
        embed = discord.Embed(
            title="🚫 Permission Denied",
            description="Only admins or @Mods can change the rates.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    rate_value = rate_type.value
    if rate_value == "i2c":
        I2C_RATE = new_rate
        title = "💱 I2C Rate Updated"
        desc = f"New rate: **{new_rate}**\nUsed for **INR → USD** conversions."
        color = discord.Color.gold()
    elif rate_value == "c2i_low":
        C2I_RATE_LOW = new_rate
        title = "💸 C2I Low Rate Updated"
        desc = f"New rate: **{new_rate}**\nUsed for **USD < {C2I_THRESHOLD}**."
        color = discord.Color.blue()
    elif rate_value == "c2i_high":
        C2I_RATE_HIGH = new_rate
        title = "💰 C2I High Rate Updated"
        desc = f"New rate: **{new_rate}**\nUsed for **USD ≥ {C2I_THRESHOLD}**."
        color = discord.Color.green()
    else:
        embed = discord.Embed(
            title="❗ Invalid Choice",
            description="Please choose a valid rate type.",
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    embed = discord.Embed(
        title=title,
        description=desc,
        color=color
    )
    embed.set_footer(text=f"Updated by {interaction.user.display_name}")
    await interaction.response.send_message(embed=embed)

# ---------- Run Bot ----------
TOKEN = os.environ.get("TOKEN")
if not TOKEN:
    print("❌ ERROR: TOKEN not found in environment variables.")
else:
    bot.run(TOKEN)
