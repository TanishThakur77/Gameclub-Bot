# gameclub_bot_full.py
import os
import json
import asyncio
from datetime import datetime, timedelta, timezone
from threading import Thread

import discord
from discord import app_commands
from discord.ext import commands, tasks
from flask import Flask

# ---------- CONFIG ----------
TOKEN = os.environ.get("TOKEN")  # or replace with "YOUR_TOKEN_HERE"
IST = timezone(timedelta(hours=5, minutes=30))

# Conversion defaults
I2C_RATE = 95.0
C2I_RATE_LOW = 91.0
C2I_RATE_HIGH = 91.5
C2I_THRESHOLD = 100.0

# Files
CRYPTO_FILE = "crypto_slots.json"
UPI_FILE = "upi_slots.json"
BACKUP_DIR = "backups"

# Ensure backup dir exists
os.makedirs(BACKUP_DIR, exist_ok=True)

# ---------- Helpers: JSON persistence ----------
def safe_load_json(path, default):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading {path}: {e}")
    return default

def safe_save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving {path}: {e}")

def backup_now():
    timestamp = datetime.now(tz=IST).strftime("%Y%m%d_%H%M%S")
    try:
        # backup crypto
        if os.path.exists(CRYPTO_FILE):
            with open(CRYPTO_FILE, "r", encoding="utf-8") as src, open(os.path.join(BACKUP_DIR, f"crypto_{timestamp}.json"), "w", encoding="utf-8") as dst:
                dst.write(src.read())
        # backup upi
        if os.path.exists(UPI_FILE):
            with open(UPI_FILE, "r", encoding="utf-8") as src, open(os.path.join(BACKUP_DIR, f"upi_{timestamp}.json"), "w", encoding="utf-8") as dst:
                dst.write(src.read())
        print(f"Backup done: {timestamp}")
    except Exception as e:
        print("Backup error:", e)

# Load persistent data
user_crypto_slots = safe_load_json(CRYPTO_FILE, {})  # {user_id: {"1": {"address":..., "type":...}, ...}}
user_upi_slots = safe_load_json(UPI_FILE, {})        # {user_id: {"1": "upi", ...}}

# ---------- Flask keep-alive (optional) ----------
app = Flask("gameclub_keepalive")

@app.route("/")
def home():
    return "✅ GameClub Bot is alive!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# Start Flask in a separate thread (safe to run even if not hosted on a platform that needs it)
Thread(target=run_flask, daemon=True).start()

# ---------- Bot setup ----------
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ---------- Utility functions ----------
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

# ---------- Background backup task ----------
@tasks.loop(hours=24)
async def daily_backup_task():
    backup_now()

# ---------- On ready ----------
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    try:
        await tree.sync()
        print("🟢 Slash commands synced")
    except Exception as e:
        print("⚠️ Slash sync failed:", e)
    if not daily_backup_task.is_running():
        daily_backup_task.start()

# ---------- Modals for slot entry ----------
class AddCryptoModal(discord.ui.Modal):
    def __init__(self, slot_num: int):
        super().__init__(title=f"Crypto Slot {slot_num}")
        self.slot_num = int(slot_num)
        self.add_item(discord.ui.TextInput(label="Crypto Address", placeholder="Enter wallet address", required=True))
        self.add_item(discord.ui.TextInput(label="Crypto Type", placeholder="e.g., USDT POLY, USDT BEP20, LTC", required=True))

    async def on_submit(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        slots = user_crypto_slots.setdefault(user_id, {str(i): {"address": None, "type": None} for i in range(1,6)})
        slots[str(self.slot_num)]["address"] = self.children[0].value.strip()
        slots[str(self.slot_num)]["type"] = self.children[1].value.strip()
        safe_save_json(CRYPTO_FILE, user_crypto_slots)
        await interaction.response.send_message(f"✅ Crypto slot {self.slot_num} saved.", ephemeral=True)

class AddUPIModal(discord.ui.Modal):
    def __init__(self, slot_num: int):
        super().__init__(title=f"UPI Slot {slot_num}")
        self.slot_num = int(slot_num)
        self.add_item(discord.ui.TextInput(label="UPI ID", placeholder="example@bank", required=True))

    async def on_submit(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        slots = user_upi_slots.setdefault(user_id, {str(i): None for i in range(1,6)})
        slots[str(self.slot_num)] = self.children[0].value.strip()
        safe_save_json(UPI_FILE, user_upi_slots)
        await interaction.response.send_message(f"✅ UPI slot {self.slot_num} saved.", ephemeral=True)

# ---------- Conversion commands ----------
@tree.command(name="i2c", description="Convert INR → USD")
@app_commands.describe(amount="Amount in INR")
async def i2c(interaction: discord.Interaction, amount: float):
    usd = amount / I2C_RATE
    ist_now = datetime.now(tz=IST)
    embed = discord.Embed(title="💱 INR → USD Conversion", color=pick_color(amount), timestamp=ist_now)
    embed.add_field(name="Amount (INR)", value=f"₹ {pretty_num(amount)}", inline=False)
    embed.add_field(name="Converted (USD)", value=f"$ {pretty_num(usd)}", inline=False)
    embed.add_field(name="Rate used", value=f"{I2C_RATE} INR per $", inline=False)
    embed.set_footer(text=f"Time (IST): {ist_now.strftime('%I:%M %p, %d %b %Y')}")
    await interaction.response.send_message(embed=embed)

@tree.command(name="c2i", description="Convert USD → INR")
@app_commands.describe(amount="Amount in USD")
async def c2i(interaction: discord.Interaction, amount: float):
    rate = C2I_RATE_LOW if amount < C2I_THRESHOLD else C2I_RATE_HIGH
    inr = amount * rate
    ist_now = datetime.now(tz=IST)
    embed = discord.Embed(title="💱 USD → INR Conversion", color=pick_color(inr), timestamp=ist_now)
    embed.add_field(name="Amount (USD)", value=f"$ {pretty_num(amount)}", inline=False)
    embed.add_field(name="Converted (INR)", value=f"₹ {pretty_num(inr)}", inline=False)
    embed.add_field(name="Rate used", value=f"{rate} INR per $", inline=False)
    embed.set_footer(text=f"Time (IST): {ist_now.strftime('%I:%M %p, %d %b %Y')}")
    await interaction.response.send_message(embed=embed)

# ---------- Admin: setrate ----------
@tree.command(name="setrate", description="Admin only: set conversion rates")
@app_commands.describe(rate_type="Which rate to set", new_rate="New numeric rate")
@app_commands.choices(rate_type=[
    app_commands.Choice(name="I2C (INR → USD)", value="i2c"),
    app_commands.Choice(name="C2I Low (USD < threshold)", value="c2i_low"),
    app_commands.Choice(name="C2I High (USD ≥ threshold)", value="c2i_high")
])
async def setrate(interaction: discord.Interaction, rate_type: app_commands.Choice[str], new_rate: float):
    global I2C_RATE, C2I_RATE_LOW, C2I_RATE_HIGH
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("🚫 Only admins can use this.", ephemeral=True)
        return
    if rate_type.value == "i2c":
        I2C_RATE = new_rate
        title = "I2C rate updated"
    elif rate_type.value == "c2i_low":
        C2I_RATE_LOW = new_rate
        title = "C2I low rate updated"
    else:
        C2I_RATE_HIGH = new_rate
        title = "C2I high rate updated"
    await interaction.response.send_message(f"✅ {title}: {new_rate}", ephemeral=True)

# ---------- Add / Update slot commands (open modals) ----------
@tree.command(name="add-addy", description="Add or replace a crypto slot (address + type)")
@app_commands.describe(slot_num="Slot number 1-5")
async def add_addy(interaction: discord.Interaction, slot_num: int):
    if not 1 <= slot_num <= 5:
        await interaction.response.send_message("❌ Invalid slot number. Choose 1-5.", ephemeral=True)
        return
    await interaction.response.send_modal(AddCryptoModal(slot_num))

@tree.command(name="add-upi", description="Add or replace a UPI slot")
@app_commands.describe(slot_num="Slot number 1-5")
async def add_upi(interaction: discord.Interaction, slot_num: int):
    if not 1 <= slot_num <= 5:
        await interaction.response.send_message("❌ Invalid slot number. Choose 1-5.", ephemeral=True)
        return
    await interaction.response.send_modal(AddUPIModal(slot_num))

# ---------- Manage-slot (update/delete user's own slots) ----------
@tree.command(name="manage-slot", description="Update or delete your slot (per-user)")
@app_commands.describe(action="Update or Delete", slot_type="Crypto or UPI", slot_num="Slot number 1-5")
@app_commands.choices(action=[
    app_commands.Choice(name="Update", value="update"),
    app_commands.Choice(name="Delete", value="delete")
])
@app_commands.choices(slot_type=[
    app_commands.Choice(name="Crypto", value="crypto"),
    app_commands.Choice(name="UPI", value="upi")
])
async def manage_slot(interaction: discord.Interaction, action: app_commands.Choice[str], slot_type: app_commands.Choice[str], slot_num: int):
    if not 1 <= slot_num <= 5:
        await interaction.response.send_message("❌ Invalid slot number. Choose 1-5.", ephemeral=True)
        return

    user_id = str(interaction.user.id)
    if slot_type.value == "crypto":
        slots = user_crypto_slots.setdefault(user_id, {str(i): {"address": None, "type": None} for i in range(1,6)})
        if action.value == "delete":
            slots[str(slot_num)] = {"address": None, "type": None}
            safe_save_json(CRYPTO_FILE, user_crypto_slots)
            await interaction.response.send_message(f"✅ Crypto slot {slot_num} deleted.", ephemeral=True)
        else:
            await interaction.response.send_modal(AddCryptoModal(slot_num))
    else:
        slots = user_upi_slots.setdefault(user_id, {str(i): None for i in range(1,6)})
        if action.value == "delete":
            slots[str(slot_num)] = None
            safe_save_json(UPI_FILE, user_upi_slots)
            await interaction.response.send_message(f"✅ UPI slot {slot_num} deleted.", ephemeral=True)
        else:
            await interaction.response.send_modal(AddUPIModal(slot_num))

# ---------- Receiving-method: embed then plain address ----------
@tree.command(name="receiving-method", description="Show embed then plain address/UPI (per-user)")
@app_commands.describe(slot_type="Crypto or UPI", slot_num="Slot number 1-5")
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

    # Send embed first
    await interaction.response.send_message(embed=embed)
    # Then send plain address (only the address/UPI)
    await interaction.followup.send(f"{address}")

# ---------- Preview: show all saved slots for the user ----------
@tree.command(name="preview", description="Preview all your saved crypto & UPI slots (per-user)")
async def preview(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    crypto = user_crypto_slots.get(user_id, {})
    upi = user_upi_slots.get(user_id, {})

    embed = discord.Embed(title=f"📂 Saved Slots — {interaction.user.display_name}", color=discord.Color.gold(), timestamp=datetime.now(tz=IST))
    # Crypto slots
    for i in range(1,6):
        s = crypto.get(str(i), {"address": None, "type": None})
        addr = s.get("address") or "Empty"
        typ = s.get("type") or "Empty"
        embed.add_field(name=f"Crypto Slot {i}", value=f"Address: `{addr}`\nType: `{typ}`", inline=False)

    # UPI slots
    for i in range(1,6):
        u = upi.get(str(i), None) or "Empty"
        embed.add_field(name=f"UPI Slot {i}", value=f"`{u}`", inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=True)

# ---------- Detailed Help ----------
@tree.command(name="help", description="Show detailed help for all commands")
async def help_command(interaction: discord.Interaction):
    ist_now = datetime.now(tz=IST)
    embed = discord.Embed(title="📖 GameClub Bot — Detailed Help", color=discord.Color.green(), timestamp=ist_now)
    embed.add_field(name="/add-addy <slot_num>", value="Open modal to save crypto address + type to your slot. (slots 1-5). Example: `/add-addy slot_num:1`", inline=False)
    embed.add_field(name="/add-upi <slot_num>", value="Open modal to save UPI ID to your slot. (slots 1-5). Example: `/add-upi slot_num:2`", inline=False)
    embed.add_field(name="/manage-slot", value="Update (opens modal) or Delete your slot. Example: `/manage-slot action:delete slot_type:crypto slot_num:1`", inline=False)
    embed.add_field(name="/receiving-method", value="Shows embed with saved info then sends a plain address/UPI. Example: `/receiving-method slot_type:crypto slot_num:1`", inline=False)
    embed.add_field(name="/preview", value="Preview all 5 crypto + 5 UPI slots you saved.", inline=False)
    embed.add_field(name="/i2c <amount>", value="Convert INR → USD.", inline=False)
    embed.add_field(name="/c2i <amount>", value="Convert USD → INR.", inline=False)
    embed.add_field(name="/setrate", value="Admin only: change conversion rates. Example: `/setrate rate_type:I2C new_rate:96`", inline=False)
    embed.add_field(name="/command", value="Plain list of commands (ephemeral).", inline=False)
    embed.set_footer(text="All slots are per-user and saved persistently to JSON files.")
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ---------- Plain command list ----------
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
/preview
/help
/command
"""
    await interaction.response.send_message(commands_text, ephemeral=True)

# ---------- Simple ping ----------
@tree.command(name="ping", description="Check if bot is online")
async def ping_simple(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Pong! Bot is online.", ephemeral=True)

# ---------- Run ----------
if not TOKEN:
    print("❌ TOKEN not found. Set the TOKEN environment variable.")
else:
    try:
        bot.run(TOKEN)
    except Exception as e:
        print("Error running bot:", e)
