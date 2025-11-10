"""
Final GameClub Bot - Full feature set
- Per-user persistent crypto (address+type) and UPI slots (5 each) stored in JSON
- /add-addy (modal), /add-upi (modal)
- /manage-slot (update/delete via modals)
- /receiving-method (embed then plain address/UPI)
- /i2c and /c2i conversion commands + /setrate (admin)
- /help (detailed embed) and /command (plain text)
- Flask keep-alive endpoint
"""

import os
import json
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta, timezone
from flask import Flask
from threading import Thread

# ---------- CONFIG ----------
# Put token in environment variable TOKEN or replace os.environ.get("TOKEN") with a string (not recommended)
TOKEN = os.environ.get("TOKEN")
IST = timezone(timedelta(hours=5, minutes=30))

# Conversion rates (can be updated with /setrate by admins)
I2C_RATE = 95.0        # INR -> USD
C2I_RATE_LOW = 91.0    # USD < threshold
C2I_RATE_HIGH = 91.5   # USD >= threshold
C2I_THRESHOLD = 100.0

# Persistent files
CRYPTO_FILE = "crypto_slots.json"  # stores per-user crypto slots
UPI_FILE = "upi_slots.json"        # stores per-user upi slots

# ---------- Helpers (JSON persistence) ----------
def load_json(file_path, default):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except Exception:
            return default
    return default

def save_json(file_path, data):
    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)

# Load persistent user data
# Data shapes:
# user_crypto_slots = { "user_id": { "1": {"address":..., "type":...}, "2": {...}, ... } }
# user_upi_slots = { "user_id": { "1": "upi_id", "2": ... } }
user_crypto_slots = load_json(CRYPTO_FILE, {})
user_upi_slots = load_json(UPI_FILE, {})

# ---------- Flask keep-alive (optional for hosting) ----------
app = Flask("")

@app.route("/")
def home():
    return "✅ Bot is alive!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

Thread(target=run_web, daemon=True).start()

# ---------- Bot setup ----------
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ---------- Utilities ----------
def pretty_num(value):
    try:
        v = float(value)
        return f"{int(v):,}" if v.is_integer() else f"{v:,.2f}"
    except Exception:
        return str(value)

def pick_color(amount):
    try:
        a = float(amount)
        if a < 500:
            return discord.Color.green()
        if a < 2000:
            return discord.Color.blue()
        return discord.Color.gold()
    except Exception:
        return discord.Color.blue()

# ---------- On ready ----------
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    await bot.change_presence(activity=discord.Game("💱 USD ⇄ INR"))
    try:
        await tree.sync()
        print("🟢 Slash commands synced!")
    except Exception as e:
        print("⚠️ Slash sync failed:", e)

# ---------- Modals ----------
class AddCryptoModal(discord.ui.Modal):
    def __init__(self, slot_num: int):
        super().__init__(title=f"Crypto Slot {slot_num}")
        self.slot_num = slot_num
        self.add_item(discord.ui.TextInput(label="Crypto Address", placeholder="Enter your address (e.g., a wallet addr)", required=True))
        self.add_item(discord.ui.TextInput(label="Crypto Type", placeholder="e.g., USDT POLY, USDT BEP20, LTC", required=True))

    async def on_submit(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        slots = user_crypto_slots.setdefault(user_id, {str(i): {"address": None, "type": None} for i in range(1,6)})
        slots[str(self.slot_num)]["address"] = self.children[0].value
        slots[str(self.slot_num)]["type"] = self.children[1].value
        save_json(CRYPTO_FILE, user_crypto_slots)
        await interaction.response.send_message(f"✅ Crypto slot {self.slot_num} updated.", ephemeral=True)

class AddUPIModal(discord.ui.Modal):
    def __init__(self, slot_num: int):
        super().__init__(title=f"UPI Slot {slot_num}")
        self.slot_num = slot_num
        self.add_item(discord.ui.TextInput(label="UPI ID", placeholder="Enter your UPI ID (example@bank)", required=True))

    async def on_submit(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        slots = user_upi_slots.setdefault(user_id, {str(i): None for i in range(1,6)})
        slots[str(self.slot_num)] = self.children[0].value
        save_json(UPI_FILE, user_upi_slots)
        await interaction.response.send_message(f"✅ UPI slot {self.slot_num} updated.", ephemeral=True)

# ---------- Conversion commands ----------
@tree.command(name="i2c", description="Convert INR → USD")
@app_commands.describe(amount="Amount in INR")
async def i2c(interaction: discord.Interaction, amount: float):
    usd = amount / I2C_RATE
    color = pick_color(amount)
    ist_now = datetime.now(tz=IST)
    embed = discord.Embed(title="💱 INR → USD Conversion", color=color, timestamp=ist_now)
    embed.add_field(name="💸 Amount in INR", value=f"**₹ {pretty_num(amount)}**", inline=False)
    embed.add_field(name="💵 Converted USD", value=f"**$ {pretty_num(usd)}**", inline=False)
    embed.add_field(name="⚖️ Rate Used", value=f"**{I2C_RATE} INR per $**", inline=False)
    embed.set_footer(text=f"Time (IST): {ist_now.strftime('%I:%M %p, %d %b %Y')}")
    await interaction.response.send_message(embed=embed)

@tree.command(name="c2i", description="Convert USD → INR")
@app_commands.describe(amount="Amount in USD")
async def c2i(interaction: discord.Interaction, amount: float):
    rate = C2I_RATE_LOW if amount < C2I_THRESHOLD else C2I_RATE_HIGH
    inr = amount * rate
    color = pick_color(inr)
    ist_now = datetime.now(tz=IST)
    embed = discord.Embed(title="💱 USD → INR Conversion", color=color, timestamp=ist_now)
    embed.add_field(name="💵 Amount in USD", value=f"**$ {pretty_num(amount)}**", inline=False)
    embed.add_field(name="💸 Converted INR", value=f"**₹ {pretty_num(inr)}**", inline=False)
    embed.add_field(name="⚖️ Rate Used", value=f"**{rate} INR per $**", inline=False)
    embed.set_footer(text=f"Time (IST): {ist_now.strftime('%I:%M %p, %d %b %Y')}")
    await interaction.response.send_message(embed=embed)

# ---------- Admin: setrate ----------
@tree.command(name="setrate", description="Set conversion rates (Admin only)")
@app_commands.describe(new_rate="Enter new rate")
@app_commands.choices(rate_type=[
    app_commands.Choice(name="I2C (INR → USD)", value="i2c"),
    app_commands.Choice(name="C2I Low (USD < 100)", value="c2i_low"),
    app_commands.Choice(name="C2I High (USD ≥ 100)", value="c2i_high")
])
async def setrate(interaction: discord.Interaction, rate_type: app_commands.Choice[str], new_rate: float):
    global I2C_RATE, C2I_RATE_LOW, C2I_RATE_HIGH
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("🚫 Only admins can change rates.", ephemeral=True)
        return
    if rate_type.value == "i2c":
        I2C_RATE = new_rate
        title = "💱 I2C Rate Updated"
    elif rate_type.value == "c2i_low":
        C2I_RATE_LOW = new_rate
        title = "💸 C2I Low Rate Updated"
    else:
        C2I_RATE_HIGH = new_rate
        title = "💰 C2I High Rate Updated"
    embed = discord.Embed(title=title, description=f"New rate: **{new_rate}**", color=discord.Color.gold())
    embed.set_footer(text=f"Updated by {interaction.user.display_name}")
    await interaction.response.send_message(embed=embed)

# ---------- Add / Update Slots (slash wrappers that open modals) ----------
@tree.command(name="add-addy", description="Add or replace a crypto slot (address + type)")
@app_commands.describe(slot_num="Slot number 1-5")
async def add_addy(interaction: discord.Interaction, slot_num: int):
    if not (1 <= slot_num <= 5):
        await interaction.response.send_message("❌ Invalid slot! Choose 1-5.", ephemeral=True)
        return
    await interaction.response.send_modal(AddCryptoModal(slot_num))

@tree.command(name="add-upi", description="Add or replace a UPI slot")
@app_commands.describe(slot_num="Slot number 1-5")
async def add_upi(interaction: discord.Interaction, slot_num: int):
    if not (1 <= slot_num <= 5):
        await interaction.response.send_message("❌ Invalid slot! Choose 1-5.", ephemeral=True)
        return
    await interaction.response.send_modal(AddUPIModal(slot_num))

# ---------- Manage Slots (update/delete user's own slots) ----------
@tree.command(name="manage-slot", description="Update or delete your slot (crypto/upi)")
@app_commands.describe(action="update or delete", slot_type="crypto or upi", slot_num="Slot number 1-5")
@app_commands.choices(action=[
    app_commands.Choice(name="Update", value="update"),
    app_commands.Choice(name="Delete", value="delete")
])
@app_commands.choices(slot_type=[
    app_commands.Choice(name="Crypto", value="crypto"),
    app_commands.Choice(name="UPI", value="upi")
])
async def manage_slot(interaction: discord.Interaction, action: app_commands.Choice[str], slot_type: app_commands.Choice[str], slot_num: int):
    if not (1 <= slot_num <= 5):
        await interaction.response.send_message("❌ Invalid slot! Choose 1-5.", ephemeral=True)
        return

    user_id = str(interaction.user.id)
    if slot_type.value == "crypto":
        slots = user_crypto_slots.setdefault(user_id, {str(i): {"address": None, "type": None} for i in range(1,6)})
        if action.value == "delete":
            slots[str(slot_num)] = {"address": None, "type": None}
            save_json(CRYPTO_FILE, user_crypto_slots)
            await interaction.response.send_message(f"✅ Crypto slot {slot_num} deleted.", ephemeral=True)
        else:
            await interaction.response.send_modal(AddCryptoModal(slot_num))
    else:
        slots = user_upi_slots.setdefault(user_id, {str(i): None for i in range(1,6)})
        if action.value == "delete":
            slots[str(slot_num)] = None
            save_json(UPI_FILE, user_upi_slots)
            await interaction.response.send_message(f"✅ UPI slot {slot_num} deleted.", ephemeral=True)
        else:
            await interaction.response.send_modal(AddUPIModal(slot_num))

# ---------- Receiving Method: send embed then plain address/UPI ----------
@tree.command(name="receiving-method", description="Show payment embed then send plain address/UPI")
@app_commands.describe(slot_type="Type", slot_num="Slot number 1-5")
@app_commands.choices(slot_type=[
    app_commands.Choice(name="Crypto", value="crypto"),
    app_commands.Choice(name="UPI", value="upi")
])
@app_commands.choices(slot_num=[
    app_commands.Choice(name="1", value=1),
    app_commands.Choice(name="2", value=2),
    app_commands.Choice(name="3", value=3),
    app_commands.Choice(name="4", value=4),
    app_commands.Choice(name="5", value=5)
])
async def receiving_method(interaction: discord.Interaction, slot_type: app_commands.Choice[str], slot_num: app_commands.Choice[int]):
    user_id = str(interaction.user.id)
    ist_now = datetime.now(tz=IST)

    if slot_type.value == "crypto":
        slots = user_crypto_slots.get(user_id, {})
        slot_data = slots.get(str(slot_num.value), {"address": "Empty", "type": "Empty"})
        address = slot_data.get("address", "Empty")
        addr_type = slot_data.get("type", "Empty")
        embed = discord.Embed(title="📌 Payment Method", color=discord.Color.blue(), timestamp=ist_now)
        embed.add_field(name="💰 Payment Address", value=f"`{address}`", inline=False)
        embed.add_field(name="🔹 Address Type", value=f"`{addr_type}`", inline=False)
        embed.set_footer(text=f"Time: {ist_now.strftime('%I:%M %p, %d %b %Y')}")
    else:
        slots = user_upi_slots.get(user_id, {})
        address = slots.get(str(slot_num.value), "Empty")
        embed = discord.Embed(title="📌 Payment Method", color=discord.Color.blue(), timestamp=ist_now)
        embed.add_field(name="💰 Payment UPI", value=f"`{address}`", inline=False)
        embed.set_footer(text=f"Time: {ist_now.strftime('%I:%M %p, %d %b %Y')}")

    # send embed
    await interaction.response.send_message(embed=embed)
    # then send plain address/UPI only
    await interaction.followup.send(f"{address}")

# ---------- Detailed /help (embed) ----------
@tree.command(name="help", description="Show all commands with detailed examples")
async def help_command(interaction: discord.Interaction):
    ist_now = datetime.now(tz=IST)
    embed = discord.Embed(title="📖 Bot Commands - Detailed Help", color=discord.Color.green(), timestamp=ist_now)

    embed.add_field(
        name="/add-addy <slot_num>",
        value="Add or update your crypto slot (address + type).\nExample: `/add-addy slot_num:1` → modal asks for address and type.",
        inline=False
    )
    embed.add_field(
        name="/add-upi <slot_num>",
        value="Add or update your UPI slot.\nExample: `/add-upi slot_num:2` → modal asks for UPI ID.",
        inline=False
    )
    embed.add_field(
        name="/manage-slot",
        value="Update or delete your saved slot.\nExample delete: `/manage-slot action:delete slot_type:crypto slot_num:1`.\nExample update (opens modal): `/manage-slot action:update slot_type:upi slot_num:2`.",
        inline=False
    )
    embed.add_field(
        name="/receiving-method",
        value="Shows embed with the saved data and then sends plain address/UPI.\nExample: `/receiving-method slot_type:crypto slot_num:1`",
        inline=False
    )
    embed.add_field(
        name="/i2c <amount>",
        value="Convert INR to USD.\nExample: `/i2c amount:500`",
        inline=False
    )
    embed.add_field(
        name="/c2i <amount>",
        value="Convert USD to INR.\nExample: `/c2i amount:50`",
        inline=False
    )
    embed.add_field(
        name="/setrate",
        value="Admin only: change conversion rates.\nExample: `/setrate rate_type:I2C new_rate:96`",
        inline=False
    )
    embed.add_field(
        name="/command",
        value="Plain text quick list of commands (ephemeral).",
        inline=False
    )

    embed.set_footer(text="All data is per-user and saved persistently. Use slash commands (/) to interact.")
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ---------- /command plain list ----------
@tree.command(name="command", description="List all commands in plain text")
async def command_list(interaction: discord.Interaction):
    commands_text = """**These are the Commands for The GameClub Bot:**
/ping
/i2c
/c2i
/setrate
/add-addy
/add-upi
/manage-slot
/receiving-method
/help
/command
"""
    await interaction.response.send_message(commands_text, ephemeral=True)

# ---------- Simple /ping ----------
@tree.command(name="ping", description="Check if bot is online")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Pong! Bot is online.", ephemeral=True)

# ---------- Run Bot ----------
if not TOKEN:
    print("❌ TOKEN not found! Set your bot token in the environment variable TOKEN.")
else:
    bot.run(TOKEN)
