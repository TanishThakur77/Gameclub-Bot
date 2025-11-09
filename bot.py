import os
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta, timezone
from flask import Flask
from threading import Thread

# ---------- CONFIG ----------
I2C_RATE = 95.0
C2I_RATE_LOW = 91.0
C2I_RATE_HIGH = 91.5
C2I_THRESHOLD = 100.0
GUILD_ID = 785743682334752768
IST = timezone(timedelta(hours=5, minutes=30))

# Per-user slots
user_crypto_slots = {}  # {user_id: {1: {"address":..., "type":...}, ...}}
user_upi_slots = {}     # {user_id: {1: "upi_id", ...}}

# ---------- Helpers ----------
def pretty_num(value):
    return f"{int(value):,}" if float(value).is_integer() else f"{value:,.2f}"

def pick_color(amount):
    if amount < 500:
        return discord.Color.green()
    elif amount < 2000:
        return discord.Color.blue()
    return discord.Color.gold()

# ---------- Flask Keep-Alive ----------
app = Flask("")

@app.route("/")
def home():
    return "✅ Bot is alive!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

Thread(target=run_web).start()

# ---------- Bot ----------
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ---------- On Ready ----------
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    await bot.change_presence(activity=discord.Game("💱 USD ⇄ INR"))
    try:
        await tree.sync()
        print("🟢 Slash commands synced!")
    except Exception as e:
        print(f"⚠️ Failed to sync: {e}")

# ---------- /ping ----------
@tree.command(name="ping", description="Check if bot is alive")
async def ping(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🏓 Pong!",
        description="Bot is working ✅ All systems operational.",
        color=discord.Color.green(),
        timestamp=datetime.now(tz=IST)
    )
    await interaction.response.send_message(embed=embed)

# ---------- /i2c ----------
@tree.command(name="i2c", description="Convert INR → USD")
@app_commands.describe(amount="Amount in INR")
async def i2c(interaction: discord.Interaction, amount: float):
    usd = amount / I2C_RATE
    color = pick_color(amount)
    ist_now = datetime.now(tz=IST)
    embed = discord.Embed(
        title="💱 INR → USD Conversion",
        color=color,
        timestamp=ist_now
    )
    embed.add_field(name="💸 Amount in INR", value=f"**₹ {pretty_num(amount)}**")
    embed.add_field(name="💵 Converted USD", value=f"**$ {pretty_num(usd)}**")
    embed.add_field(name="⚖️ Rate Used", value=f"**{I2C_RATE} INR per $**")
    embed.set_footer(text=f"Time (IST): {ist_now.strftime('%I:%M %p, %d %b %Y')}")
    await interaction.response.send_message(embed=embed)

# ---------- /c2i ----------
@tree.command(name="c2i", description="Convert USD → INR")
@app_commands.describe(amount="Amount in USD")
async def c2i(interaction: discord.Interaction, amount: float):
    rate = C2I_RATE_LOW if amount < C2I_THRESHOLD else C2I_RATE_HIGH
    inr = amount * rate
    color = pick_color(inr)
    ist_now = datetime.now(tz=IST)
    embed = discord.Embed(
        title="💱 USD → INR Conversion",
        color=color,
        timestamp=ist_now
    )
    embed.add_field(name="💵 Amount in USD", value=f"**$ {pretty_num(amount)}**")
    embed.add_field(name="💸 Converted INR", value=f"**₹ {pretty_num(inr)}**")
    embed.add_field(name="⚖️ Rate Used", value=f"**{rate} INR per $**")
    embed.set_footer(text=f"Time (IST): {ist_now.strftime('%I:%M %p, %d %b %Y')}")
    await interaction.response.send_message(embed=embed)

# ---------- /setrate ----------
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
    elif rate_type.value == "c2i_high":
        C2I_RATE_HIGH = new_rate
        title = "💰 C2I High Rate Updated"
    embed = discord.Embed(title=title, description=f"New rate: **{new_rate}**", color=discord.Color.gold())
    embed.set_footer(text=f"Updated by {interaction.user.display_name}")
    await interaction.response.send_message(embed=embed)

# ---------- Modals ----------
class AddCryptoModal(discord.ui.Modal):
    def __init__(self, slot_num: int):
        super().__init__(title=f"Crypto Slot {slot_num}")
        self.slot_num = slot_num
        self.add_item(discord.ui.TextInput(label="Crypto Address", placeholder="Enter your address", required=True))
        self.add_item(discord.ui.TextInput(label="Crypto Type", placeholder="e.g., USDT POLY, USDT BEP20, LTC", required=True))

    async def on_submit(self, interaction: discord.Interaction):
        slots = user_crypto_slots.setdefault(interaction.user.id, {i: {"address": None, "type": None} for i in range(1,6)})
        slots[self.slot_num]["address"] = self.children[0].value
        slots[self.slot_num]["type"] = self.children[1].value
        embed = discord.Embed(
            title=f"✅ Crypto Slot {self.slot_num} Updated",
            description=f"Address: `{self.children[0].value}`\nType: `{self.children[1].value}`",
            color=discord.Color.green(),
            timestamp=datetime.now(tz=IST)
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

class AddUPIModal(discord.ui.Modal):
    def __init__(self, slot_num: int):
        super().__init__(title=f"UPI Slot {slot_num}")
        self.slot_num = slot_num
        self.add_item(discord.ui.TextInput(label="UPI ID", placeholder="Enter your UPI ID", required=True))

    async def on_submit(self, interaction: discord.Interaction):
        slots = user_upi_slots.setdefault(interaction.user.id, {i: None for i in range(1,6)})
        slots[self.slot_num] = self.children[0].value
        embed = discord.Embed(
            title=f"✅ UPI Slot {self.slot_num} Updated",
            description=f"UPI ID: `{self.children[0].value}`",
            color=discord.Color.green(),
            timestamp=datetime.now(tz=IST)
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

# ---------- Add / Manage Slots ----------
@tree.command(name="add-addy", description="Add or replace a crypto slot")
@app_commands.describe(slot_num="Slot number 1-5")
async def add_addy(interaction: discord.Interaction, slot_num: int):
    if slot_num < 1 or slot_num > 5:
        await interaction.response.send_message("❌ Invalid slot! Choose 1-5.", ephemeral=True)
        return
    await interaction.response.send_modal(AddCryptoModal(slot_num))

@tree.command(name="add-upi", description="Add or replace a UPI slot")
@app_commands.describe(slot_num="Slot number 1-5")
async def add_upi(interaction: discord.Interaction, slot_num: int):
    if slot_num < 1 or slot_num > 5:
        await interaction.response.send_message("❌ Invalid slot! Choose 1-5.", ephemeral=True)
        return
    await interaction.response.send_modal(AddUPIModal(slot_num))

# ---------- Receiving Method ----------
from discord.ui import View

@tree.command(name="receiving-method", description="Select crypto or UPI slot to pay")
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
    if slot_type.value == "crypto":
        slots = user_crypto_slots.setdefault(interaction.user.id, {i: {"address": None, "type": None} for i in range(1,6)})
        slot_data = slots[slot_num.value]
        address = slot_data["address"] or "Empty"
        addr_type = slot_data["type"] or "Empty"
        embed = discord.Embed(
            title="📌 Payment Method",
            color=discord.Color.blue(),
            timestamp=datetime.now(tz=IST)
        )
        embed.add_field(name="💰 Payment Address", value=f"`{address}`", inline=False)
        embed.add_field(name="🔹 Address Type", value=f"`{addr_type}`", inline=False)
        embed.set_footer(text=f"Time: {datetime.now(tz=IST).strftime('%I:%M %p, %d %b %Y')}")
    else:
        slots = user_upi_slots.setdefault(interaction.user.id, {i: None for i in range(1,6)})
        address = slots[slot_num.value] or "Empty"
        embed = discord.Embed(
            title="📌 Payment Method",
            color=discord.Color.blue(),
            timestamp=datetime.now(tz=IST)
        )
        embed.add_field(name="💰 Payment UPI", value=f"`{address}`", inline=False)
        embed.set_footer(text=f"Time: {datetime.now(tz=IST).strftime('%I:%M %p, %d %b %Y')}")

    await interaction.response.send_message(embed=embed)

# ---------- Run Bot ----------
TOKEN = os.environ.get("TOKEN")
if not TOKEN:
    print("❌ TOKEN not found!")
else:
    bot.run(TOKEN)
