# bot.py
import os
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta, timezone
from flask import Flask
from threading import Thread

# ---------- CONFIG ----------
I2C_RATE = 95             # INR → USD (crypto)
C2I_RATE_LOW = 91.0       # USD < 100 → INR
C2I_RATE_HIGH = 91.5      # USD >= 100 → INR
C2I_THRESHOLD = 100.0
GUILD_ID = 785743682334752768  # Replace with your guild/server ID
# ----------------------------

# ---------- Bot & Flask Setup ----------
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='.', intents=intents)
IST = timezone(timedelta(hours=5, minutes=30))

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Bot is running!"

def run():
    port = int(os.environ.get("PORT", 8080, 8080))
    app.run(host="0.0.0.0", port=port)

Thread(target=run).start()

# ---------- Helper Functions ----------
def pretty_num(value):
    return f"{int(value):,}" if float(value).is_integer() else f"{value:,.2f}"

def pick_color(amount):
    if amount < 500:
        return discord.Color.green()
    elif amount < 2000:
        return discord.Color.blue()
    else:
        return discord.Color.gold()

# ---------- User-specific Data ----------
# Stores per-user addresses: {user_id: [slots]}
user_crypto = {}  # {user_id: [{"address": "", "type": ""}, ...5]}
user_upi = {}     # {user_id: ["", "", "", "", ""]}

# ---------- On Ready ----------
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    await bot.change_presence(status=discord.Status.online, activity=discord.Game("💱 USD/INR & Receiving Methods"))
    guild = discord.Object(id=GUILD_ID)
    try:
        await bot.tree.sync(guild=guild)
        print("🔹 Slash commands synced successfully!")
    except Exception as e:
        print(f"⚠️ Command sync failed: {e}")

# ---------- /ping ----------
@bot.tree.command(name="ping", description="Check if bot is alive.")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Pong! The bot is active and working smoothly.", ephemeral=True)

# ---------- /i2c ----------
@bot.tree.command(name="i2c", description="Convert INR → Crypto (USD)")
@app_commands.describe(amount="Enter amount in INR")
async def i2c(interaction: discord.Interaction, amount: float):
    usd = amount / I2C_RATE
    embed = discord.Embed(
        title="💱 INR → Crypto Conversion",
        color=pick_color(amount),
        timestamp=datetime.now(tz=IST)
    )
    embed.add_field(name="💸 You Pay (INR)", value=f"**₹ {pretty_num(amount)}**", inline=True)
    embed.add_field(name="🔗 You Receive (USD)", value=f"**$ {pretty_num(usd)}**", inline=True)
    embed.add_field(name="⚖️ Rate used", value=f"**{I2C_RATE} INR per $**", inline=False)
    embed.set_footer(text=f"Time (IST): {datetime.now(tz=IST).strftime('%I:%M %p, %d %b %Y')}")
    await interaction.response.send_message(embed=embed)

# ---------- /c2i ----------
@bot.tree.command(name="c2i", description="Convert USD → INR")
@app_commands.describe(amount="Enter amount in USD")
async def c2i(interaction: discord.Interaction, amount: float):
    rate = C2I_RATE_LOW if amount < C2I_THRESHOLD else C2I_RATE_HIGH
    inr = amount * rate
    embed = discord.Embed(
        title="💸 Crypto → INR Conversion",
        color=pick_color(inr),
        timestamp=datetime.now(tz=IST)
    )
    embed.add_field(name="💰 You Pay (USD)", value=f"**$ {pretty_num(amount)}**", inline=True)
    embed.add_field(name="🇮🇳 You Receive (INR)", value=f"**₹ {pretty_num(inr)}**", inline=True)
    embed.add_field(name="⚖️ Rate used", value=f"**{rate:g} INR per $**", inline=False)
    embed.set_footer(text=f"Time (IST): {datetime.now(tz=IST).strftime('%I:%M %p, %d %b %Y')}")
    await interaction.response.send_message(embed=embed)

# ---------- /setrate with dropdown ----------
@bot.tree.command(name="setrate", description="Set conversion rates (I2C or C2I)")
@app_commands.choices(rate_type=[
    app_commands.Choice(name="i2c", value="i2c"),
    app_commands.Choice(name="c2i_low", value="c2i_low"),
    app_commands.Choice(name="c2i_high", value="c2i_high")
])
@app_commands.describe(new_rate="Enter the new rate")
async def setrate(interaction: discord.Interaction, rate_type: app_commands.Choice[str], new_rate: float):
    allowed_roles = ["Mods"]
    if not (interaction.user.id == bot.owner_id or any(role.name in allowed_roles for role in interaction.user.roles)):
        return await interaction.response.send_message("🚫 You don't have permission to set rates.", ephemeral=True)

    global I2C_RATE, C2I_RATE_LOW, C2I_RATE_HIGH
    if rate_type.value == "i2c":
        I2C_RATE = new_rate
        msg = f"💱 I2C rate updated to **{new_rate} INR/$**"
    elif rate_type.value == "c2i_low":
        C2I_RATE_LOW = new_rate
        msg = f"💰 C2I Low rate updated to **{new_rate} INR/$**"
    else:
        C2I_RATE_HIGH = new_rate
        msg = f"💰 C2I High rate updated to **{new_rate} INR/$**"

    await interaction.response.send_message(msg, ephemeral=True)

# ---------- Receiving Method Dropdown ----------
class ReceivingSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Crypto Address", description="Select to see your crypto addresses"),
            discord.SelectOption(label="UPI ID", description="Select to see your UPI IDs")
        ]
        super().__init__(placeholder="Choose your receiving method", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        choice = self.values[0]

        if choice == "Crypto Address":
            slots = user_crypto.get(user_id, [{}]*5)
            msg = ""
            for idx, slot in enumerate(slots):
                if slot.get("address"):
                    msg += f"**Payment Address:**\n**{slot['address']}**\n**Type:** {slot['type']}\n\n"
            if not msg:
                msg = "No crypto addresses found. Use `/add-address` to add."
            await interaction.response.send_message(msg, ephemeral=True)

        elif choice == "UPI ID":
            slots = user_upi.get(user_id, [""]*5)
            msg = ""
            for slot in slots:
                if slot:
                    msg += f"**Payment UPI:**\n**{slot}**\n\n"
            if not msg:
                msg = "No UPI IDs found. Use `/add-upi` to add."
            await interaction.response.send_message(msg, ephemeral=True)

class ReceivingView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(ReceivingSelect())

@bot.tree.command(name="receiving-method", description="View your crypto/UPI addresses")
async def receiving_method(interaction: discord.Interaction):
    await interaction.response.send_message("Select a receiving method:", view=ReceivingView(), ephemeral=True)

# ---------- Add or Update Crypto ----------
@bot.tree.command(name="add-address", description="Add or update your crypto address")
@app_commands.describe(slot="Slot 1-5", address="Your crypto address", crypto_type="Type of crypto (USDT, LTC, etc.)")
async def add_address(interaction: discord.Interaction, slot: int, address: str, crypto_type: str):
    if not 1 <= slot <= 5:
        return await interaction.response.send_message("❌ Slot must be between 1 and 5.", ephemeral=True)
    user_id = interaction.user.id
    user_crypto.setdefault(user_id, [{}]*5)
    user_crypto[user_id][slot-1] = {"address": address, "type": crypto_type}
    await interaction.response.send_message(f"✅ Slot {slot} updated!", ephemeral=True)

# ---------- Add or Update UPI ----------
@bot.tree.command(name="add-upi", description="Add or update your UPI ID")
@app_commands.describe(slot="Slot 1-5", upi="Your UPI ID")
async def add_upi(interaction: discord.Interaction, slot: int, upi: str):
    if not 1 <= slot <= 5:
        return await interaction.response.send_message("❌ Slot must be between 1 and 5.", ephemeral=True)
    user_id = interaction.user.id
    user_upi.setdefault(user_id, [""]*5)
    user_upi[user_id][slot-1] = upi
    await interaction.response.send_message(f"✅ UPI Slot {slot} updated!", ephemeral=True)

# ---------- Run Bot ----------
token = os.environ.get("TOKEN")
if not token:
    print("❌ ERROR: No token found in environment variables.")
else:
    bot.run(token)

    print("❌ TOKEN not found!")
else:
    bot.run(TOKEN)

