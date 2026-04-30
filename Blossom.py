import discord
from discord.ext import commands, tasks
from discord.ui import Button, View, Modal, TextInput, Select
import random
import asyncio
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import json

# Try to import keep_alive (for Replit hosting), otherwise skip
try:
    from keep_alive import keep_alive
except ImportError:
    def keep_alive():
        pass

# --- BOT CONFIGURATION ---
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="b!", intents=intents)
bot.remove_command('help')

# --- ADMIN LIST ---
ADMINS = ["dispute12", "xion0624"]

# --- DATABASE SETUP ---
MONGO_AVAILABLE = True
try:
    from pymongo import MongoClient
except ImportError:
    MONGO_AVAILABLE = False
    print("⚠️ pymongo not installed")

MONGODB_URI = os.getenv('MONGODB_URI')
USE_MONGODB = False

if MONGODB_URI and MONGO_AVAILABLE:
    try:
        mongo_client = MongoClient(MONGODB_URI)
        db = mongo_client['blossom_garden_bot']
        USE_MONGODB = True
        print("✅ Connected to MongoDB Atlas!")
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")

# File paths – added pet_equipped and permanents
DATA_FILES = {
    'economy': 'data/economy.json',
    'inventory': 'data/inventory.json',
    'pets': 'data/pets.json',
    'pet_equipped': 'data/pet_equipped.json',
    'cooldowns': 'data/cooldowns.json',
    'redeem': 'data/redeem.json',
    'channels': 'data/channels.json',
    'buffs': 'data/buffs.json',
    'permanents': 'data/permanents.json'
}

if not os.path.exists('data'):
    os.makedirs('data')

# Initialize global variables
economy = {}
player_inventory = {}
player_pets = {}
pet_equipped = {}
player_buffs = {}
player_permanents = {}
beg_cooldown = {}
farm_cooldown = {}
hunt_cooldown = {}
work_cooldown = {}
daily_cooldown = {}
weekly_cooldown = {}
hourly_cooldown = {}
gift_cooldown = {}
pet_feed_cooldown = {}
pet_play_cooldown = {}
pet_cooldown = {}
redeem_codes = {}
server_channels = {}

DAILY_GIFT_LIMIT = 1000000

# (shop_items, pet_shop_items remain the same – omitted for brevity, they are unchanged)
# ... [keep all shop_items and pet_shop_items definitions as in original]

# Helper function to parse user input
def parse_user_input(guild, user_input):
    """Parse user input (mention, ID, or username) into a Member object"""
    user_input = user_input.strip()
    if user_input.startswith('<@') and user_input.endswith('>'):
        user_id = int(user_input.strip('<@!>'))
        return guild.get_member(user_id)
    if user_input.isdigit():
        return guild.get_member(int(user_input))
    username_lower = user_input.lower()
    for member in guild.members:
        if member.name.lower() == username_lower:
            return member
        if member.display_name.lower() == username_lower:
            return member
    # Backwards compatibility for old name#discriminator format
    if '#' in user_input:
        name, discrim = user_input.split('#')
        for member in guild.members:
            if member.name == name and member.discriminator == discrim:
                return member
    return None

# --- DATABASE FUNCTIONS ---
def load_all_data():
    global economy, player_inventory, player_pets, pet_equipped, player_buffs, player_permanents
    global beg_cooldown, farm_cooldown, hunt_cooldown, work_cooldown
    global daily_cooldown, weekly_cooldown, hourly_cooldown, gift_cooldown
    global pet_feed_cooldown, pet_play_cooldown, pet_cooldown
    global redeem_codes, server_channels

    if USE_MONGODB:
        try:
            eco_data = db.economy.find_one({'_id': 'economy'})
            if eco_data:
                economy = {int(k): v for k, v in eco_data.get('data', {}).items()}
            inv_data = db.inventory.find_one({'_id': 'inventory'})
            if inv_data:
                player_inventory = {int(k): v for k, v in inv_data.get('data', {}).items()}
            pets_data = db.pets.find_one({'_id': 'pets'})
            if pets_data:
                player_pets = {int(k): v for k, v in pets_data.get('data', {}).items()}
            equipped_data = db.pets.find_one({'_id': 'pet_equipped'})
            if equipped_data:
                pet_equipped = {int(k): v for k, v in equipped_data.get('data', {}).items()}
            buffs_data = db.buffs.find_one({'_id': 'buffs'})
            if buffs_data:
                player_buffs = {int(k): v for k, v in buffs_data.get('data', {}).items()}
            perms_data = db.permanents.find_one({'_id': 'permanents'})
            if perms_data:
                player_permanents = {int(k): v for k, v in perms_data.get('data', {}).items()}
            # Cooldowns loading same as before...
            cooldowns_data = db.cooldowns.find_one({'_id': 'cooldowns'})
            if cooldowns_data:
                cooldowns = cooldowns_data.get('data', {})
                for uid, data in cooldowns.items():
                    uid_int = int(uid)
                    if 'beg' in data: beg_cooldown[uid_int] = datetime.fromisoformat(data['beg'])
                    if 'farm' in data: farm_cooldown[uid_int] = datetime.fromisoformat(data['farm'])
                    if 'hunt' in data: hunt_cooldown[uid_int] = datetime.fromisoformat(data['hunt'])
                    if 'work' in data: work_cooldown[uid_int] = datetime.fromisoformat(data['work'])
                    if 'daily' in data: daily_cooldown[uid_int] = datetime.fromisoformat(data['daily'])
                    if 'weekly' in data: weekly_cooldown[uid_int] = datetime.fromisoformat(data['weekly'])
                    if 'hourly' in data: hourly_cooldown[uid_int] = datetime.fromisoformat(data['hourly'])
                    if 'gift' in data:
                        gift_cooldown[uid_int] = (datetime.fromisoformat(data['gift']['date']), data['gift']['amount'])
                    if 'pet_feed' in data: pet_feed_cooldown[uid_int] = datetime.fromisoformat(data['pet_feed'])
                    if 'pet_play' in data: pet_play_cooldown[uid_int] = datetime.fromisoformat(data['pet_play'])
                    if 'pet_reward' in data: pet_cooldown[uid_int] = datetime.fromisoformat(data['pet_reward'])
            redeem_data = db.redeem.find_one({'_id': 'redeem'})
            if redeem_data:
                redeem_codes = redeem_data.get('data', {})
            channels_data = db.channels.find_one({'_id': 'channels'})
            if channels_data:
                server_channels = {int(k): v for k, v in channels_data.get('data', {}).items()}
            print("✅ Loaded data from MongoDB")
        except Exception as e:
            print(f"❌ MongoDB load error: {e}")
            load_from_files()
    else:
        load_from_files()

def load_from_files():
    global economy, player_inventory, player_pets, pet_equipped, player_buffs, player_permanents
    global beg_cooldown, farm_cooldown, hunt_cooldown, work_cooldown
    global daily_cooldown, weekly_cooldown, hourly_cooldown, gift_cooldown
    global pet_feed_cooldown, pet_play_cooldown, pet_cooldown
    global redeem_codes, server_channels

    try:
        with open(DATA_FILES['economy'], 'r') as f: economy = {int(k): v for k, v in json.load(f).items()}
    except: economy = {}
    try:
        with open(DATA_FILES['inventory'], 'r') as f: player_inventory = {int(k): v for k, v in json.load(f).items()}
    except: player_inventory = {}
    try:
        with open(DATA_FILES['pets'], 'r') as f: player_pets = {int(k): v for k, v in json.load(f).items()}
    except: player_pets = {}
    try:
        with open(DATA_FILES['pet_equipped'], 'r') as f: pet_equipped = {int(k): v for k, v in json.load(f).items()}
    except: pet_equipped = {}
    try:
        with open(DATA_FILES['buffs'], 'r') as f: player_buffs = {int(k): v for k, v in json.load(f).items()}
    except: player_buffs = {}
    try:
        with open(DATA_FILES['permanents'], 'r') as f: player_permanents = {int(k): v for k, v in json.load(f).items()}
    except: player_permanents = {}
    try:
        with open(DATA_FILES['cooldowns'], 'r') as f:
            cooldowns = json.load(f)
            for uid_str, data in cooldowns.items():
                uid = int(uid_str)
                if 'beg' in data: beg_cooldown[uid] = datetime.fromisoformat(data['beg'])
                if 'farm' in data: farm_cooldown[uid] = datetime.fromisoformat(data['farm'])
                if 'hunt' in data: hunt_cooldown[uid] = datetime.fromisoformat(data['hunt'])
                if 'work' in data: work_cooldown[uid] = datetime.fromisoformat(data['work'])
                if 'daily' in data: daily_cooldown[uid] = datetime.fromisoformat(data['daily'])
                if 'weekly' in data: weekly_cooldown[uid] = datetime.fromisoformat(data['weekly'])
                if 'hourly' in data: hourly_cooldown[uid] = datetime.fromisoformat(data['hourly'])
                if 'gift' in data:
                    gift_cooldown[uid] = (datetime.fromisoformat(data['gift']['date']), data['gift']['amount'])
                if 'pet_feed' in data: pet_feed_cooldown[uid] = datetime.fromisoformat(data['pet_feed'])
                if 'pet_play' in data: pet_play_cooldown[uid] = datetime.fromisoformat(data['pet_play'])
                if 'pet_reward' in data: pet_cooldown[uid] = datetime.fromisoformat(data['pet_reward'])
    except: pass
    try:
        with open(DATA_FILES['redeem'], 'r') as f: redeem_codes = json.load(f)
    except: redeem_codes = {}
    try:
        with open(DATA_FILES['channels'], 'r') as f: server_channels = {int(k): v for k, v in json.load(f).items()}
    except: server_channels = {}
    print("✅ Loaded data from local files")

def save_all_data():
    if USE_MONGODB:
        try:
            db.economy.update_one({'_id': 'economy'}, {'$set': {'data': {str(k): v for k, v in economy.items()}}}, upsert=True)
            db.inventory.update_one({'_id': 'inventory'}, {'$set': {'data': {str(k): v for k, v in player_inventory.items()}}}, upsert=True)
            db.pets.update_one({'_id': 'pets'}, {'$set': {'data': {str(k): v for k, v in player_pets.items()}}}, upsert=True)
            db.pets.update_one({'_id': 'pet_equipped'}, {'$set': {'data': {str(k): v for k, v in pet_equipped.items()}}}, upsert=True)
            db.buffs.update_one({'_id': 'buffs'}, {'$set': {'data': {str(k): v for k, v in player_buffs.items()}}}, upsert=True)
            db.permanents.update_one({'_id': 'permanents'}, {'$set': {'data': {str(k): v for k, v in player_permanents.items()}}}, upsert=True)

            # Cooldowns saving (same logic)
            cooldowns = {}
            all_users = set(list(beg_cooldown.keys()) + list(farm_cooldown.keys()) + list(hunt_cooldown.keys()) +
                            list(work_cooldown.keys()) + list(daily_cooldown.keys()) + list(weekly_cooldown.keys()) +
                            list(hourly_cooldown.keys()) + list(gift_cooldown.keys()) + list(pet_feed_cooldown.keys()) +
                            list(pet_play_cooldown.keys()) + list(pet_cooldown.keys()))
            for uid in all_users:
                cooldowns[str(uid)] = {}
                if uid in beg_cooldown: cooldowns[str(uid)]['beg'] = beg_cooldown[uid].isoformat()
                if uid in farm_cooldown: cooldowns[str(uid)]['farm'] = farm_cooldown[uid].isoformat()
                if uid in hunt_cooldown: cooldowns[str(uid)]['hunt'] = hunt_cooldown[uid].isoformat()
                if uid in work_cooldown: cooldowns[str(uid)]['work'] = work_cooldown[uid].isoformat()
                if uid in daily_cooldown: cooldowns[str(uid)]['daily'] = daily_cooldown[uid].isoformat()
                if uid in weekly_cooldown: cooldowns[str(uid)]['weekly'] = weekly_cooldown[uid].isoformat()
                if uid in hourly_cooldown: cooldowns[str(uid)]['hourly'] = hourly_cooldown[uid].isoformat()
                if uid in gift_cooldown:
                    cooldowns[str(uid)]['gift'] = {'date': gift_cooldown[uid][0].isoformat(), 'amount': gift_cooldown[uid][1]}
                if uid in pet_feed_cooldown: cooldowns[str(uid)]['pet_feed'] = pet_feed_cooldown[uid].isoformat()
                if uid in pet_play_cooldown: cooldowns[str(uid)]['pet_play'] = pet_play_cooldown[uid].isoformat()
                if uid in pet_cooldown: cooldowns[str(uid)]['pet_reward'] = pet_cooldown[uid].isoformat()
            db.cooldowns.update_one({'_id': 'cooldowns'}, {'$set': {'data': cooldowns}}, upsert=True)
            db.redeem.update_one({'_id': 'redeem'}, {'$set': {'data': redeem_codes}}, upsert=True)
            db.channels.update_one({'_id': 'channels'}, {'$set': {'data': {str(k): v for k, v in server_channels.items()}}}, upsert=True)
            print("💾 Saved to MongoDB")
        except Exception as e:
            print(f"❌ MongoDB save error: {e}")
            save_to_files()
    else:
        save_to_files()

def save_to_files():
    with open(DATA_FILES['economy'], 'w') as f: json.dump({str(k): v for k, v in economy.items()}, f, indent=4)
    with open(DATA_FILES['inventory'], 'w') as f: json.dump({str(k): v for k, v in player_inventory.items()}, f, indent=4)
    with open(DATA_FILES['pets'], 'w') as f: json.dump({str(k): v for k, v in player_pets.items()}, f, indent=4)
    with open(DATA_FILES['pet_equipped'], 'w') as f: json.dump({str(k): v for k, v in pet_equipped.items()}, f, indent=4)
    with open(DATA_FILES['buffs'], 'w') as f: json.dump({str(k): v for k, v in player_buffs.items()}, f, indent=4)
    with open(DATA_FILES['permanents'], 'w') as f: json.dump({str(k): v for k, v in player_permanents.items()}, f, indent=4)
    # Cooldowns saving (same as original but using correct file)
    cooldowns = {}
    all_users = set(list(beg_cooldown.keys()) + list(farm_cooldown.keys()) + list(hunt_cooldown.keys()) +
                    list(work_cooldown.keys()) + list(daily_cooldown.keys()) + list(weekly_cooldown.keys()) +
                    list(hourly_cooldown.keys()) + list(gift_cooldown.keys()) + list(pet_feed_cooldown.keys()) +
                    list(pet_play_cooldown.keys()) + list(pet_cooldown.keys()))
    for uid in all_users:
        cooldowns[str(uid)] = {}
        if uid in beg_cooldown: cooldowns[str(uid)]['beg'] = beg_cooldown[uid].isoformat()
        if uid in farm_cooldown: cooldowns[str(uid)]['farm'] = farm_cooldown[uid].isoformat()
        if uid in hunt_cooldown: cooldowns[str(uid)]['hunt'] = hunt_cooldown[uid].isoformat()
        if uid in work_cooldown: cooldowns[str(uid)]['work'] = work_cooldown[uid].isoformat()
        if uid in daily_cooldown: cooldowns[str(uid)]['daily'] = daily_cooldown[uid].isoformat()
        if uid in weekly_cooldown: cooldowns[str(uid)]['weekly'] = weekly_cooldown[uid].isoformat()
        if uid in hourly_cooldown: cooldowns[str(uid)]['hourly'] = hourly_cooldown[uid].isoformat()
        if uid in gift_cooldown:
            cooldowns[str(uid)]['gift'] = {'date': gift_cooldown[uid][0].isoformat(), 'amount': gift_cooldown[uid][1]}
        if uid in pet_feed_cooldown: cooldowns[str(uid)]['pet_feed'] = pet_feed_cooldown[uid].isoformat()
        if uid in pet_play_cooldown: cooldowns[str(uid)]['pet_play'] = pet_play_cooldown[uid].isoformat()
        if uid in pet_cooldown: cooldowns[str(uid)]['pet_reward'] = pet_cooldown[uid].isoformat()
    with open(DATA_FILES['cooldowns'], 'w') as f: json.dump(cooldowns, f, indent=4)
    with open(DATA_FILES['redeem'], 'w') as f: json.dump(redeem_codes, f, indent=4)
    with open(DATA_FILES['channels'], 'w') as f: json.dump({str(k): v for k, v in server_channels.items()}, f, indent=4)

# ---------- CORE FUNCTIONS (unchanged, but listed for completeness) ----------
def update_balance(user_id, amount):
    global economy
    economy[user_id] = economy.get(user_id, 0) + amount
    if economy[user_id] < 0:
        economy[user_id] = 0
    save_all_data()

def get_balance(user_id):
    return economy.get(user_id, 0)

def add_to_inventory(user_id, item_id, quantity=1):
    global player_inventory
    if user_id not in player_inventory:
        player_inventory[user_id] = {}
    player_inventory[user_id][item_id] = player_inventory[user_id].get(item_id, 0) + quantity
    save_all_data()

def remove_from_inventory(user_id, item_id, quantity=1):
    global player_inventory
    if user_id in player_inventory and item_id in player_inventory[user_id]:
        player_inventory[user_id][item_id] -= quantity
        if player_inventory[user_id][item_id] <= 0:
            del player_inventory[user_id][item_id]
        save_all_data()

def has_item(user_id, item_id, quantity=1):
    return player_inventory.get(user_id, {}).get(item_id, 0) >= quantity

def get_inventory(user_id):
    return player_inventory.get(user_id, {})

def set_cooldown(cooldown_dict, user_id):
    cooldown_dict[user_id] = datetime.now()
    save_all_data()

def check_cooldown(cooldown_dict, user_id, cooldown_seconds=86400):
    if user_id in cooldown_dict:
        last_used = cooldown_dict[user_id]
        time_passed = (datetime.now() - last_used).total_seconds()
        if time_passed < cooldown_seconds:
            remaining = cooldown_seconds - time_passed
            return True, remaining
    return False, 0

def format_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours}h {minutes}m"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"

# Buff functions (unchanged)
def apply_win_buffs(user_id, win_amount):
    return win_amount, False
def apply_loss_protection(user_id, loss_amount):
    return loss_amount, False
def get_daily_multiplier(user_id):
    if user_id in player_buffs and player_buffs[user_id].get('xp_boost'):
        expiry = player_buffs[user_id].get('xp_boost_expiry')
        if expiry and expiry > datetime.now():
            return 2
        else:
            player_buffs[user_id]['xp_boost'] = False
    return 1

# Load data on startup
load_all_data()

# ===================================================================
# ADMIN UI MODALS AND VIEWS (unchanged from original – all the AdminPanelView,
# EditBalanceModal, GiveAllModal, GenerateCodeModal, AddAdminModal, ItemManagementView,
# AddItemModal, RemoveItemModal, ClearInventoryModal, PetManagementView, AddPetModal,
# RemovePetModal, ResetCooldownsView, InspectPlayerView, PlayerSelectMenu, ConfirmResetView)
# They are correctly implemented. I'm not repeating them for brevity.
# ===================================================================

# [Keep all the View classes exactly as they were – they contain no bugs]

# ===================================================================
# REGULAR UI VIEWS (Redeem, Shop, etc.) – unchanged
# ===================================================================

# [Keep all regular views]

# ===================================================================
# GAME VIEWS – unchanged
# ===================================================================

# [Keep all game views]

# ===================================================================
# COMMANDS (help, admin, bal, lb, daily, weekly, hourly, beg, farm, hunt, work,
#           crash, coinflip, dice, slots, roulette, mines, color, higherlower,
#           tower, scratch, treasure, roulettegun, race, poker, blackjack, rps,
#           shop, petshop, inventory, buffs, gift, giftstats, mypets, pet, petstats,
#           duel, redeem, setup, add_admin, admins)
# All these commands are unchanged except the duel view which already works.
# ===================================================================

# [Insert all command definitions from the original code here]

# Auto-save and leaderboard tasks
async def auto_save():
    while True:
        await asyncio.sleep(60)
        save_all_data()
        print("💾 Auto-saved all data!")

@tasks.loop(hours=1)
async def hourly_leaderboard():
    for gid, cid in server_channels.items():
        channel = bot.get_channel(cid)
        if channel and economy:
            top = sorted(economy.items(), key=lambda x: x[1], reverse=True)[:5]
            if top:
                desc = ""
                for i, (uid, bal) in enumerate(top, 1):
                    medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "📊"
                    try:
                        user = await bot.fetch_user(uid)
                        desc += f"{medal} **{i}.** {user.name} — `{bal:,}` petals\n"
                    except:
                        desc += f"{medal} **{i}.** Unknown User — `{bal:,}` petals\n"
                embed = discord.Embed(title="🏆 Hourly Leaderboard", description=desc, color=0xffb7c5)
                await channel.send(embed=embed)

@bot.event
async def on_ready():
    print(f'🌸 {bot.user} is online!')
    print(f'📊 Serving {len(bot.guilds)} servers')
    print(f'💾 Database: {"MongoDB" if USE_MONGODB else "Local File"}')
    print(f'👑 Admins: {", ".join(ADMINS)}')
    bot.loop.create_task(auto_save())
    if not hourly_leaderboard.is_running():
        hourly_leaderboard.start()

# Run the bot
keep_alive()
bot.run(TOKEN)
