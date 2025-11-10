import os
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import TextInput, Modal
from datetime import datetime, timedelta, timezone
from flask import Flask
from threading import Thread
import json

# ---------- CONFIG ----------
IST = timezone(timedelta(hours=5, minutes=30))
DATA_FILE = "user_slots.json"
EXCHANGE_FILE = "exchanges.json"

I2C_RATE = 95.0
C2I_RATE_LOW = 91.0
C2I_RATE_HIGH = 91.5
C2I_THRESHOLD = 100.0

# ---------- Persistent Storage ----------
def load_json(file_path, default):
    if not os.path.exists(file_path):
        return default
    with open(file_path, "r") as f:
        return json.load(f)

def save_json(file_path, data):
    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)

user_slots = load_json(DATA_FILE, {})
exchanges = load_json(EXCHANGE_FILE, {})

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
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ---------- Helpers ----------
def pretty_num(value):
    return f"{int(value):,}" if float(value).is_integer() else f"{value:,.2f}"

def pick_color(amount):
    if amount < 500:
        return discord.Color.green()
    elif amount < 2000:
        return discord.Color.blue()
    return discord.Color.gold()

def get_user_slot(user_id):
    uid = str(user_id)
    if uid not in user_slots:
        user_slots[uid] = {"crypto": {}, "upi": {}}
    return user_slots[uid]

# ---------- On Ready ----------
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    await bot.change_presence(activity=discord.Game("💱 Exchange Tracker"))
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

# ---------- Add / Update Slots ----------
class AddSlotModal(discord.ui.Modal):
    def __init__(self, slot_type: str, slot_num: int):
        super().__init__(title=f"{slot_type.capitalize()} Slot {slot_num}")
        self.slot_type = slot_type
        self.slot_num = slot_num
        if slot_type == "crypto":
            self.add_item(TextInput(label="Address", placeholder="Enter your crypto address", required=True))
            self.add_item(TextInput(label="Type", placeholder="e.g., USDT POLY, LTC", required=True))
        else:
            self.add_item(TextInput(label="UPI ID", placeholder="Enter your UPI ID", required=True))

    async def on_submit(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        if uid not in user_slots:
            user_slots[uid] = {"crypto": {}, "upi": {}}
        slots = user_slots[uid][self.slot_type]
        if self.slot_type == "crypto":
            slots[str(self.slot_num)] = {
                "address": self.children[0].value,
                "type": self.children[1].value
            }
            msg = f"✅ {self.slot_type.capitalize()} Slot {self.slot_num} Updated."
        else:
            slots[str(self.slot_num)] = {"upi": self.children[0].value}
            msg = f"✅ {self.slot_type.upper()} Slot {self.slot_num} Updated."
        save_json(DATA_FILE, user_slots)
        await interaction.response.send_message(msg, ephemeral=True)

# ---------- /add-addy ----------
@tree.command(name="add-addy", description="Add/replace crypto slot")
@app_commands.describe(slot_num="Slot number 1-5")
async def add_addy(interaction: discord.Interaction, slot_num: int):
    if slot_num < 1 or slot_num > 5:
        await interaction.response.send_message("❌ Invalid slot! Choose 1-5.", ephemeral=True)
        return
    await interaction.response.send_modal(AddSlotModal("crypto", slot_num))

# ---------- /add-upi ----------
@tree.command(name="add-upi", description="Add/replace UPI slot")
@app_commands.describe(slot_num="Slot number 1-5")
async def add_upi(interaction: discord.Interaction, slot_num: int):
    if slot_num < 1 or slot_num > 5:
        await interaction.response.send_message("❌ Invalid slot! Choose 1-5.", ephemeral=True)
        return
    await interaction.response.send_modal(AddSlotModal("upi", slot_num))

# ---------- /manage-slot ----------
@tree.command(name="manage-slot", description="Update or delete any slot")
@app_commands.describe(action="Choose action", slot_type="Slot type", slot_num="Slot number 1-5")
@app_commands.choices(action=[
    app_commands.Choice(name="Update", value="update"),
    app_commands.Choice(name="Delete", value="delete")
])
@app_commands.choices(slot_type=[
    app_commands.Choice(name="Crypto", value="crypto"),
    app_commands.Choice(name="UPI", value="upi")
])
async def manage_slot(interaction: discord.Interaction, action: app_commands.Choice[str], slot_type: app_commands.Choice[str], slot_num: int):
    uid = str(interaction.user.id)
    if uid not in user_slots:
        user_slots[uid] = {"crypto": {}, "upi": {}}
    slots = user_slots[uid][slot_type.value]
    if slot_num < 1 or slot_num > 5:
        await interaction.response.send_message("❌ Invalid slot! Choose 1-5.", ephemeral=True)
        return
    if action.value == "delete":
        slots.pop(str(slot_num), None)
        save_json(DATA_FILE, user_slots)
        await interaction.response.send_message(f"✅ {slot_type.value.capitalize()} Slot {slot_num} deleted.", ephemeral=True)
    else:
        await interaction.response.send_modal(AddSlotModal(slot_type.value, slot_num))

# ---------- /receiving-method ----------
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
    uid = str(interaction.user.id)
    slots = get_user_slot(uid)[slot_type.value]
    value = slots.get(str(slot_num.value))
    if not value:
        await interaction.response.send_message("❌ This slot is empty.", ephemeral=True)
        return
    if slot_type.value == "crypto":
        desc = f"💰 **{value['address']}**\nType: **{value['type']}**"
    else:
        desc = f"💰 **{value['upi']}**"
    embed = discord.Embed(
        title="📌 Payment Info",
        description=desc,
        color=discord.Color.blue(),
        timestamp=datetime.now(tz=IST)
    )
    await interaction.response.send_message(embed=embed)

# ---------- /done (all-in-one) ----------
@tree.command(name="done", description="Record a completed exchange")
@app_commands.describe(
    user="Mention the user who did the exchange",
    amount="Amount in USD",
    ex_type="Exchange type (fill manually, e.g., USDT → UPI)"
)
async def done(interaction: discord.Interaction, user: discord.Member, amount: float, ex_type: str):
    uid = str(user.id)
    if uid not in exchanges:
        exchanges[uid] = {"total_amount": 0.0, "deals": 0}
    exchanges[uid]["total_amount"] += amount
    exchanges[uid]["deals"] += 1
    save_json(EXCHANGE_FILE, exchanges)

    # 1️⃣ Confirmation
    embed = discord.Embed(
        title="✅ Exchange Recorded",
        color=pick_color(amount),
        timestamp=datetime.now(tz=IST)
    )
    embed.add_field(name="User", value=user.mention)
    embed.add_field(name="Amount", value=f"${amount:,.2f}")
    embed.add_field(name="Type", value=ex_type)
    embed.add_field(name="Total Deals", value=str(exchanges[uid]["deals"]))
    embed.set_footer(text=f"Recorded at {datetime.now(tz=IST).strftime('%I:%M %p, %d %b %Y')}")
    await interaction.response.send_message(embed=embed)

    # 2️⃣ Thank you
    await interaction.channel.send("🙏 Thank you for choosing Gameclub exchanges! Hope you liked our service.")

    # 3️⃣ Vouch warning
    await interaction.channel.send("📌 Copy Paste this vouch in this server only or get blacklisted!")

    # 4️⃣ Invite link
    await interaction.channel.send("https://discord.gg/tuQeqYy4")

    # 5️⃣ +rep
    await interaction.channel.send(f"+rep {user.id} Legit Exchange {ex_type} ${amount:,.2f}")

    # 6️⃣ Feedback
    feedback_channel = interaction.guild.get_channel(1371445182658252900)
    if feedback_channel:
        await feedback_channel.send(f"📝 Kindly give feedback for our exchanger {interaction.user.mention}")

# ---------- /adjust-total ----------
@tree.command(name="adjust-total", description="Adjust total exchanged amount for a user")
@app_commands.describe(user="Mention a user", adjust_amount="Amount to add or subtract (use negative to decrease)")
async def adjust_total(interaction: discord.Interaction, user: discord.Member, adjust_amount: float):
    uid = str(user.id)
    if uid not in exchanges:
        exchanges[uid] = {"total_amount": 0.0, "deals": 0}
    exchanges[uid]["total_amount"] += adjust_amount
    save_json(EXCHANGE_FILE, exchanges)
    await interaction.response.send_message(f"✅ Total adjusted. New total: ${exchanges[uid]['total_amount']:,.2f}")

# ---------- /profile ----------
@tree.command(name="profile", description="View a user's exchange profile")
@app_commands.describe(user="Mention a user")
async def profile(interaction: discord.Interaction, user: discord.Member):
    data = exchanges.get(str(user.id), {"total_amount": 0.0, "deals": 0})
    total = data["total_amount"]
    deals = data["deals"]
    avg = total / deals if deals else 0.0
    embed = discord.Embed(
        title=f"📊 Exchange Profile: {user.display_name}",
        color=discord.Color.purple(),
        timestamp=datetime.now(tz=IST)
    )
    embed.set_thumbnail(url=user.avatar.url if user.avatar else None)
    embed.add_field(name="Total Exchanged", value=f"${total:,.2f}", inline=True)
    embed.add_field(name="Total Deals", value=str(deals), inline=True)
    embed.add_field(name="Average Deal", value=f"${avg:,.2f}", inline=True)
    embed.set_footer(text=f"Last updated: {datetime.now(tz=IST).strftime('%I:%M %p, %d %b %Y')}")
    await interaction.response.send_message(embed=embed)

# ---------- /help ----------
@tree.command(name="help", description="List all commands")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📜 GameClub Bot Commands",
        description="These are the available commands:",
        color=discord.Color.gold(),
        timestamp=datetime.now(tz=IST)
    )
    cmds = [
        ("/ping", "Check if bot is alive"),
        ("/i2c", "Convert INR → USD"),
        ("/c2i", "Convert USD → INR"),
        ("/setrate", "Set conversion rates (Admin only)"),
        ("/add-addy", "Add or replace crypto slot (1-5)"),
        ("/add-upi", "Add or replace UPI slot (1-5)"),
        ("/manage-slot", "Update or delete any slot"),
        ("/receiving-method", "View your saved crypto/UPI"),
        ("/done", "Record a completed exchange"),
        ("/adjust-total", "Adjust total exchanged amount for a user"),
        ("/profile", "View a user's exchange profile"),
        ("/help", "Show this help message")
    ]
    for c,d in cmds:
        embed.add_field(name=c, value=d, inline=False)
    await interaction.response.send_message(embed=embed)

# ---------- /commands ----------
@tree.command(name="commands", description="Alias for /help")
async def commands_cmd(interaction: discord.Interaction):
    await help_cmd(interaction)

# ---------- Run Bot ----------
TOKEN = os.environ.get("TOKEN")
if not TOKEN:
    print("❌ TOKEN not found!")
else:
    bot.run(TOKEN)
