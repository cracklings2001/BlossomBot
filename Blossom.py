import discord
from discord.ext import commands, tasks
from discord.ui import Button, View, Modal, TextInput
import random
import asyncio
import os
from dotenv import load_dotenv
from keep_alive import keep_alive
import math
from datetime import datetime, timedelta
import json

# Try to import pymongo
try:
    from pymongo import MongoClient
    MONGO_AVAILABLE = True
except ImportError:
    MONGO_AVAILABLE = False
    print("⚠️ pymongo not installed")

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

# File paths
DATA_FILES = {
    'economy': 'data/economy.json',
    'inventory': 'data/inventory.json',
    'pets': 'data/pets.json',
    'cooldowns': 'data/cooldowns.json',
    'redeem': 'data/redeem.json',
    'channels': 'data/channels.json',
    'buffs': 'data/buffs.json'
}

if not os.path.exists('data'):
    os.makedirs('data')

# Initialize variables
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

# --- SHOP ITEMS ---
shop_items = {
    "flower_coin": {
        "name": "🌸 Flower Coin",
        "emoji": "🌸",
        "price": 1000,
        "description": "A beautiful collectible flower coin",
        "type": "collectible"
    },
    "rainbow_petal": {
        "name": "🌈 Rainbow Petal",
        "emoji": "🌈",
        "price": 5000,
        "description": "A rare rainbow-colored petal",
        "type": "collectible"
    },
    "golden_flower": {
        "name": "⭐ Golden Flower",
        "emoji": "⭐",
        "price": 10000,
        "description": "A legendary golden flower",
        "type": "collectible"
    },
    "lucky_charm": {
        "name": "🍀 Lucky Charm",
        "emoji": "🍀",
        "price": 25000,
        "description": "Increases your luck in games! (5% better odds)",
        "type": "buff"
    },
    "xp_boost": {
        "name": "⚡ XP Boost",
        "emoji": "⚡",
        "price": 15000,
        "description": "Doubles daily rewards for 24 hours",
        "type": "buff"
    },
    "protection_amulet": {
        "name": "NOT AVAIALBLE",
        "emoji": "🛡️",
        "price": 300000000000000000000000000,
        "description": "NOT FOR SALE",
        "type": "consumable"
    },
    "double_win": {
        "name": "🎰 Double Win Token",
        "emoji": "🎰",
        "price": 50000,
        "description": "Doubles your next win in any game!",
        "type": "consumable"
    },
    "bank_vault": {
        "name": "🏦 Bank Vault",
        "emoji": "🏦",
        "price": 100000,
        "description": "Increases your daily gift limit by 500,000",
        "type": "permanent"
    },
    "mystery_box": {
        "name": "🎁 Mystery Box",
        "emoji": "🎁",
        "price": 7500,
        "description": "Contains random rewards!",
        "type": "mystery"
    },
    "petal_wand": {
        "name": "✨ Petal Wand",
        "emoji": "✨",
        "price": 150000,
        "description": "Legendary wand that glows with power",
        "type": "collectible"
    }
}

# --- PET SHOP ITEMS ---
pet_shop_items = {
    "basic_cat": {
        "name": "🐱 Garden Cat",
        "emoji": "🐱",
        "price": 1000000,
        "description": "A cute cat that guards your garden",
        "daily_reward": 500,
        "rarity": "common",
        "max_level": 10,
        "xp_per_level": 1000
    },
    "basic_dog": {
        "name": "🐕 Garden Dog",
        "emoji": "🐕",
        "price": 1500000,
        "description": "A loyal dog that finds treasures",
        "daily_reward": 750,
        "rarity": "common",
        "max_level": 10,
        "xp_per_level": 1000
    },
    "magical_fox": {
        "name": "🦊 Magical Fox",
        "emoji": "🦊",
        "price": 5000000,
        "description": "A mystical fox that brings good luck",
        "daily_reward": 2000,
        "rarity": "rare",
        "max_level": 15,
        "xp_per_level": 1500
    },
    "crystal_dragon": {
        "name": "🐉 Crystal Dragon",
        "emoji": "🐉",
        "price": 10000000,
        "description": "A majestic dragon that hoards petals",
        "daily_reward": 5000,
        "rarity": "epic",
        "max_level": 20,
        "xp_per_level": 2000
    },
    "phoenix": {
        "name": "🔥 Phoenix",
        "emoji": "🔥",
        "price": 25000000,
        "description": "A legendary bird that rises from ashes",
        "daily_reward": 15000,
        "rarity": "legendary",
        "max_level": 25,
        "xp_per_level": 3000
    },
    "unicorn": {
        "name": "🦄 Rainbow Unicorn",
        "emoji": "🦄",
        "price": 50000000,
        "description": "A mythical unicorn that spreads magic",
        "daily_reward": 30000,
        "rarity": "mythic",
        "max_level": 30,
        "xp_per_level": 5000
    },
    "golden_dragon": {
        "name": "👑 Golden Dragon",
        "emoji": "👑",
        "price": 100000000,
        "description": "The rarest dragon, covered in pure gold",
        "daily_reward": 75000,
        "rarity": "godly",
        "max_level": 50,
        "xp_per_level": 10000
    },
    "void_walker": {
        "name": "🌑 Void Walker",
        "emoji": "🌑",
        "price": 250000000,
        "description": "A mysterious being from another dimension",
        "daily_reward": 150000,
        "rarity": "transcendent",
        "max_level": 100,
        "xp_per_level": 25000
    }
}

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
            
            cooldowns_data = db.cooldowns.find_one({'_id': 'cooldowns'})
            if cooldowns_data:
                cooldowns = cooldowns_data.get('data', {})
                for uid, data in cooldowns.items():
                    uid_int = int(uid)
                    if 'beg' in data:
                        beg_cooldown[uid_int] = datetime.fromisoformat(data['beg'])
                    if 'farm' in data:
                        farm_cooldown[uid_int] = datetime.fromisoformat(data['farm'])
                    if 'hunt' in data:
                        hunt_cooldown[uid_int] = datetime.fromisoformat(data['hunt'])
                    if 'work' in data:
                        work_cooldown[uid_int] = datetime.fromisoformat(data['work'])
                    if 'daily' in data:
                        daily_cooldown[uid_int] = datetime.fromisoformat(data['daily'])
                    if 'weekly' in data:
                        weekly_cooldown[uid_int] = datetime.fromisoformat(data['weekly'])
                    if 'hourly' in data:
                        hourly_cooldown[uid_int] = datetime.fromisoformat(data['hourly'])
                    if 'gift' in data:
                        gift_cooldown[uid_int] = (datetime.fromisoformat(data['gift']['date']), data['gift']['amount'])
                    if 'pet_feed' in data:
                        pet_feed_cooldown[uid_int] = datetime.fromisoformat(data['pet_feed'])
                    if 'pet_play' in data:
                        pet_play_cooldown[uid_int] = datetime.fromisoformat(data['pet_play'])
                    if 'pet_reward' in data:
                        pet_cooldown[uid_int] = datetime.fromisoformat(data['pet_reward'])
            
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
        with open(DATA_FILES['economy'], 'r') as f:
            economy = {int(k): v for k, v in json.load(f).items()}
    except: economy = {}
    
    try:
        with open(DATA_FILES['inventory'], 'r') as f:
            player_inventory = {int(k): v for k, v in json.load(f).items()}
    except: player_inventory = {}
    
    try:
        with open(DATA_FILES['pets'], 'r') as f:
            player_pets = {int(k): v for k, v in json.load(f).items()}
    except: player_pets = {}
    
    try:
        with open(DATA_FILES['pets'] + '_equipped', 'r') as f:
            pet_equipped = {int(k): v for k, v in json.load(f).items()}
    except: pet_equipped = {}
    
    try:
        with open(DATA_FILES['buffs'], 'r') as f:
            player_buffs = {int(k): v for k, v in json.load(f).items()}
    except: player_buffs = {}
    
    try:
        with open(DATA_FILES['cooldowns'], 'r') as f:
            cooldowns = json.load(f)
            for uid, data in cooldowns.items():
                uid_int = int(uid)
                if 'beg' in data:
                    beg_cooldown[uid_int] = datetime.fromisoformat(data['beg'])
                if 'farm' in data:
                    farm_cooldown[uid_int] = datetime.fromisoformat(data['farm'])
                if 'hunt' in data:
                    hunt_cooldown[uid_int] = datetime.fromisoformat(data['hunt'])
                if 'work' in data:
                    work_cooldown[uid_int] = datetime.fromisoformat(data['work'])
                if 'daily' in data:
                    daily_cooldown[uid_int] = datetime.fromisoformat(data['daily'])
                if 'weekly' in data:
                    weekly_cooldown[uid_int] = datetime.fromisoformat(data['weekly'])
                if 'hourly' in data:
                    hourly_cooldown[uid_int] = datetime.fromisoformat(data['hourly'])
                if 'gift' in data:
                    gift_cooldown[uid_int] = (datetime.fromisoformat(data['gift']['date']), data['gift']['amount'])
                if 'pet_feed' in data:
                    pet_feed_cooldown[uid_int] = datetime.fromisoformat(data['pet_feed'])
                if 'pet_play' in data:
                    pet_play_cooldown[uid_int] = datetime.fromisoformat(data['pet_play'])
                if 'pet_reward' in data:
                    pet_cooldown[uid_int] = datetime.fromisoformat(data['pet_reward'])
    except: pass
    
    try:
        with open(DATA_FILES['redeem'], 'r') as f:
            redeem_codes = json.load(f)
    except: redeem_codes = {}
    
    try:
        with open(DATA_FILES['channels'], 'r') as f:
            server_channels = {int(k): v for k, v in json.load(f).items()}
    except: server_channels = {}
    
    player_permanents = {}
    print("✅ Loaded data from local files")

def save_all_data():
    if USE_MONGODB:
        try:
            db.economy.update_one({'_id': 'economy'}, {'$set': {'data': {str(k): v for k, v in economy.items()}}}, upsert=True)
            db.inventory.update_one({'_id': 'inventory'}, {'$set': {'data': {str(k): v for k, v in player_inventory.items()}}}, upsert=True)
            db.pets.update_one({'_id': 'pets'}, {'$set': {'data': {str(k): v for k, v in player_pets.items()}}}, upsert=True)
            db.pets.update_one({'_id': 'pet_equipped'}, {'$set': {'data': {str(k): v for k, v in pet_equipped.items()}}}, upsert=True)
            db.buffs.update_one({'_id': 'buffs'}, {'$set': {'data': {str(k): v for k, v in player_buffs.items()}}}, upsert=True)
            
            cooldowns = {}
            all_users = set(list(beg_cooldown.keys()) + list(farm_cooldown.keys()) + list(hunt_cooldown.keys()) + 
                            list(work_cooldown.keys()) + list(daily_cooldown.keys()) + list(weekly_cooldown.keys()) + 
                            list(hourly_cooldown.keys()) + list(gift_cooldown.keys()) + list(pet_feed_cooldown.keys()) + 
                            list(pet_play_cooldown.keys()) + list(pet_cooldown.keys()))
            
            for uid in all_users:
                cooldowns[str(uid)] = {}
                if uid in beg_cooldown:
                    cooldowns[str(uid)]['beg'] = beg_cooldown[uid].isoformat()
                if uid in farm_cooldown:
                    cooldowns[str(uid)]['farm'] = farm_cooldown[uid].isoformat()
                if uid in hunt_cooldown:
                    cooldowns[str(uid)]['hunt'] = hunt_cooldown[uid].isoformat()
                if uid in work_cooldown:
                    cooldowns[str(uid)]['work'] = work_cooldown[uid].isoformat()
                if uid in daily_cooldown:
                    cooldowns[str(uid)]['daily'] = daily_cooldown[uid].isoformat()
                if uid in weekly_cooldown:
                    cooldowns[str(uid)]['weekly'] = weekly_cooldown[uid].isoformat()
                if uid in hourly_cooldown:
                    cooldowns[str(uid)]['hourly'] = hourly_cooldown[uid].isoformat()
                if uid in gift_cooldown:
                    cooldowns[str(uid)]['gift'] = {'date': gift_cooldown[uid][0].isoformat(), 'amount': gift_cooldown[uid][1]}
                if uid in pet_feed_cooldown:
                    cooldowns[str(uid)]['pet_feed'] = pet_feed_cooldown[uid].isoformat()
                if uid in pet_play_cooldown:
                    cooldowns[str(uid)]['pet_play'] = pet_play_cooldown[uid].isoformat()
                if uid in pet_cooldown:
                    cooldowns[str(uid)]['pet_reward'] = pet_cooldown[uid].isoformat()
            
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
    with open(DATA_FILES['economy'], 'w') as f:
        json.dump({str(k): v for k, v in economy.items()}, f, indent=4)
    with open(DATA_FILES['inventory'], 'w') as f:
        json.dump({str(k): v for k, v in player_inventory.items()}, f, indent=4)
    with open(DATA_FILES['pets'], 'w') as f:
        json.dump({str(k): v for k, v in player_pets.items()}, f, indent=4)
    with open(DATA_FILES['pets'] + '_equipped', 'w') as f:
        json.dump({str(k): v for k, v in pet_equipped.items()}, f, indent=4)
    with open(DATA_FILES['buffs'], 'w') as f:
        json.dump({str(k): v for k, v in player_buffs.items()}, f, indent=4)
    
    cooldowns = {}
    all_users = set(list(beg_cooldown.keys()) + list(farm_cooldown.keys()) + list(hunt_cooldown.keys()) + 
                    list(work_cooldown.keys()) + list(daily_cooldown.keys()) + list(weekly_cooldown.keys()) + 
                    list(hourly_cooldown.keys()) + list(gift_cooldown.keys()) + list(pet_feed_cooldown.keys()) + 
                    list(pet_play_cooldown.keys()) + list(pet_cooldown.keys()))
    
    for uid in all_users:
        cooldowns[str(uid)] = {}
        if uid in beg_cooldown:
            cooldowns[str(uid)]['beg'] = beg_cooldown[uid].isoformat()
        if uid in farm_cooldown:
            cooldowns[str(uid)]['farm'] = farm_cooldown[uid].isoformat()
        if uid in hunt_cooldown:
            cooldowns[str(uid)]['hunt'] = hunt_cooldown[uid].isoformat()
        if uid in work_cooldown:
            cooldowns[str(uid)]['work'] = work_cooldown[uid].isoformat()
        if uid in daily_cooldown:
            cooldowns[str(uid)]['daily'] = daily_cooldown[uid].isoformat()
        if uid in weekly_cooldown:
            cooldowns[str(uid)]['weekly'] = weekly_cooldown[uid].isoformat()
        if uid in hourly_cooldown:
            cooldowns[str(uid)]['hourly'] = hourly_cooldown[uid].isoformat()
        if uid in gift_cooldown:
            cooldowns[str(uid)]['gift'] = {'date': gift_cooldown[uid][0].isoformat(), 'amount': gift_cooldown[uid][1]}
        if uid in pet_feed_cooldown:
            cooldowns[str(uid)]['pet_feed'] = pet_feed_cooldown[uid].isoformat()
        if uid in pet_play_cooldown:
            cooldowns[str(uid)]['pet_play'] = pet_play_cooldown[uid].isoformat()
        if uid in pet_cooldown:
            cooldowns[str(uid)]['pet_reward'] = pet_cooldown[uid].isoformat()
    
    with open(DATA_FILES['cooldowns'], 'w') as f:
        json.dump(cooldowns, f, indent=4)
    with open(DATA_FILES['redeem'], 'w') as f:
        json.dump(redeem_codes, f, indent=4)
    with open(DATA_FILES['channels'], 'w') as f:
        json.dump({str(k): v for k, v in server_channels.items()}, f, indent=4)

# --- CORE FUNCTIONS ---
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

# --- BUFF HANDLING FUNCTIONS ---
def apply_win_buffs(user_id, win_amount):
    if user_id in player_buffs and player_buffs[user_id].get('double_win', 0) > 0:
        win_amount = win_amount * 2
        player_buffs[user_id]['double_win'] -= 1
        if player_buffs[user_id]['double_win'] <= 0:
            del player_buffs[user_id]['double_win']
        save_all_data()
        return win_amount, True
    return win_amount, False

def apply_loss_protection(user_id, loss_amount):
    if user_id in player_buffs and player_buffs[user_id].get('protection', 0) > 0:
        player_buffs[user_id]['protection'] -= 1
        if player_buffs[user_id]['protection'] <= 0:
            del player_buffs[user_id]['protection']
        save_all_data()
        return 0, True
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

# --- UI VIEWS ---

class RedeemModal(Modal, title="🌸 Redeem Petals"):
    code_input = TextInput(label="Voucher Code", placeholder="Enter your code...", min_length=1, max_length=20)
    
    async def on_submit(self, interaction: discord.Interaction):
        code_text = self.code_input.value.strip().upper()
        if code_text in redeem_codes:
            data = redeem_codes[code_text]
            if data["uses"] > 0:
                update_balance(interaction.user.id, data["value"])
                data["uses"] -= 1
                if data["uses"] <= 0:
                    del redeem_codes[code_text]
                save_all_data()
                embed = discord.Embed(title="🌸 Voucher Redeemed!", description=f"{interaction.user.mention} claimed **{data['value']} petals**!", color=0xff69b4)
                await interaction.response.send_message(embed=embed, ephemeral=False)
            else:
                await interaction.response.send_message("❌ Code expired!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Invalid code!", ephemeral=True)

class RedeemButtonView(View):
    def __init__(self):
        super().__init__(timeout=60)
    
    @discord.ui.button(label="🎟️ Redeem Code", style=discord.ButtonStyle.primary, emoji="🎟️")
    async def redeem_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RedeemModal())

# Shop Views
class ShopView(View):
    def __init__(self, ctx, page=0):
        super().__init__(timeout=120)
        self.ctx = ctx
        self.page = page
        self.items_per_page = 5
        self.items_list = list(shop_items.items())
        self.total_pages = max(1, (len(self.items_list) + self.items_per_page - 1) // self.items_per_page)
        self.update_buttons()
    
    def update_buttons(self):
        self.clear_items()
        
        start = self.page * self.items_per_page
        end = min(start + self.items_per_page, len(self.items_list))
        
        for i in range(start, end):
            item_id, item_data = self.items_list[i]
            btn = Button(label=f"{item_data['emoji']} {item_data['name']} - {item_data['price']:,}🌸", 
                        style=discord.ButtonStyle.secondary, custom_id=f"buy_{item_id}")
            btn.callback = self.create_buy_callback(item_id, item_data)
            self.add_item(btn)
        
        if self.page > 0:
            prev = Button(label="◀️ Previous", style=discord.ButtonStyle.primary)
            prev.callback = self.previous_page
            self.add_item(prev)
        
        page_btn = Button(label=f"Page {self.page + 1}/{self.total_pages}", style=discord.ButtonStyle.secondary, disabled=True)
        self.add_item(page_btn)
        
        if self.page < self.total_pages - 1:
            nxt = Button(label="Next ▶️", style=discord.ButtonStyle.primary)
            nxt.callback = self.next_page
            self.add_item(nxt)
        
        inv_btn = Button(label="🎒 Inventory", style=discord.ButtonStyle.success, row=2)
        inv_btn.callback = self.show_inventory
        self.add_item(inv_btn)
        
        close_btn = Button(label="❌ Close", style=discord.ButtonStyle.danger, row=2)
        close_btn.callback = self.close_shop
        self.add_item(close_btn)
    
    def create_buy_callback(self, item_id, item_data):
        async def callback(interaction: discord.Interaction):
            if interaction.user != self.ctx.author:
                await interaction.response.send_message("❌ Not your shop!", ephemeral=True)
                return
            
            if get_balance(interaction.user.id) < item_data['price']:
                await interaction.response.send_message(f"❌ You need {item_data['price']:,} petals!", ephemeral=True)
                return
            
            embed = discord.Embed(title="Confirm Purchase", description=f"Buy {item_data['emoji']} {item_data['name']} for {item_data['price']:,} petals?", color=0xffa500)
            view = ConfirmView(self.ctx, item_id, item_data, item_data['price'])
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        return callback
    
    async def previous_page(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Not your shop!", ephemeral=True)
            return
        self.page -= 1
        self.update_buttons()
        embed = self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def next_page(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Not your shop!", ephemeral=True)
            return
        self.page += 1
        self.update_buttons()
        embed = self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def show_inventory(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Not your inventory!", ephemeral=True)
            return
        await self.ctx.invoke(bot.get_command('inventory'), member=self.ctx.author)
    
    async def close_shop(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Not your shop!", ephemeral=True)
            return
        await interaction.response.edit_message(content="Shop closed!", embed=None, view=None)
        self.stop()
    
    def create_embed(self):
        embed = discord.Embed(title="🌸 Petal Shop", description="Browse our magical items:", color=0xff69b4)
        start = self.page * self.items_per_page
        end = min(start + self.items_per_page, len(self.items_list))
        for i in range(start, end):
            item_id, item_data = self.items_list[i]
            embed.add_field(name=f"{item_data['emoji']} {item_data['name']}", 
                          value=f"Price: {item_data['price']:,} petals\n{item_data['description']}\nType: {item_data['type'].title()}", inline=False)
        balance = get_balance(self.ctx.author.id)
        embed.set_footer(text=f"Your Balance: {balance:,} petals | Page {self.page + 1}/{self.total_pages}")
        return embed

class ConfirmView(View):
    def __init__(self, ctx, item_id, item_data, price):
        super().__init__(timeout=30)
        self.ctx = ctx
        self.item_id = item_id
        self.item_data = item_data
        self.price = price
    
    @discord.ui.button(label="✅ Confirm", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Not your purchase!", ephemeral=True)
            return
        
        if get_balance(interaction.user.id) < self.price:
            await interaction.response.edit_message(content=f"❌ You need {self.price:,} petals!", embed=None, view=None)
            return
        
        update_balance(interaction.user.id, -self.price)
        add_to_inventory(interaction.user.id, self.item_id)
        
        if self.item_id == "mystery_box":
            reward = random.choice([500, 1000, 2500, 5000, 10000, 25000])
            update_balance(interaction.user.id, reward)
            embed = discord.Embed(title="🎁 Mystery Box", description=f"You found {reward:,} petals!", color=0x00ff00)
        else:
            embed = discord.Embed(title="✅ Purchase Successful", description=f"You bought {self.item_data['emoji']} {self.item_data['name']} for {self.price:,} petals!", color=0x00ff00)
        
        embed.add_field(name="New Balance", value=f"{get_balance(interaction.user.id):,} petals")
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()
    
    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Not your purchase!", ephemeral=True)
            return
        await interaction.response.edit_message(content="Purchase cancelled!", embed=None, view=None)
        self.stop()

# Pet Shop Views
class PetShopView(View):
    def __init__(self, ctx, page=0):
        super().__init__(timeout=120)
        self.ctx = ctx
        self.page = page
        self.items_per_page = 4
        self.items_list = list(pet_shop_items.items())
        self.total_pages = max(1, (len(self.items_list) + self.items_per_page - 1) // self.items_per_page)
        self.update_buttons()
    
    def update_buttons(self):
        self.clear_items()
        
        start = self.page * self.items_per_page
        end = min(start + self.items_per_page, len(self.items_list))
        
        for i in range(start, end):
            pet_id, pet_data = self.items_list[i]
            btn = Button(label=f"{pet_data['emoji']} {pet_data['name']} - {pet_data['price']:,}🌸", 
                        style=discord.ButtonStyle.secondary)
            btn.callback = self.create_buy_callback(pet_id, pet_data)
            self.add_item(btn)
        
        if self.page > 0:
            prev = Button(label="◀️ Previous", style=discord.ButtonStyle.primary)
            prev.callback = self.previous_page
            self.add_item(prev)
        
        page_btn = Button(label=f"Page {self.page + 1}/{self.total_pages}", style=discord.ButtonStyle.secondary, disabled=True)
        self.add_item(page_btn)
        
        if self.page < self.total_pages - 1:
            nxt = Button(label="Next ▶️", style=discord.ButtonStyle.primary)
            nxt.callback = self.next_page
            self.add_item(nxt)
        
        my_pets_btn = Button(label="🐾 My Pets", style=discord.ButtonStyle.success, row=2)
        my_pets_btn.callback = self.show_my_pets
        self.add_item(my_pets_btn)
        
        close_btn = Button(label="❌ Close", style=discord.ButtonStyle.danger, row=2)
        close_btn.callback = self.close_shop
        self.add_item(close_btn)
    
    def create_buy_callback(self, pet_id, pet_data):
        async def callback(interaction: discord.Interaction):
            if interaction.user != self.ctx.author:
                await interaction.response.send_message("❌ Not your shop!", ephemeral=True)
                return
            
            if get_balance(interaction.user.id) < pet_data['price']:
                await interaction.response.send_message(f"❌ You need {pet_data['price']:,} petals!", ephemeral=True)
                return
            
            if interaction.user.id in player_pets and pet_id in player_pets[interaction.user.id]:
                await interaction.response.send_message(f"❌ You already own this pet!", ephemeral=True)
                return
            
            embed = discord.Embed(title="Confirm Adoption", description=f"Adopt {pet_data['emoji']} {pet_data['name']} for {pet_data['price']:,} petals?\n\n{pet_data['description']}\nDaily Reward: {pet_data['daily_reward']:,} petals", color=0xffa500)
            view = ConfirmPetView(self.ctx, pet_id, pet_data, pet_data['price'])
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        return callback
    
    async def previous_page(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Not your shop!", ephemeral=True)
            return
        self.page -= 1
        self.update_buttons()
        embed = self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def next_page(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Not your shop!", ephemeral=True)
            return
        self.page += 1
        self.update_buttons()
        embed = self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def show_my_pets(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Not your pets!", ephemeral=True)
            return
        await self.ctx.invoke(bot.get_command('mypets'))
    
    async def close_shop(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Not your shop!", ephemeral=True)
            return
        await interaction.response.edit_message(content="Pet shop closed!", embed=None, view=None)
        self.stop()
    
    def create_embed(self):
        embed = discord.Embed(title="🐾 Magical Pet Shop", description="Adopt a magical companion:", color=0xff69b4)
        start = self.page * self.items_per_page
        end = min(start + self.items_per_page, len(self.items_list))
        for i in range(start, end):
            pet_id, pet_data = self.items_list[i]
            embed.add_field(name=f"{pet_data['emoji']} {pet_data['name']} [{pet_data['rarity'].title()}]", 
                          value=f"Price: {pet_data['price']:,} petals\nDaily Reward: {pet_data['daily_reward']:,} petals\nMax Level: {pet_data['max_level']}\n{pet_data['description']}", inline=False)
        balance = get_balance(self.ctx.author.id)
        embed.set_footer(text=f"Your Balance: {balance:,} petals | Page {self.page + 1}/{self.total_pages}")
        return embed

class ConfirmPetView(View):
    def __init__(self, ctx, pet_id, pet_data, price):
        super().__init__(timeout=30)
        self.ctx = ctx
        self.pet_id = pet_id
        self.pet_data = pet_data
        self.price = price
    
    @discord.ui.button(label="✅ Adopt", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Not your adoption!", ephemeral=True)
            return
        
        if get_balance(interaction.user.id) < self.price:
            await interaction.response.edit_message(content=f"❌ You need {self.price:,} petals!", embed=None, view=None)
            return
        
        update_balance(interaction.user.id, -self.price)
        
        if interaction.user.id not in player_pets:
            player_pets[interaction.user.id] = {}
        
        player_pets[interaction.user.id][self.pet_id] = {
            "name": self.pet_data['name'],
            "level": 1,
            "xp": 0,
            "happiness": 100,
            "last_fed": datetime.now(),
            "last_played": datetime.now()
        }
        
        if interaction.user.id not in pet_equipped:
            pet_equipped[interaction.user.id] = self.pet_id
        
        save_all_data()
        
        embed = discord.Embed(title="🐾 Pet Adopted!", description=f"You adopted {self.pet_data['emoji']} {self.pet_data['name']} for {self.price:,} petals!", color=0x00ff00)
        embed.add_field(name="New Balance", value=f"{get_balance(interaction.user.id):,} petals")
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()
    
    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Not your adoption!", ephemeral=True)
            return
        await interaction.response.edit_message(content="Adoption cancelled!", embed=None, view=None)
        self.stop()

# --- INVENTORY WITH BUTTONS ---
class InventoryView(View):
    def __init__(self, ctx, target, page=0):
        super().__init__(timeout=120)
        self.ctx = ctx
        self.target = target
        self.page = page
        self.items_per_page = 5
        self.inv = get_inventory(target.id)
        self.items_list = [(item_id, qty) for item_id, qty in self.inv.items() if item_id in shop_items]
        self.total_pages = max(1, (len(self.items_list) + self.items_per_page - 1) // self.items_per_page)
        self.update_buttons()
    
    def update_buttons(self):
        self.clear_items()
        
        start = self.page * self.items_per_page
        end = min(start + self.items_per_page, len(self.items_list))
        
        for i in range(start, end):
            item_id, quantity = self.items_list[i]
            item_data = shop_items[item_id]
            
            btn = Button(
                label=f"{item_data['emoji']} {item_data['name']} x{quantity}",
                style=discord.ButtonStyle.primary,
                custom_id=f"use_{item_id}"
            )
            btn.callback = self.create_use_callback(item_id, item_data)
            self.add_item(btn)
        
        if self.page > 0:
            prev_btn = Button(label="◀️ Previous", style=discord.ButtonStyle.secondary)
            prev_btn.callback = self.previous_page
            self.add_item(prev_btn)
        
        if self.total_pages > 1:
            page_btn = Button(label=f"Page {self.page + 1}/{self.total_pages}", style=discord.ButtonStyle.secondary, disabled=True)
            self.add_item(page_btn)
        
        if self.page < self.total_pages - 1:
            next_btn = Button(label="Next ▶️", style=discord.ButtonStyle.secondary)
            next_btn.callback = self.next_page
            self.add_item(next_btn)
        
        close_btn = Button(label="❌ Close", style=discord.ButtonStyle.danger, emoji="❌", row=2)
        close_btn.callback = self.close_inventory
        self.add_item(close_btn)
        
        refresh_btn = Button(label="🔄 Refresh", style=discord.ButtonStyle.secondary, emoji="🔄", row=2)
        refresh_btn.callback = self.refresh_inventory
        self.add_item(refresh_btn)
    
    def create_use_callback(self, item_id, item_data):
        async def callback(interaction: discord.Interaction):
            if interaction.user != self.ctx.author:
                await interaction.response.send_message("❌ This isn't your inventory!", ephemeral=True)
                return
            
            if not has_item(self.target.id, item_id):
                await interaction.response.send_message(f"❌ You no longer have {item_data['emoji']} {item_data['name']}!", ephemeral=True)
                await self.refresh_inventory(interaction)
                return
            
            embed = discord.Embed(
                title=f"📦 Use {item_data['emoji']} {item_data['name']}?",
                description=f"Are you sure you want to use **{item_data['name']}**?\n\n{item_data['description']}",
                color=0xffa500
            )
            
            if item_id == "lucky_charm":
                embed.add_field(name="✨ Effect", value="+5% better luck in games for 24 hours", inline=False)
            elif item_id == "xp_boost":
                embed.add_field(name="✨ Effect", value="Doubles daily rewards for 24 hours", inline=False)
            elif item_id == "protection_amulet":
                embed.add_field(name="✨ Effect", value="Protects you from 1 loss in any game", inline=False)
            elif item_id == "double_win":
                embed.add_field(name="✨ Effect", value="Doubles your next win in any game", inline=False)
            elif item_id == "bank_vault":
                embed.add_field(name="✨ Effect", value="Permanently increases daily gift limit to 1,500,000", inline=False)
            elif item_id == "mystery_box":
                embed.add_field(name="✨ Effect", value="Contains random petals (500 - 25,000)", inline=False)
            else:
                embed.add_field(name="✨ Effect", value="Collectible item - no gameplay effect", inline=False)
            
            view = ConfirmUseView(self.ctx, self, item_id, item_data)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        
        return callback
    
    async def previous_page(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Not your inventory!", ephemeral=True)
            return
        self.page -= 1
        self.update_buttons()
        await self.update_inventory_message(interaction)
    
    async def next_page(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Not your inventory!", ephemeral=True)
            return
        self.page += 1
        self.update_buttons()
        await self.update_inventory_message(interaction)
    
    async def close_inventory(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Not your inventory!", ephemeral=True)
            return
        await interaction.response.edit_message(content="🎒 Inventory closed!", embed=None, view=None)
        self.stop()
    
    async def refresh_inventory(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Not your inventory!", ephemeral=True)
            return
        
        self.inv = get_inventory(self.target.id)
        self.items_list = [(item_id, qty) for item_id, qty in self.inv.items() if item_id in shop_items]
        self.total_pages = max(1, (len(self.items_list) + self.items_per_page - 1) // self.items_per_page)
        
        if self.page >= self.total_pages:
            self.page = max(0, self.total_pages - 1)
        
        self.update_buttons()
        await self.update_inventory_message(interaction)
    
    async def update_inventory_message(self, interaction: discord.Interaction):
        embed = self.create_inventory_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    def create_inventory_embed(self):
        if not self.items_list:
            embed = discord.Embed(
                title=f"🎒 {self.target.display_name}'s Inventory",
                description="No items found! Visit the shop with `b!shop` to buy some!",
                color=0xffa500
            )
            return embed
        
        embed = discord.Embed(
            title=f"🎒 {self.target.display_name}'s Inventory",
            description=f"Click any item button to use it!\nPage {self.page + 1}/{self.total_pages}",
            color=0x00ff88
        )
        
        start = self.page * self.items_per_page
        end = min(start + self.items_per_page, len(self.items_list))
        
        total_value = 0
        for i in range(start, end):
            item_id, quantity = self.items_list[i]
            item_data = shop_items[item_id]
            item_value = item_data['price'] * quantity
            total_value += item_value
            
            effect_text = ""
            if item_id == "lucky_charm":
                effect_text = "🍀 +5% luck (24h)"
            elif item_id == "xp_boost":
                effect_text = "⚡ Double daily rewards (24h)"
            elif item_id == "protection_amulet":
                effect_text = "🛡️ Protects from 1 loss"
            elif item_id == "double_win":
                effect_text = "🎰 Doubles next win"
            elif item_id == "bank_vault":
                effect_text = "🏦 +500k gift limit (permanent)"
            elif item_id == "mystery_box":
                effect_text = "🎁 Random petals (500-25k)"
            else:
                effect_text = "🌸 Collectible"
            
            embed.add_field(
                name=f"{item_data['emoji']} {item_data['name']} x{quantity}",
                value=f"**Value:** {item_value:,} petals\n**Effect:** {effect_text}",
                inline=False
            )
        
        embed.set_footer(text=f"💰 Total Inventory Value: {total_value:,} petals")
        return embed

class ConfirmUseView(View):
    def __init__(self, ctx, parent_view, item_id, item_data):
        super().__init__(timeout=30)
        self.ctx = ctx
        self.parent_view = parent_view
        self.item_id = item_id
        self.item_data = item_data
    
    @discord.ui.button(label="✅ Use Item", style=discord.ButtonStyle.success, emoji="✅")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Not your item!", ephemeral=True)
            return
        
        if not has_item(self.ctx.author.id, self.item_id):
            await interaction.response.edit_message(content=f"❌ You no longer have {self.item_data['emoji']} {self.item_data['name']}!", embed=None, view=None)
            await self.parent_view.refresh_inventory(interaction)
            return
        
        if self.item_id == "mystery_box":
            reward = random.choice([500, 1000, 2500, 5000, 10000, 25000])
            update_balance(self.ctx.author.id, reward)
            remove_from_inventory(self.ctx.author.id, self.item_id)
            embed = discord.Embed(
                title="🎁 Mystery Box Opened! 🎁",
                description=f"You opened a mystery box and found **{reward:,} petals**!",
                color=0x00ff00
            )
            embed.add_field(name="New Balance", value=f"{get_balance(self.ctx.author.id):,} petals", inline=False)
            await interaction.response.edit_message(embed=embed, view=None)
        
        elif self.item_id == "lucky_charm":
            expiry = datetime.now() + timedelta(hours=24)
            if self.ctx.author.id not in player_buffs:
                player_buffs[self.ctx.author.id] = {}
            player_buffs[self.ctx.author.id]['luck'] = True
            player_buffs[self.ctx.author.id]['luck_expiry'] = expiry
            remove_from_inventory(self.ctx.author.id, self.item_id)
            embed = discord.Embed(
                title="🍀 Lucky Charm Activated! 🍀",
                description=f"You used a Lucky Charm!\nYou have **+5% better odds** in games for 24 hours!",
                color=0x00ff00
            )
            embed.add_field(name="Expires", value=f"<t:{int(expiry.timestamp())}:R>", inline=False)
            await interaction.response.edit_message(embed=embed, view=None)
        
        elif self.item_id == "xp_boost":
            expiry = datetime.now() + timedelta(hours=24)
            if self.ctx.author.id not in player_buffs:
                player_buffs[self.ctx.author.id] = {}
            player_buffs[self.ctx.author.id]['xp_boost'] = True
            player_buffs[self.ctx.author.id]['xp_boost_expiry'] = expiry
            remove_from_inventory(self.ctx.author.id, self.item_id)
            embed = discord.Embed(
                title="⚡ XP Boost Activated! ⚡",
                description=f"You used an XP Boost!\nYour daily rewards are **DOUBLED** for 24 hours!",
                color=0x00ff00
            )
            embed.add_field(name="Expires", value=f"<t:{int(expiry.timestamp())}:R>", inline=False)
            await interaction.response.edit_message(embed=embed, view=None)
        
        elif self.item_id == "protection_amulet":
            if self.ctx.author.id not in player_buffs:
                player_buffs[self.ctx.author.id] = {}
            player_buffs[self.ctx.author.id]['protection'] = player_buffs[self.ctx.author.id].get('protection', 0) + 1
            remove_from_inventory(self.ctx.author.id, self.item_id)
            total = player_buffs[self.ctx.author.id]['protection']
            embed = discord.Embed(
                title="🛡️ Protection Amulet Activated! 🛡️",
                description=f"You used a Protection Amulet!\nYou are protected from your next **{total}** loss(es)!",
                color=0x00ff00
            )
            await interaction.response.edit_message(embed=embed, view=None)
        
        elif self.item_id == "double_win":
            if self.ctx.author.id not in player_buffs:
                player_buffs[self.ctx.author.id] = {}
            player_buffs[self.ctx.author.id]['double_win'] = player_buffs[self.ctx.author.id].get('double_win', 0) + 1
            remove_from_inventory(self.ctx.author.id, self.item_id)
            total = player_buffs[self.ctx.author.id]['double_win']
            embed = discord.Embed(
                title="🎰 Double Win Token Activated! 🎰",
                description=f"You used a Double Win Token!\nYour next **{total}** win(s) will be **DOUBLED**!",
                color=0x00ff00
            )
            await interaction.response.edit_message(embed=embed, view=None)
        
        elif self.item_id == "bank_vault":
            if self.ctx.author.id not in player_permanents:
                player_permanents[self.ctx.author.id] = {}
            player_permanents[self.ctx.author.id]['bank_vault'] = True
            remove_from_inventory(self.ctx.author.id, self.item_id)
            embed = discord.Embed(
                title="🏦 Bank Vault Unlocked! 🏦",
                description=f"You unlocked the Bank Vault!\nYour daily gift limit is now **1,500,000** petals (up from 1,000,000)!",
                color=0x00ff00
            )
            await interaction.response.edit_message(embed=embed, view=None)
        
        else:
            remove_from_inventory(self.ctx.author.id, self.item_id)
            embed = discord.Embed(
                title=f"{self.item_data['emoji']} Item Used!",
                description=f"You used **{self.item_data['name']}**!\n*You admire its beauty before it disappears...*",
                color=0xff69b4
            )
            embed.set_footer(text="Collectible items have no gameplay effect, but they're nice to have!")
            await interaction.response.edit_message(embed=embed, view=None)
        
        save_all_data()
        await self.parent_view.refresh_inventory(interaction)
        self.stop()
    
    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.danger, emoji="❌")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Not your item!", ephemeral=True)
            return
        await interaction.response.edit_message(content="❌ Item use cancelled!", embed=None, view=None)
        self.stop()

# --- GAME VIEWS ---

class CrashView(View):
    def __init__(self, ctx, bet):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.bet = bet
        self.multiplier = 1.0
        self.cashed_out = False
        self.crashed = False
        self.crash_point = random.uniform(1.2, 3.0)
        self.message = None
    
    @discord.ui.button(label="💰 Cash Out", style=discord.ButtonStyle.success)
    async def cashout(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Not your game!", ephemeral=True)
            return
        if self.cashed_out or self.crashed:
            return
        
        self.cashed_out = True
        win_amount = int(self.bet * self.multiplier)
        final_win, buff_used = apply_win_buffs(self.ctx.author.id, win_amount)
        update_balance(self.ctx.author.id, final_win - self.bet)
        
        embed = discord.Embed(title="✈️ Cash Out!", description=f"You cashed out at {self.multiplier:.2f}x!", color=0x00ff00)
        if buff_used:
            embed.add_field(name="🎰 DOUBLE WIN TOKEN ACTIVATED!", value=f"Your win was doubled! {win_amount} → {final_win} petals!", inline=False)
        embed.add_field(name="Result", value=f"You won {final_win} petals!", inline=False)
        embed.add_field(name="New Balance", value=f"{get_balance(self.ctx.author.id):,} petals", inline=False)
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()
    
    async def start(self, msg):
        self.message = msg
        for _ in range(30):
            await asyncio.sleep(0.8)
            if self.cashed_out or self.crashed:
                break
            
            self.multiplier += random.uniform(0.05, 0.3)
            
            if random.random() < 0.1 or self.multiplier >= self.crash_point:
                self.crashed = True
                loss_amount = self.bet
                actual_loss, buff_used = apply_loss_protection(self.ctx.author.id, loss_amount)
                update_balance(self.ctx.author.id, -actual_loss)
                embed = discord.Embed(title="💥 CRASH!", description=f"The plane crashed at {self.multiplier:.2f}x!", color=0xff0000)
                if buff_used:
                    embed.add_field(name="🛡️ PROTECTION AMULET ACTIVATED!", value=f"You lost {loss_amount} petals but were protected! No deduction!", inline=False)
                else:
                    embed.add_field(name="Result", value=f"You lost {actual_loss} petals!", inline=False)
                embed.add_field(name="New Balance", value=f"{get_balance(self.ctx.author.id):,} petals", inline=False)
                await self.message.edit(embed=embed, view=None)
                self.stop()
                break
            
            embed = discord.Embed(title="✈️ Crash Game", description=f"Multiplier: {self.multiplier:.2f}x\nCurrent Payout: {int(self.bet * self.multiplier)} petals", color=0xffa500)
            await self.message.edit(embed=embed, view=self)

class CoinflipView(View):
    def __init__(self, ctx, bet):
        super().__init__(timeout=30)
        self.ctx = ctx
        self.bet = bet
    
    @discord.ui.button(label="🪙 HEADS", style=discord.ButtonStyle.primary)
    async def heads(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.flip(interaction, "heads")
    
    @discord.ui.button(label="🪙 TAILS", style=discord.ButtonStyle.primary)
    async def tails(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.flip(interaction, "tails")
    
    async def flip(self, interaction: discord.Interaction, choice):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Not your game!", ephemeral=True)
            return
        
        result = random.choice(["heads", "tails"])
        if choice == result:
            win_amount = int(self.bet * 0.9)
            final_win, buff_used = apply_win_buffs(self.ctx.author.id, win_amount)
            update_balance(self.ctx.author.id, final_win)
            embed = discord.Embed(title="🪙 Coinflip", description=f"You chose {choice.upper()}, result was {result.upper()}!", color=0x00ff00)
            if buff_used:
                embed.add_field(name="🎰 DOUBLE WIN TOKEN ACTIVATED!", value=f"Your win was doubled! {win_amount} → {final_win} petals!", inline=False)
            embed.add_field(name="Result", value=f"You won {final_win} petals!", inline=False)
        else:
            loss_amount = self.bet
            actual_loss, buff_used = apply_loss_protection(self.ctx.author.id, loss_amount)
            update_balance(self.ctx.author.id, -actual_loss)
            embed = discord.Embed(title="🪙 Coinflip", description=f"You chose {choice.upper()}, result was {result.upper()}!", color=0xff0000)
            if buff_used:
                embed.add_field(name="🛡️ PROTECTION AMULET ACTIVATED!", value=f"You lost {loss_amount} petals but were protected! No deduction!", inline=False)
            else:
                embed.add_field(name="Result", value=f"You lost {actual_loss} petals!", inline=False)
        
        embed.add_field(name="New Balance", value=f"{get_balance(self.ctx.author.id):,} petals", inline=False)
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()

class DiceDuelView(View):
    def __init__(self, ctx, bet):
        super().__init__(timeout=30)
        self.ctx = ctx
        self.bet = bet
    
    @discord.ui.button(label="🎲 ROLL", style=discord.ButtonStyle.primary)
    async def roll(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Not your game!", ephemeral=True)
            return
        
        player = random.randint(1, 6)
        bot = random.randint(1, 6)
        dice = {1:"⚀",2:"⚁",3:"⚂",4:"⚃",5:"⚄",6:"⚅"}
        
        if player > bot:
            win_amount = int(self.bet * 1.8)
            final_win, buff_used = apply_win_buffs(self.ctx.author.id, win_amount)
            update_balance(self.ctx.author.id, final_win - self.bet)
            embed = discord.Embed(title="🎲 Dice Duel", description=f"Your roll: {dice[player]} {player}\nBot roll: {dice[bot]} {bot}", color=0x00ff00)
            if buff_used:
                embed.add_field(name="🎰 DOUBLE WIN TOKEN ACTIVATED!", value=f"Your win was doubled! {win_amount} → {final_win} petals!", inline=False)
            embed.add_field(name="Result", value=f"You won {final_win} petals!", inline=False)
        else:
            loss_amount = self.bet
            actual_loss, buff_used = apply_loss_protection(self.ctx.author.id, loss_amount)
            update_balance(self.ctx.author.id, -actual_loss)
            embed = discord.Embed(title="🎲 Dice Duel", description=f"Your roll: {dice[player]} {player}\nBot roll: {dice[bot]} {bot}", color=0xff0000)
            if buff_used:
                embed.add_field(name="🛡️ PROTECTION AMULET ACTIVATED!", value=f"You lost {loss_amount} petals but were protected! No deduction!", inline=False)
            else:
                embed.add_field(name="Result", value=f"You lost {actual_loss} petals!", inline=False)
        
        embed.add_field(name="New Balance", value=f"{get_balance(self.ctx.author.id):,} petals", inline=False)
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()

class SlotMachineView(View):
    def __init__(self, ctx, bet):
        super().__init__(timeout=30)
        self.ctx = ctx
        self.bet = bet
    
    @discord.ui.button(label="🎰 SPIN", style=discord.ButtonStyle.primary)
    async def spin(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Not your game!", ephemeral=True)
            return
        
        symbols = ["🍒", "🍊", "🍋", "🍉", "⭐", "💎", "7️⃣", "🌸"]
        reels = [random.choice(symbols) for _ in range(3)]
        
        if reels[0] == reels[1] == reels[2]:
            mult = {"7️⃣":6, "💎":5, "⭐":4, "🌸":3}.get(reels[0], 2)
            win_amount = self.bet * mult
            final_win, buff_used = apply_win_buffs(self.ctx.author.id, win_amount)
            update_balance(self.ctx.author.id, final_win - self.bet)
            result = f"JACKPOT! Won {final_win} petals!"
            color = 0x00ff00
        elif reels[0] == reels[1] or reels[1] == reels[2] or reels[0] == reels[2]:
            win_amount = int(self.bet * 1.5)
            final_win, buff_used = apply_win_buffs(self.ctx.author.id, win_amount)
            update_balance(self.ctx.author.id, final_win - self.bet)
            result = f"MATCH! Won {final_win} petals!"
            color = 0xffa500
        else:
            loss_amount = self.bet
            actual_loss, buff_used = apply_loss_protection(self.ctx.author.id, loss_amount)
            update_balance(self.ctx.author.id, -actual_loss)
            result = f"No match! Lost {actual_loss} petals!"
            color = 0xff0000
        
        embed = discord.Embed(title="🎰 Slot Machine", description=f"{reels[0]} | {reels[1]} | {reels[2]}\n\n{result}", color=color)
        embed.add_field(name="New Balance", value=f"{get_balance(self.ctx.author.id):,} petals", inline=False)
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()

class RouletteView(View):
    def __init__(self, ctx, bet):
        super().__init__(timeout=30)
        self.ctx = ctx
        self.bet = bet
    
    @discord.ui.button(label="🔴 RED", style=discord.ButtonStyle.danger)
    async def red(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.spin(interaction, "red")
    
    @discord.ui.button(label="⚫ BLACK", style=discord.ButtonStyle.secondary)
    async def black(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.spin(interaction, "black")
    
    @discord.ui.button(label="🟢 GREEN", style=discord.ButtonStyle.success)
    async def green(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.spin(interaction, "green")
    
    async def spin(self, interaction: discord.Interaction, choice):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Not your game!", ephemeral=True)
            return
        
        num = random.randint(0, 36)
        if num == 0:
            result = "green"
            mult = 12
        elif num in [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]:
            result = "red"
            mult = 2
        else:
            result = "black"
            mult = 2
        
        if choice == result:
            win_amount = self.bet * (mult if result == "green" else 1.8)
            final_win, buff_used = apply_win_buffs(self.ctx.author.id, int(win_amount))
            update_balance(self.ctx.author.id, final_win - self.bet)
            embed = discord.Embed(title="🎡 Roulette", description=f"Ball landed on {num} ({result.upper()})", color=0x00ff00)
            if buff_used:
                embed.add_field(name="🎰 DOUBLE WIN TOKEN ACTIVATED!", value=f"Your win was doubled! {int(win_amount)} → {final_win} petals!", inline=False)
            embed.add_field(name="Result", value=f"You won {final_win} petals!", inline=False)
        else:
            loss_amount = self.bet
            actual_loss, buff_used = apply_loss_protection(self.ctx.author.id, loss_amount)
            update_balance(self.ctx.author.id, -actual_loss)
            embed = discord.Embed(title="🎡 Roulette", description=f"Ball landed on {num} ({result.upper()})", color=0xff0000)
            if buff_used:
                embed.add_field(name="🛡️ PROTECTION AMULET ACTIVATED!", value=f"You lost {loss_amount} petals but were protected! No deduction!", inline=False)
            else:
                embed.add_field(name="Result", value=f"You lost {actual_loss} petals!", inline=False)
        
        embed.add_field(name="New Balance", value=f"{get_balance(self.ctx.author.id):,} petals", inline=False)
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()

# --- MINES GAME ---
class MinesButton(Button):
    def __init__(self, num):
        super().__init__(label="🌸", style=discord.ButtonStyle.secondary, row=(num-1)//3, emoji="🌸")
        self.num = num
    
    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if interaction.user != view.ctx.author:
            await interaction.response.send_message("❌ Not your game!", ephemeral=True)
            return
        
        if self.num in view.bombs:
            view.stop()
            loss_amount = view.bet
            actual_loss, buff_used = apply_loss_protection(view.ctx.author.id, loss_amount)
            update_balance(view.ctx.author.id, -actual_loss)
            for c in view.children:
                if hasattr(c, 'num') and c.num in view.bombs:
                    c.style, c.label, c.emoji = discord.ButtonStyle.danger, "💣", None
                elif hasattr(c, 'num'):
                    c.style, c.disabled = discord.ButtonStyle.secondary, True
                else:
                    c.disabled = True
            
            embed = discord.Embed(title="💥 BOOM!", description=f"You stepped on a bomb!", color=0xff0000)
            if buff_used:
                embed.add_field(name="🛡️ PROTECTION AMULET ACTIVATED!", value=f"You lost {loss_amount} petals but were protected! No deduction!", inline=False)
            else:
                embed.add_field(name="Result", value=f"You lost {actual_loss} petals!", inline=False)
            embed.add_field(name="New Balance", value=f"{get_balance(view.ctx.author.id):,} petals", inline=False)
            await interaction.response.edit_message(embed=embed, view=view)
        else:
            view.revealed += 1
            self.style, self.label, self.disabled, self.emoji = discord.ButtonStyle.success, "🍃", True, None
            
            mult = round(1.15 ** view.revealed, 2)
            val = int(view.bet * mult)
            
            async def co(i):
                view.stop()
                win_amount = val
                final_win, buff_used = apply_win_buffs(view.ctx.author.id, win_amount)
                update_balance(view.ctx.author.id, final_win - view.bet)
                for c in view.children:
                    c.disabled = True
                embed = discord.Embed(title="💰 Cashout!", description=f"You cashed out with {view.revealed} safe tiles!", color=0x00ff00)
                if buff_used:
                    embed.add_field(name="🎰 DOUBLE WIN TOKEN ACTIVATED!", value=f"Your win was doubled! {win_amount} → {final_win} petals!", inline=False)
                embed.add_field(name="Result", value=f"You won {final_win} petals!", inline=False)
                embed.add_field(name="New Balance", value=f"{get_balance(view.ctx.author.id):,} petals", inline=False)
                await i.response.edit_message(embed=embed, view=view)
            
            btn = discord.utils.get(view.children, label="💰 Cashout")
            if not btn:
                btn = Button(label="💰 Cashout", style=discord.ButtonStyle.primary, emoji="💎", row=3)
                btn.callback = co
                view.add_item(btn)
            
            embed = discord.Embed(title="🌸 Minesweeper", description=f"Safe tiles: {view.revealed}\nMultiplier: {mult}x\nPotential win: {val} petals", color=0x00ff88)
            await interaction.response.edit_message(embed=embed, view=view)

class MinesView(View):
    def __init__(self, ctx, bet, bombs):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.bet = bet
        self.bombs = bombs
        self.revealed = 0
        for i in range(1, 10):
            self.add_item(MinesButton(i))

# --- COLOR GAME ---
class ColorButton(Button):
    def __init__(self, name, emoji, style_color):
        super().__init__(label=name, emoji=emoji, style=style_color)
        self.color_name = name
    
    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if interaction.user != view.ctx.author:
            await interaction.response.send_message("❌ Not your game!", ephemeral=True)
            return
        
        view.stop()
        colors = ["🟡 Yellow", "🔴 Red", "⚪ White", "🟢 Green", "🌸 Pink", "🔵 Blue"]
        rolled = [random.choice(colors) for _ in range(3)]
        hits = rolled.count(f"{self.emoji} {self.color_name}")
        
        for c in view.children:
            c.disabled = True
        
        result_display = " 🎲 ".join(rolled)
        
        if hits > 0:
            win_amount = view.bet * hits
            final_win, buff_used = apply_win_buffs(view.ctx.author.id, win_amount)
            update_balance(view.ctx.author.id, final_win - view.bet)
            embed = discord.Embed(title="🎉 Victory!", description=f"Result: {result_display}\nGuessed {self.color_name} - appeared {hits} times!", color=0x00ff00)
            if buff_used:
                embed.add_field(name="🎰 DOUBLE WIN TOKEN ACTIVATED!", value=f"Your win was doubled! {win_amount} → {final_win} petals!", inline=False)
            embed.add_field(name="Result", value=f"You won {final_win} petals!", inline=False)
        else:
            loss_amount = view.bet
            actual_loss, buff_used = apply_loss_protection(view.ctx.author.id, loss_amount)
            update_balance(view.ctx.author.id, -actual_loss)
            embed = discord.Embed(title="💔 Defeat", description=f"Result: {result_display}\nGuessed {self.color_name} - didn't appear!", color=0xff0000)
            if buff_used:
                embed.add_field(name="🛡️ PROTECTION AMULET ACTIVATED!", value=f"You lost {loss_amount} petals but were protected! No deduction!", inline=False)
            else:
                embed.add_field(name="Result", value=f"You lost {actual_loss} petals!", inline=False)
        
        embed.add_field(name="New Balance", value=f"{get_balance(view.ctx.author.id):,} petals", inline=False)
        await interaction.response.edit_message(embed=embed, view=view)

class ColorView(View):
    def __init__(self, ctx, bet):
        super().__init__(timeout=30)
        self.ctx = ctx
        self.bet = bet
        
        color_configs = [
            ("Yellow", "🟡", discord.ButtonStyle.primary),
            ("Red", "🔴", discord.ButtonStyle.danger),
            ("White", "⚪", discord.ButtonStyle.secondary),
            ("Green", "🟢", discord.ButtonStyle.success),
            ("Pink", "🌸", discord.ButtonStyle.primary),
            ("Blue", "🔵", discord.ButtonStyle.primary)
        ]
        
        for name, emoji, style in color_configs:
            self.add_item(ColorButton(name, emoji, style))

# --- HIGHER LOWER GAME ---
class HigherLowerView(View):
    def __init__(self, ctx, bet, current_card, card_display, card_emoji):
        super().__init__(timeout=30)
        self.ctx = ctx
        self.bet = bet
        self.current_card = current_card
        self.card_display = card_display
        self.card_emoji = card_emoji
        self.game_active = True
    
    @discord.ui.button(label="⬆️ HIGHER", style=discord.ButtonStyle.success, emoji="⬆️")
    async def higher(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.guess(interaction, "higher")
    
    @discord.ui.button(label="⬇️ LOWER", style=discord.ButtonStyle.danger, emoji="⬇️")
    async def lower(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.guess(interaction, "lower")
    
    async def guess(self, interaction: discord.Interaction, choice):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Not your game!", ephemeral=True)
            return
        
        if not self.game_active:
            return
        
        next_card = random.randint(1, 13)
        card_names = {1:"A", 11:"J", 12:"Q", 13:"K"}
        next_display = card_names.get(next_card, str(next_card))
        
        card_emojis = {
            1: "🃏", 2: "2️⃣", 3: "3️⃣", 4: "4️⃣", 5: "5️⃣",
            6: "6️⃣", 7: "7️⃣", 8: "8️⃣", 9: "9️⃣", 10: "🔟",
            11: "👑", 12: "👸", 13: "🤴"
        }
        next_emoji = card_emojis.get(next_card, "🎴")
        
        current_card_visual = f"{self.card_emoji} **{self.card_display}**"
        next_card_visual = f"{next_emoji} **{next_display}**"
        
        if (choice == "higher" and next_card > self.current_card) or (choice == "lower" and next_card < self.current_card):
            win_amount = int(self.bet * 1.8)
            final_win, buff_used = apply_win_buffs(self.ctx.author.id, win_amount)
            update_balance(self.ctx.author.id, final_win - self.bet)
            embed = discord.Embed(title="🎴 Higher/Lower", description=f"Your card: {current_card_visual}\nNext card: {next_card_visual}", color=0x00ff00)
            if buff_used:
                embed.add_field(name="🎰 DOUBLE WIN TOKEN ACTIVATED!", value=f"Your win was doubled! {win_amount} → {final_win} petals!", inline=False)
            embed.add_field(name="Result", value=f"{choice.upper()} was correct! You won {final_win} petals!", inline=False)
        elif next_card == self.current_card:
            embed = discord.Embed(title="🎴 Higher/Lower", description=f"Your card: {current_card_visual}\nNext card: {next_card_visual}\n\nTie! Bet returned!", color=0xffa500)
        else:
            loss_amount = self.bet
            actual_loss, buff_used = apply_loss_protection(self.ctx.author.id, loss_amount)
            update_balance(self.ctx.author.id, -actual_loss)
            embed = discord.Embed(title="🎴 Higher/Lower", description=f"Your card: {current_card_visual}\nNext card: {next_card_visual}", color=0xff0000)
            if buff_used:
                embed.add_field(name="🛡️ PROTECTION AMULET ACTIVATED!", value=f"You lost {loss_amount} petals but were protected! No deduction!", inline=False)
            else:
                embed.add_field(name="Result", value=f"{choice.upper()} was wrong! You lost {actual_loss} petals!", inline=False)
        
        embed.add_field(name="New Balance", value=f"{get_balance(self.ctx.author.id):,} petals", inline=False)
        self.game_active = False
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()

# --- TOWER CLIMB GAME ---
class TowerView(View):
    def __init__(self, ctx, bet):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.bet = bet
        self.floor = 1
        self.multiplier = 1.0
        self.update_display()
    
    def update_display(self):
        self.multiplier = round(1.1 ** self.floor, 2)
    
    @discord.ui.button(label="⬆️ CLIMB", style=discord.ButtonStyle.success, emoji="⬆️")
    async def climb(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Not your game!", ephemeral=True)
            return
        
        if random.random() < 0.4:
            loss_amount = self.bet
            actual_loss, buff_used = apply_loss_protection(self.ctx.author.id, loss_amount)
            update_balance(self.ctx.author.id, -actual_loss)
            embed = discord.Embed(title="🏰 Tower Climb", description=f"You fell from floor {self.floor}!", color=0xff0000)
            if buff_used:
                embed.add_field(name="🛡️ PROTECTION AMULET ACTIVATED!", value=f"You lost {loss_amount} petals but were protected! No deduction!", inline=False)
            else:
                embed.add_field(name="Result", value=f"You lost {actual_loss} petals!", inline=False)
            embed.add_field(name="New Balance", value=f"{get_balance(self.ctx.author.id):,} petals", inline=False)
            await interaction.response.edit_message(embed=embed, view=None)
            self.stop()
        else:
            self.floor += 1
            self.update_display()
            potential_win = int(self.bet * self.multiplier)
            embed = discord.Embed(title="🏰 Tower Climb", description=f"You reached floor {self.floor}!\nMultiplier: {self.multiplier}x\nPotential win: {potential_win} petals\n\nClick CASHOUT or CLIMB higher!", color=0xffa500)
            await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="💰 CASHOUT", style=discord.ButtonStyle.primary, emoji="💰")
    async def cashout(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Not your game!", ephemeral=True)
            return
        
        win_amount = int(self.bet * self.multiplier)
        final_win, buff_used = apply_win_buffs(self.ctx.author.id, win_amount)
        update_balance(self.ctx.author.id, final_win - self.bet)
        embed = discord.Embed(title="🏰 Tower Climb", description=f"You cashed out at floor {self.floor}!", color=0x00ff00)
        if buff_used:
            embed.add_field(name="🎰 DOUBLE WIN TOKEN ACTIVATED!", value=f"Your win was doubled! {win_amount} → {final_win} petals!", inline=False)
        embed.add_field(name="Result", value=f"You won {final_win} petals!", inline=False)
        embed.add_field(name="New Balance", value=f"{get_balance(self.ctx.author.id):,} petals", inline=False)
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()

# --- SCRATCH CARD GAME ---
class ScratchView(View):
    def __init__(self, ctx, bet):
        super().__init__(timeout=30)
        self.ctx = ctx
        self.bet = bet
        self.revealed = [False, False, False]
        self.values = [random.randint(1, 10) for _ in range(3)]
    
    @discord.ui.button(label="❓", style=discord.ButtonStyle.secondary, emoji="🎫", row=0)
    async def scratch1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.reveal(interaction, 0, button)
    
    @discord.ui.button(label="❓", style=discord.ButtonStyle.secondary, emoji="🎫", row=0)
    async def scratch2(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.reveal(interaction, 1, button)
    
    @discord.ui.button(label="❓", style=discord.ButtonStyle.secondary, emoji="🎫", row=0)
    async def scratch3(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.reveal(interaction, 2, button)
    
    async def reveal(self, interaction: discord.Interaction, index, button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Not your game!", ephemeral=True)
            return
        
        if self.revealed[index]:
            return
        
        self.revealed[index] = True
        button.label = str(self.values[index])
        button.disabled = True
        
        if all(self.revealed):
            if self.values[0] == self.values[1] == self.values[2]:
                win_amount = self.bet * 3
                final_win, buff_used = apply_win_buffs(self.ctx.author.id, win_amount)
                update_balance(self.ctx.author.id, final_win - self.bet)
                embed = discord.Embed(title="🎫 Scratch Card", description=f"{self.values[0]} | {self.values[1]} | {self.values[2]}", color=0x00ff00)
                if buff_used:
                    embed.add_field(name="🎰 DOUBLE WIN TOKEN ACTIVATED!", value=f"Your win was doubled! {win_amount} → {final_win} petals!", inline=False)
                embed.add_field(name="Result", value=f"JACKPOT! You won {final_win} petals!", inline=False)
            elif self.values[0] == self.values[1] or self.values[1] == self.values[2] or self.values[0] == self.values[2]:
                win_amount = int(self.bet * 1.5)
                final_win, buff_used = apply_win_buffs(self.ctx.author.id, win_amount)
                update_balance(self.ctx.author.id, final_win - self.bet)
                embed = discord.Embed(title="🎫 Scratch Card", description=f"{self.values[0]} | {self.values[1]} | {self.values[2]}", color=0xffa500)
                if buff_used:
                    embed.add_field(name="🎰 DOUBLE WIN TOKEN ACTIVATED!", value=f"Your win was doubled! {win_amount} → {final_win} petals!", inline=False)
                embed.add_field(name="Result", value=f"MATCH! You won {final_win} petals!", inline=False)
            else:
                loss_amount = self.bet
                actual_loss, buff_used = apply_loss_protection(self.ctx.author.id, loss_amount)
                update_balance(self.ctx.author.id, -actual_loss)
                embed = discord.Embed(title="🎫 Scratch Card", description=f"{self.values[0]} | {self.values[1]} | {self.values[2]}", color=0xff0000)
                if buff_used:
                    embed.add_field(name="🛡️ PROTECTION AMULET ACTIVATED!", value=f"You lost {loss_amount} petals but were protected! No deduction!", inline=False)
                else:
                    embed.add_field(name="Result", value=f"No match! You lost {actual_loss} petals!", inline=False)
            embed.add_field(name="New Balance", value=f"{get_balance(self.ctx.author.id):,} petals", inline=False)
            await interaction.response.edit_message(embed=embed, view=None)
            self.stop()
        else:
            remaining = 3 - sum(self.revealed)
            await interaction.response.edit_message(content=f"Scratched {self.values[index]}! {remaining} left!", view=self)

# --- TREASURE HUNT GAME ---
class TreasureHuntView(View):
    def __init__(self, ctx, bet):
        super().__init__(timeout=30)
        self.ctx = ctx
        self.bet = bet
        self.treasure_position = random.randint(1, 6)
        self.attempts = 0
        self.max_attempts = 2
    
    @discord.ui.button(label="📍 1", style=discord.ButtonStyle.secondary, row=0)
    async def spot1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.hunt(interaction, 1, button)
    
    @discord.ui.button(label="📍 2", style=discord.ButtonStyle.secondary, row=0)
    async def spot2(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.hunt(interaction, 2, button)
    
    @discord.ui.button(label="📍 3", style=discord.ButtonStyle.secondary, row=0)
    async def spot3(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.hunt(interaction, 3, button)
    
    @discord.ui.button(label="📍 4", style=discord.ButtonStyle.secondary, row=1)
    async def spot4(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.hunt(interaction, 4, button)
    
    @discord.ui.button(label="📍 5", style=discord.ButtonStyle.secondary, row=1)
    async def spot5(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.hunt(interaction, 5, button)
    
    @discord.ui.button(label="📍 6", style=discord.ButtonStyle.secondary, row=1)
    async def spot6(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.hunt(interaction, 6, button)
    
    async def hunt(self, interaction: discord.Interaction, spot, button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Not your game!", ephemeral=True)
            return
        
        if self.attempts >= self.max_attempts:
            return
        
        self.attempts += 1
        if spot == self.treasure_position:
            win_amount = int(self.bet * 2.5)
            final_win, buff_used = apply_win_buffs(self.ctx.author.id, win_amount)
            update_balance(self.ctx.author.id, final_win - self.bet)
            embed = discord.Embed(title="💎 Treasure Hunt", description=f"You found the treasure at spot {spot}!", color=0x00ff00)
            if buff_used:
                embed.add_field(name="🎰 DOUBLE WIN TOKEN ACTIVATED!", value=f"Your win was doubled! {win_amount} → {final_win} petals!", inline=False)
            embed.add_field(name="Result", value=f"You won {final_win} petals!", inline=False)
            embed.add_field(name="New Balance", value=f"{get_balance(self.ctx.author.id):,} petals", inline=False)
            await interaction.response.edit_message(embed=embed, view=None)
            self.stop()
        elif self.attempts >= self.max_attempts:
            loss_amount = self.bet
            actual_loss, buff_used = apply_loss_protection(self.ctx.author.id, loss_amount)
            update_balance(self.ctx.author.id, -actual_loss)
            embed = discord.Embed(title="💎 Treasure Hunt", description=f"You didn't find the treasure! It was at spot {self.treasure_position}.", color=0xff0000)
            if buff_used:
                embed.add_field(name="🛡️ PROTECTION AMULET ACTIVATED!", value=f"You lost {loss_amount} petals but were protected! No deduction!", inline=False)
            else:
                embed.add_field(name="Result", value=f"You lost {actual_loss} petals!", inline=False)
            embed.add_field(name="New Balance", value=f"{get_balance(self.ctx.author.id):,} petals", inline=False)
            await interaction.response.edit_message(embed=embed, view=None)
            self.stop()
        else:
            button.disabled = True
            remaining = self.max_attempts - self.attempts
            await interaction.response.edit_message(content=f"Nothing at spot {spot}! {remaining} attempt(s) left!", view=self)

# --- RUSSIAN ROULETTE (3 Bullets) ---
class RussianRouletteView(View):
    def __init__(self, ctx, bet):
        super().__init__(timeout=30)
        self.ctx = ctx
        self.bet = bet
        chambers = [False] * 6
        bullet_positions = random.sample(range(6), 3)
        for pos in bullet_positions:
            chambers[pos] = True
        self.chambers = chambers
        self.current_chamber = 0
        self.spins = 0
        self.max_spins = 3
    
    @discord.ui.button(label="🔫 PULL TRIGGER", style=discord.ButtonStyle.danger, emoji="🔫", row=0)
    async def pull(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Not your game!", ephemeral=True)
            return
        
        self.spins += 1
        
        if self.chambers[self.current_chamber]:
            loss_amount = self.bet
            actual_loss, buff_used = apply_loss_protection(self.ctx.author.id, loss_amount)
            update_balance(self.ctx.author.id, -actual_loss)
            embed = discord.Embed(title="💀 RUSSIAN ROULETTE", description=f"BANG! Chamber {self.current_chamber + 1} had a bullet!", color=0xff0000)
            if buff_used:
                embed.add_field(name="🛡️ PROTECTION AMULET ACTIVATED!", value=f"You lost {loss_amount} petals but were protected! No deduction!", inline=False)
            else:
                embed.add_field(name="Result", value=f"You lost {actual_loss} petals!", inline=False)
            embed.add_field(name="New Balance", value=f"{get_balance(self.ctx.author.id):,} petals", inline=False)
            await interaction.response.edit_message(embed=embed, view=None)
            self.stop()
            return
        
        self.current_chamber += 1
        remaining_bullets = sum(self.chambers[self.current_chamber:])
        
        if self.spins >= self.max_spins:
            win_amount = self.bet * 3
            final_win, buff_used = apply_win_buffs(self.ctx.author.id, win_amount)
            update_balance(self.ctx.author.id, final_win - self.bet)
            embed = discord.Embed(title="🔫 RUSSIAN ROULETTE", description=f"You survived {self.max_spins} pulls!", color=0x00ff00)
            if buff_used:
                embed.add_field(name="🎰 DOUBLE WIN TOKEN ACTIVATED!", value=f"Your win was doubled! {win_amount} → {final_win} petals!", inline=False)
            embed.add_field(name="Result", value=f"You won {final_win} petals!", inline=False)
            embed.add_field(name="New Balance", value=f"{get_balance(self.ctx.author.id):,} petals", inline=False)
            await interaction.response.edit_message(embed=embed, view=None)
            self.stop()
            return
        
        remaining_pulls = self.max_spins - self.spins
        embed = discord.Embed(title="🔫 RUSSIAN ROULETTE", description=f"Click! Chamber {self.current_chamber} was empty!\n{remaining_bullets} bullets left in {6 - self.current_chamber} chambers.\nYou have {remaining_pulls} pull(s) left.", color=0xffa500)
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="💰 CASHOUT", style=discord.ButtonStyle.success, emoji="💰", row=1)
    async def cashout(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Not your game!", ephemeral=True)
            return
        
        if self.spins == 0:
            cashout_amount = int(self.bet * 0.7)
        elif self.spins == 1:
            cashout_amount = int(self.bet * 1.2)
        elif self.spins == 2:
            cashout_amount = int(self.bet * 2.0)
        else:
            cashout_amount = int(self.bet * 2.8)
        
        update_balance(self.ctx.author.id, cashout_amount - self.bet)
        embed = discord.Embed(title="🔫 RUSSIAN ROULETTE", description=f"You cashed out after {self.spins} pull(s) and won {cashout_amount} petals!", color=0x00ff00)
        embed.add_field(name="New Balance", value=f"{get_balance(self.ctx.author.id):,} petals", inline=False)
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()

# --- HORSE RACING GAME ---
class RaceView(View):
    def __init__(self, ctx, bet):
        super().__init__(timeout=30)
        self.ctx = ctx
        self.bet = bet
        self.horses = ["🐎 Thunder", "⚡ Lightning", "🔥 Blaze", "💨 Wind", "🌙 Shadow"]
    
    @discord.ui.button(label="🐎 Thunder", style=discord.ButtonStyle.primary, row=0)
    async def horse1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.race(interaction, 0)
    
    @discord.ui.button(label="⚡ Lightning", style=discord.ButtonStyle.primary, row=0)
    async def horse2(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.race(interaction, 1)
    
    @discord.ui.button(label="🔥 Blaze", style=discord.ButtonStyle.primary, row=0)
    async def horse3(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.race(interaction, 2)
    
    @discord.ui.button(label="💨 Wind", style=discord.ButtonStyle.primary, row=1)
    async def horse4(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.race(interaction, 3)
    
    @discord.ui.button(label="🌙 Shadow", style=discord.ButtonStyle.primary, row=1)
    async def horse5(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.race(interaction, 4)
    
    async def race(self, interaction: discord.Interaction, choice):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Not your game!", ephemeral=True)
            return
        
        winner = random.randint(0, 4)
        if choice == winner:
            win_amount = int(self.bet * 3.5)
            final_win, buff_used = apply_win_buffs(self.ctx.author.id, win_amount)
            update_balance(self.ctx.author.id, final_win - self.bet)
            embed = discord.Embed(title="🏇 Horse Racing", description=f"Winner: {self.horses[winner]}\nYour bet: {self.horses[choice]}", color=0x00ff00)
            if buff_used:
                embed.add_field(name="🎰 DOUBLE WIN TOKEN ACTIVATED!", value=f"Your win was doubled! {win_amount} → {final_win} petals!", inline=False)
            embed.add_field(name="Result", value=f"You won {final_win} petals!", inline=False)
        else:
            loss_amount = self.bet
            actual_loss, buff_used = apply_loss_protection(self.ctx.author.id, loss_amount)
            update_balance(self.ctx.author.id, -actual_loss)
            embed = discord.Embed(title="🏇 Horse Racing", description=f"Winner: {self.horses[winner]}\nYour bet: {self.horses[choice]}", color=0xff0000)
            if buff_used:
                embed.add_field(name="🛡️ PROTECTION AMULET ACTIVATED!", value=f"You lost {loss_amount} petals but were protected! No deduction!", inline=False)
            else:
                embed.add_field(name="Result", value=f"You lost {actual_loss} petals!", inline=False)
        
        embed.add_field(name="New Balance", value=f"{get_balance(self.ctx.author.id):,} petals", inline=False)
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()

# --- POKER GAME ---
class PokerView(View):
    def __init__(self, ctx, bet):
        super().__init__(timeout=30)
        self.ctx = ctx
        self.bet = bet
    
    @discord.ui.button(label="🃏 DEAL CARDS", style=discord.ButtonStyle.primary, emoji="🃏", row=0)
    async def deal(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Not your game!", ephemeral=True)
            return
        
        suits = ["♥️", "♦️", "♣️", "♠️"]
        values = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
        
        player_cards = [(random.choice(values), random.choice(suits)) for _ in range(5)]
        bot_cards = [(random.choice(values), random.choice(suits)) for _ in range(5)]
        
        player_display = " ".join([f"{v}{s}" for v, s in player_cards])
        bot_display = " ".join([f"{v}{s}" for v, s in bot_cards])
        
        player_score = self.evaluate_hand(player_cards)
        bot_score = self.evaluate_hand(bot_cards)
        
        if player_score > bot_score:
            win_amount = int(self.bet * 1.8)
            final_win, buff_used = apply_win_buffs(self.ctx.author.id, win_amount)
            update_balance(self.ctx.author.id, final_win - self.bet)
            result = f"You won {final_win} petals!"
            color = 0x00ff00
        else:
            loss_amount = self.bet
            actual_loss, buff_used = apply_loss_protection(self.ctx.author.id, loss_amount)
            update_balance(self.ctx.author.id, -actual_loss)
            result = f"You lost {actual_loss} petals!"
            color = 0xff0000
        
        embed = discord.Embed(title="🃏 Poker Showdown", description=f"Your hand: {player_display}\nBot's hand: {bot_display}\n\n{result}", color=color)
        embed.add_field(name="New Balance", value=f"{get_balance(self.ctx.author.id):,} petals", inline=False)
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()
    
    def evaluate_hand(self, cards):
        values = [c[0] for c in cards]
        value_counts = {}
        for v in values:
            value_counts[v] = value_counts.get(v, 0) + 1
        
        if 5 in value_counts.values():
            return 8
        elif 4 in value_counts.values():
            return 7
        elif 3 in value_counts.values() and 2 in value_counts.values():
            return 6
        elif 3 in value_counts.values():
            return 3
        elif list(value_counts.values()).count(2) == 2:
            return 2
        elif 2 in value_counts.values():
            return 1
        return 0

# --- DUEL VIEW ---
class DuelView(View):
    def __init__(self, ctx, opponent, bet):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.opponent = opponent
        self.bet = bet
        self.accepted = False
    
    @discord.ui.button(label="⚔️ Accept", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.opponent:
            await interaction.response.send_message("❌ Not your duel!", ephemeral=True)
            return
        
        if get_balance(self.ctx.author.id) < self.bet:
            await interaction.response.send_message(f"❌ {self.ctx.author.name} doesn't have enough petals!", ephemeral=True)
            return
        if get_balance(self.opponent.id) < self.bet:
            await interaction.response.send_message(f"❌ You don't have enough petals!", ephemeral=True)
            return
        
        self.accepted = True
        update_balance(self.ctx.author.id, -self.bet)
        update_balance(self.opponent.id, -self.bet)
        
        winner = random.choice([self.ctx.author, self.opponent])
        update_balance(winner.id, self.bet * 2)
        
        embed = discord.Embed(title="⚔️ Duel Result", description=f"{winner.mention} wins the duel and gets {self.bet * 2} petals!", color=0x00ff00)
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()
    
    @discord.ui.button(label="❌ Decline", style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.opponent:
            await interaction.response.send_message("❌ Not your duel!", ephemeral=True)
            return
        await interaction.response.edit_message(content="❌ Duel declined!", embed=None, view=None)
        self.stop()

# --- COMMANDS ---

@bot.command()
async def help(ctx):
    embed = discord.Embed(title="🌸 Blossom Garden Bot", description="Here are all my commands:", color=0xffb7c5)
    embed.add_field(name="💰 **Economy**", value="`bal`, `lb`, `daily`, `weekly`, `hourly`, `beg`, `farm`, `hunt`, `work`", inline=False)
    embed.add_field(name="🎲 **Games**", value="`crash`, `mines`, `color`, `coinflip`, `dice`, `slots`, `roulette`, `blackjack`, `rps`, `higherlower`, `tower`, `scratch`, `treasure`, `roulettegun`, `race`, `poker`", inline=False)
    embed.add_field(name="🛒 **Shop**", value="`shop`, `petshop`, `inventory`, `buffs`", inline=False)
    embed.add_field(name="🐾 **Pets**", value="`mypets`, `pet`, `petstats`", inline=False)
    embed.add_field(name="⚔️ **Duel**", value="`duel @user <bet>`", inline=False)
    embed.add_field(name="🎁 **Gifting**", value="`gift @user <amount>`, `giftstats`", inline=False)
    embed.add_field(name="🎟️ **Redeem**", value="`redeem`", inline=False)
    embed.set_footer(text="🌸 Type b!inventory to see and use your items with buttons!")
    await ctx.send(embed=embed)

@bot.command()
async def bal(ctx):
    balance = get_balance(ctx.author.id)
    emoji = "👑" if balance >= 10000 else "💎" if balance >= 5000 else "🌟" if balance >= 1000 else "🌸"
    embed = discord.Embed(title=f"{emoji} {ctx.author.name}'s Balance", description=f"**{balance:,} petals**", color=0xff69b4)
    await ctx.send(embed=embed)

@bot.command()
async def lb(ctx):
    if not economy:
        await ctx.send("No data yet!")
        return
    top = sorted(economy.items(), key=lambda x: x[1], reverse=True)[:10]
    desc = ""
    for i, (uid, bal) in enumerate(top, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "📊"
        user = await bot.fetch_user(uid)
        desc += f"{medal} **{i}.** {user.name} — `{bal:,}` petals\n"
    embed = discord.Embed(title="🏆 Leaderboard", description=desc, color=0xffb7c5)
    await ctx.send(embed=embed)

@bot.command()
async def daily(ctx):
    uid = ctx.author.id
    on_cd, remaining = check_cooldown(daily_cooldown, uid)
    if on_cd:
        await ctx.send(f"⏰ Come back in {format_time(remaining)}")
        return
    reward = random.randint(300, 700) * get_daily_multiplier(uid)
    update_balance(uid, reward)
    set_cooldown(daily_cooldown, uid)
    await ctx.send(f"📅 You received {reward} petals!")

@bot.command()
async def weekly(ctx):
    uid = ctx.author.id
    on_cd, remaining = check_cooldown(weekly_cooldown, uid, 604800)
    if on_cd:
        await ctx.send(f"⏰ Come back in {format_time(remaining)}")
        return
    reward = random.randint(2000, 5000) * get_daily_multiplier(uid)
    update_balance(uid, reward)
    set_cooldown(weekly_cooldown, uid)
    await ctx.send(f"📅 Weekly reward: {reward} petals!")

@bot.command()
async def hourly(ctx):
    uid = ctx.author.id
    on_cd, remaining = check_cooldown(hourly_cooldown, uid, 3600)
    if on_cd:
        await ctx.send(f"⏰ Come back in {format_time(remaining)}")
        return
    reward = random.randint(30, 80) * get_daily_multiplier(uid)
    update_balance(uid, reward)
    set_cooldown(hourly_cooldown, uid)
    await ctx.send(f"⏰ Hourly reward: {reward} petals!")

@bot.command()
async def beg(ctx):
    uid = ctx.author.id
    on_cd, remaining = check_cooldown(beg_cooldown, uid)
    if on_cd:
        await ctx.send(f"⏰ Come back tomorrow! ({format_time(remaining)})")
        return
    reward = random.randint(30, 100) * get_daily_multiplier(uid)
    update_balance(uid, reward)
    set_cooldown(beg_cooldown, uid)
    await ctx.send(f"🌸 A kind stranger gave you {reward} petals!")

@bot.command()
async def farm(ctx):
    uid = ctx.author.id
    on_cd, remaining = check_cooldown(farm_cooldown, uid)
    if on_cd:
        await ctx.send(f"⏰ Crops need time! ({format_time(remaining)})")
        return
    reward = random.randint(120, 300) * get_daily_multiplier(uid)
    update_balance(uid, reward)
    set_cooldown(farm_cooldown, uid)
    await ctx.send(f"🚜 You harvested {reward} petals!")

@bot.command()
async def hunt(ctx):
    uid = ctx.author.id
    on_cd, remaining = check_cooldown(hunt_cooldown, uid)
    if on_cd:
        await ctx.send(f"⏰ Forest needs rest! ({format_time(remaining)})")
        return
    reward = random.randint(60, 200) * get_daily_multiplier(uid)
    update_balance(uid, reward)
    set_cooldown(hunt_cooldown, uid)
    await ctx.send(f"🏹 You found {reward} petals while hunting!")

@bot.command()
async def work(ctx):
    uid = ctx.author.id
    on_cd, remaining = check_cooldown(work_cooldown, uid)
    if on_cd:
        await ctx.send(f"⏰ You're tired! ({format_time(remaining)})")
        return
    reward = random.randint(90, 250) * get_daily_multiplier(uid)
    update_balance(uid, reward)
    set_cooldown(work_cooldown, uid)
    await ctx.send(f"💼 You earned {reward} petals from work!")

# Game Commands
@bot.command()
async def crash(ctx, bet: int):
    if bet <= 0 or get_balance(ctx.author.id) < bet:
        await ctx.send("❌ Invalid bet or insufficient balance!")
        return
    embed = discord.Embed(title="✈️ Crash Game", description=f"Multiplier: 1.00x", color=0xffa500)
    msg = await ctx.send(embed=embed)
    view = CrashView(ctx, bet)
    await view.start(msg)

@bot.command()
async def coinflip(ctx, bet: int):
    if bet <= 0 or get_balance(ctx.author.id) < bet:
        await ctx.send("❌ Invalid bet or insufficient balance!")
        return
    embed = discord.Embed(title="🪙 Coinflip", description=f"Bet: {bet} petals\nChoose Heads or Tails", color=0xffa500)
    await ctx.send(embed=embed, view=CoinflipView(ctx, bet))

@bot.command()
async def dice(ctx, bet: int):
    if bet <= 0 or get_balance(ctx.author.id) < bet:
        await ctx.send("❌ Invalid bet or insufficient balance!")
        return
    embed = discord.Embed(title="🎲 Dice Duel", description=f"Bet: {bet} petals\nClick ROLL to play!", color=0xffa500)
    await ctx.send(embed=embed, view=DiceDuelView(ctx, bet))

@bot.command()
async def slots(ctx, bet: int):
    if bet <= 0 or get_balance(ctx.author.id) < bet:
        await ctx.send("❌ Invalid bet or insufficient balance!")
        return
    embed = discord.Embed(title="🎰 Slot Machine", description=f"Bet: {bet} petals\nClick SPIN to play!", color=0xffa500)
    await ctx.send(embed=embed, view=SlotMachineView(ctx, bet))

@bot.command()
async def roulette(ctx, bet: int):
    if bet <= 0 or get_balance(ctx.author.id) < bet:
        await ctx.send("❌ Invalid bet or insufficient balance!")
        return
    embed = discord.Embed(title="🎡 Roulette", description=f"Bet: {bet} petals\nChoose Red, Black, or Green", color=0xffa500)
    await ctx.send(embed=embed, view=RouletteView(ctx, bet))

@bot.command()
async def mines(ctx, bet: int):
    if bet <= 0 or get_balance(ctx.author.id) < bet:
        await ctx.send("❌ Invalid bet or insufficient balance!")
        return
    bombs = random.sample(range(1, 10), 4)
    embed = discord.Embed(title="💣 Minesweeper", description=f"Bet: {bet} petals\nFind safe flowers! (4 bombs hidden)", color=0xff69b4)
    await ctx.send(embed=embed, view=MinesView(ctx, bet, bombs))

@bot.command()
async def color(ctx, bet: int):
    if bet <= 0 or get_balance(ctx.author.id) < bet:
        await ctx.send("❌ Invalid bet or insufficient balance!")
        return
    embed = discord.Embed(title="🎨 Color Predictor", description=f"Bet: {bet} petals\nPick a color!", color=0xff69b4)
    await ctx.send(embed=embed, view=ColorView(ctx, bet))

@bot.command()
async def higherlower(ctx, bet: int):
    if bet <= 0 or get_balance(ctx.author.id) < bet:
        await ctx.send("❌ Invalid bet or insufficient balance!")
        return
    
    card_names = {1:"A", 11:"J", 12:"Q", 13:"K"}
    current_card = random.randint(1, 13)
    current_display = card_names.get(current_card, str(current_card))
    
    card_emojis = {
        1: "🃏", 2: "2️⃣", 3: "3️⃣", 4: "4️⃣", 5: "5️⃣",
        6: "6️⃣", 7: "7️⃣", 8: "8️⃣", 9: "9️⃣", 10: "🔟",
        11: "👑", 12: "👸", 13: "🤴"
    }
    current_emoji = card_emojis.get(current_card, "🎴")
    
    embed = discord.Embed(title="🎴 Higher or Lower", description=f"Your card: {current_emoji} {current_display}\nBet: {bet} petals\n\nWill the next card be HIGHER or LOWER?", color=0xffa500)
    await ctx.send(embed=embed, view=HigherLowerView(ctx, bet, current_card, current_display, current_emoji))

@bot.command()
async def tower(ctx, bet: int):
    if bet <= 0 or get_balance(ctx.author.id) < bet:
        await ctx.send("❌ Invalid bet or insufficient balance!")
        return
    embed = discord.Embed(title="🏰 Tower Climb", description=f"Bet: {bet} petals\nClimb the tower and cash out!", color=0xffa500)
    await ctx.send(embed=embed, view=TowerView(ctx, bet))

@bot.command()
async def scratch(ctx, bet: int):
    if bet <= 0 or get_balance(ctx.author.id) < bet:
        await ctx.send("❌ Invalid bet or insufficient balance!")
        return
    embed = discord.Embed(title="🎫 Scratch Card", description=f"Bet: {bet} petals\nScratch all three cards!", color=0xffa500)
    await ctx.send(embed=embed, view=ScratchView(ctx, bet))

@bot.command()
async def treasure(ctx, bet: int):
    if bet <= 0 or get_balance(ctx.author.id) < bet:
        await ctx.send("❌ Invalid bet or insufficient balance!")
        return
    embed = discord.Embed(title="💎 Treasure Hunt", description=f"Bet: {bet} petals\nFind the treasure in 2 attempts!", color=0xffa500)
    await ctx.send(embed=embed, view=TreasureHuntView(ctx, bet))

@bot.command()
async def roulettegun(ctx, bet: int):
    if bet <= 0 or get_balance(ctx.author.id) < bet:
        await ctx.send("❌ Invalid bet or insufficient balance!")
        return
    embed = discord.Embed(title="💀 Russian Roulette", description=f"Bet: {bet} petals\n⚠️ 3 BULLETS, 6 CHAMBERS!\nPull the trigger up to 3 times or cash out early!", color=0xff0000)
    await ctx.send(embed=embed, view=RussianRouletteView(ctx, bet))

@bot.command()
async def race(ctx, bet: int):
    if bet <= 0 or get_balance(ctx.author.id) < bet:
        await ctx.send("❌ Invalid bet or insufficient balance!")
        return
    embed = discord.Embed(title="🏇 Horse Racing", description=f"Bet: {bet} petals\nPick a horse to win!", color=0xffa500)
    await ctx.send(embed=embed, view=RaceView(ctx, bet))

@bot.command()
async def poker(ctx, bet: int):
    if bet <= 0 or get_balance(ctx.author.id) < bet:
        await ctx.send("❌ Invalid bet or insufficient balance!")
        return
    embed = discord.Embed(title="🃏 Poker", description=f"Bet: {bet} petals\nFace off against the bot!", color=0xffa500)
    await ctx.send(embed=embed, view=PokerView(ctx, bet))

@bot.command()
async def blackjack(ctx, bet: int):
    if bet <= 0 or get_balance(ctx.author.id) < bet:
        await ctx.send("❌ Invalid bet or insufficient balance!")
        return
    
    player = [random.randint(1, 11), random.randint(1, 11)]
    dealer = [random.randint(1, 11), random.randint(1, 11)]
    
    embed = discord.Embed(title="🃏 Blackjack", description=f"Your hand: {player} = {sum(player)}\nDealer shows: [{dealer[0]}, ?]\n\nType `hit` or `stand`", color=0xff69b4)
    await ctx.send(embed=embed)
    
    def check(m): return m.author == ctx.author and m.content.lower() in ['hit', 'stand']
    
    while sum(player) < 21:
        try:
            msg = await bot.wait_for('message', check=check, timeout=30)
            if msg.content.lower() == 'hit':
                player.append(random.randint(1, 11))
                if sum(player) > 21:
                    break
                await ctx.send(f"Your hand: {player} = {sum(player)}")
            else:
                break
        except:
            break
    
    while sum(dealer) < 17:
        dealer.append(random.randint(1, 11))
    
    psum, dsum = sum(player), sum(dealer)
    
    if psum > 21 or (dsum <= 21 and psum < dsum):
        loss_amount = bet
        actual_loss, buff_used = apply_loss_protection(ctx.author.id, loss_amount)
        update_balance(ctx.author.id, -actual_loss)
        if buff_used:
            result = f"You lost {loss_amount} petals but were protected!"
        else:
            result = f"You lost {actual_loss} petals!"
        color = 0xff0000
    elif dsum > 21 or psum > dsum:
        win_amount = int(bet * 0.95)
        final_win, buff_used = apply_win_buffs(ctx.author.id, win_amount)
        update_balance(ctx.author.id, final_win)
        if buff_used:
            result = f"DOUBLE WIN! You won {final_win} petals! (Doubled from {win_amount})"
        else:
            result = f"You won {final_win} petals!"
        color = 0x00ff00
    else:
        result = "Push! Bet returned!"
        color = 0xffa500
    
    final_embed = discord.Embed(title="🃏 Blackjack Result", description=f"Your hand: {player} = {psum}\nDealer hand: {dealer} = {dsum}\n\n{result}", color=color)
    final_embed.add_field(name="New Balance", value=f"{get_balance(ctx.author.id):,} petals", inline=False)
    await ctx.send(embed=final_embed)

@bot.command()
async def rps(ctx, choice: str, bet: int):
    if bet <= 0 or get_balance(ctx.author.id) < bet:
        await ctx.send("❌ Invalid bet or insufficient balance!")
        return
    
    choices = ["rock", "paper", "scissors"]
    if choice.lower() not in choices:
        await ctx.send("❌ Choose rock, paper, or scissors!")
        return
    
    bot_choice = random.choice(choices)
    emojis = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}
    
    if choice.lower() == bot_choice:
        loss_amount = bet
        actual_loss, buff_used = apply_loss_protection(ctx.author.id, loss_amount)
        update_balance(ctx.author.id, -actual_loss)
        if buff_used:
            result = f"Tie goes to house! You lost {loss_amount} petals but were protected!"
        else:
            result = f"Tie goes to house! You lost {actual_loss} petals!"
        color = 0xff0000
    elif (choice.lower() == "rock" and bot_choice == "scissors") or (choice.lower() == "paper" and bot_choice == "rock") or (choice.lower() == "scissors" and bot_choice == "paper"):
        win_amount = int(bet * 0.9)
        final_win, buff_used = apply_win_buffs(ctx.author.id, win_amount)
        update_balance(ctx.author.id, final_win)
        if buff_used:
            result = f"DOUBLE WIN! You win {final_win} petals! (Doubled from {win_amount})"
        else:
            result = f"You win {final_win} petals!"
        color = 0x00ff00
    else:
        loss_amount = bet
        actual_loss, buff_used = apply_loss_protection(ctx.author.id, loss_amount)
        update_balance(ctx.author.id, -actual_loss)
        if buff_used:
            result = f"You lost {loss_amount} petals but were protected!"
        else:
            result = f"You lose {actual_loss} petals!"
        color = 0xff0000
    
    embed = discord.Embed(title="✂️ Rock Paper Scissors", description=f"You: {emojis[choice.lower()]} {choice}\nBot: {emojis[bot_choice]} {bot_choice}\n\n{result}", color=color)
    embed.add_field(name="New Balance", value=f"{get_balance(ctx.author.id):,} petals", inline=False)
    await ctx.send(embed=embed)

# Shop Commands
@bot.command()
async def shop(ctx, page: int = 1):
    view = ShopView(ctx, page - 1)
    embed = view.create_embed()
    await ctx.send(embed=embed, view=view)

@bot.command()
async def petshop(ctx, page: int = 1):
    view = PetShopView(ctx, page - 1)
    embed = view.create_embed()
    await ctx.send(embed=embed, view=view)

@bot.command()
async def inventory(ctx, member: discord.Member = None):
    target = member or ctx.author
    
    inv = get_inventory(target.id)
    
    if not inv:
        embed = discord.Embed(
            title="🎒 Inventory",
            description=f"{target.mention} has no items! Visit the shop with `b!shop` to buy some!",
            color=0xffa500
        )
        await ctx.send(embed=embed)
        return
    
    view = InventoryView(ctx, target)
    embed = view.create_inventory_embed()
    await ctx.send(embed=embed, view=view)

@bot.command()
async def buffs(ctx):
    embed = discord.Embed(title="✨ Active Buffs", color=0xff69b4)
    has_buffs = False
    
    if ctx.author.id in player_buffs:
        if player_buffs[ctx.author.id].get('luck'):
            expiry = player_buffs[ctx.author.id].get('luck_expiry')
            if expiry and expiry > datetime.now():
                has_buffs = True
                embed.add_field(name="🍀 Lucky Charm", value=f"+5% luck\nExpires: <t:{int(expiry.timestamp())}:R>", inline=False)
            else:
                player_buffs[ctx.author.id]['luck'] = False
        
        if player_buffs[ctx.author.id].get('xp_boost'):
            expiry = player_buffs[ctx.author.id].get('xp_boost_expiry')
            if expiry and expiry > datetime.now():
                has_buffs = True
                embed.add_field(name="⚡ XP Boost", value=f"Double daily rewards\nExpires: <t:{int(expiry.timestamp())}:R>", inline=False)
            else:
                player_buffs[ctx.author.id]['xp_boost'] = False
        
        if player_buffs[ctx.author.id].get('protection', 0) > 0:
            has_buffs = True
            embed.add_field(name="🛡️ Protection Amulet", value=f"{player_buffs[ctx.author.id]['protection']} remaining", inline=False)
        
        if player_buffs[ctx.author.id].get('double_win', 0) > 0:
            has_buffs = True
            embed.add_field(name="🎰 Double Win Token", value=f"{player_buffs[ctx.author.id]['double_win']} remaining", inline=False)
    
    if ctx.author.id in player_permanents and player_permanents[ctx.author.id].get('bank_vault'):
        has_buffs = True
        embed.add_field(name="🏦 Bank Vault", value="Daily gift limit: 1,500,000 petals", inline=False)
    
    if not has_buffs:
        embed.description = "No active buffs! Buy items from the shop and use `b!inventory` to activate them!"
    
    await ctx.send(embed=embed)

# Gift Commands
@bot.command()
async def gift(ctx, member: discord.Member, amount: int):
    if member == ctx.author:
        await ctx.send("❌ You can't gift yourself!")
        return
    if amount <= 0:
        await ctx.send("❌ Amount must be positive!")
        return
    if get_balance(ctx.author.id) < amount:
        await ctx.send(f"❌ You only have {get_balance(ctx.author.id)} petals!")
        return
    
    uid = ctx.author.id
    today = datetime.now().date()
    
    limit = 1500000 if uid in player_permanents and player_permanents[uid].get('bank_vault') else DAILY_GIFT_LIMIT
    
    if uid in gift_cooldown:
        last, gifted = gift_cooldown[uid]
        if last == today and gifted + amount > limit:
            remaining = limit - gifted
            await ctx.send(f"❌ Daily gift limit reached! You can gift {remaining} more petals today!")
            return
        elif last == today:
            new_total = gifted + amount
        else:
            new_total = amount
    else:
        new_total = amount
    
    if new_total > limit:
        remaining = limit - (new_total - amount)
        await ctx.send(f"❌ Daily gift limit reached! You can gift {remaining} more petals today!")
        return
    
    update_balance(ctx.author.id, -amount)
    update_balance(member.id, amount)
    gift_cooldown[uid] = (today, new_total)
    save_all_data()
    
    embed = discord.Embed(title="🎁 Gift Sent!", description=f"{ctx.author.mention} gifted {amount:,} petals to {member.mention}!", color=0xff69b4)
    embed.add_field(name="Daily Limit", value=f"Used: {new_total:,}/{limit:,}")
    await ctx.send(embed=embed)

@bot.command()
async def giftstats(ctx):
    uid = ctx.author.id
    today = datetime.now().date()
    limit = 1500000 if uid in player_permanents and player_permanents[uid].get('bank_vault') else DAILY_GIFT_LIMIT
    
    if uid in gift_cooldown and gift_cooldown[uid][0] == today:
        used = gift_cooldown[uid][1]
        remaining = limit - used
        await ctx.send(f"📊 Daily Gifting: Used {used:,}/{limit:,} petals\nRemaining: {remaining:,}")
    else:
        await ctx.send(f"📊 Daily Gifting: Used 0/{limit:,} petals\nRemaining: {limit:,}")

# Pet Commands
@bot.command()
async def mypets(ctx):
    uid = ctx.author.id
    if uid not in player_pets or not player_pets[uid]:
        await ctx.send("❌ You don't have any pets! Visit the pet shop with `b!petshop`!")
        return
    
    embed = discord.Embed(title=f"🐾 {ctx.author.name}'s Pets", color=0x00ff88)
    for pet_id, pet in player_pets[uid].items():
        pet_data = pet_shop_items[pet_id]
        equipped = "✅" if uid in pet_equipped and pet_equipped[uid] == pet_id else ""
        happiness = "❤️" * (pet["happiness"] // 10) + "🖤" * (10 - (pet["happiness"] // 10))
        embed.add_field(name=f"{pet_data['emoji']} {pet.get('name', pet_data['name'])} {equipped}", 
                      value=f"Level: {pet['level']}/{pet_data['max_level']}\nHappiness: {happiness} {pet['happiness']}%\nXP: {pet['xp']}/{pet_data['xp_per_level'] * pet['level']}", inline=False)
    embed.set_footer(text="Use b!pet to interact with your pets")
    await ctx.send(embed=embed)

@bot.command()
async def pet(ctx, action: str = None, *, name: str = None):
    uid = ctx.author.id
    
    if uid not in player_pets or not player_pets[uid]:
        await ctx.send("❌ You don't have any pets! Visit the pet shop with `b!petshop`!")
        return
    
    if uid not in pet_equipped:
        pet_equipped[uid] = list(player_pets[uid].keys())[0]
        save_all_data()
    
    if action is None:
        pet_id = pet_equipped[uid]
        pet = player_pets[uid][pet_id]
        pet_data = pet_shop_items[pet_id]
        happiness = "❤️" * (pet["happiness"] // 10) + "🖤" * (10 - (pet["happiness"] // 10))
        xp_needed = pet_data['xp_per_level'] * pet['level']
        xp_bar = "🟢" * int((pet["xp"] / xp_needed) * 10) + "⚫" * (10 - int((pet["xp"] / xp_needed) * 10)) if xp_needed > 0 else "🟢" * 10
        
        embed = discord.Embed(title=f"🐾 {pet_data['emoji']} {pet.get('name', pet_data['name'])}", color=0xff69b4)
        embed.add_field(name="Stats", value=f"**Level:** {pet['level']}/{pet_data['max_level']}\n**XP:** {pet['xp']:,}/{xp_needed:,}\n{xp_bar}\n**Happiness:** {happiness} {pet['happiness']}%\n**Daily Reward:** {pet_data['daily_reward'] + int(pet_data['daily_reward'] * (pet['level'] / 100)) + int(pet_data['daily_reward'] * (pet['happiness'] / 200)):,} petals", inline=False)
        embed.set_footer(text="Commands: b!pet feed | b!pet play | b!pet collect | b!pet rename | b!pet equip")
        await ctx.send(embed=embed)
    
    elif action.lower() == "feed":
        pet_id = pet_equipped[uid]
        pet = player_pets[uid][pet_id]
        pet_data = pet_shop_items[pet_id]
        
        on_cd, remaining = check_cooldown(pet_feed_cooldown, uid, 1800)
        if on_cd:
            await ctx.send(f"⏰ Your pet is full! Come back in {format_time(remaining)}")
            return
        
        old_happiness = pet["happiness"]
        pet["happiness"] = min(100, pet["happiness"] + 20)
        pet["xp"] += 50
        set_cooldown(pet_feed_cooldown, uid)
        
        leveled = False
        while pet["xp"] >= pet_data['xp_per_level'] * pet["level"] and pet["level"] < pet_data["max_level"]:
            pet["xp"] -= pet_data['xp_per_level'] * pet["level"]
            pet["level"] += 1
            leveled = True
        
        save_all_data()
        
        msg = f"🍖 You fed {pet_data['emoji']} {pet.get('name', pet_data['name'])}! Happiness: {old_happiness}% → {pet['happiness']}% (+50 XP)"
        if leveled:
            msg += f"\n🎉 LEVEL UP! Your pet reached level {pet['level']}! 🎉"
        await ctx.send(msg)
    
    elif action.lower() == "play":
        pet_id = pet_equipped[uid]
        pet = player_pets[uid][pet_id]
        pet_data = pet_shop_items[pet_id]
        
        on_cd, remaining = check_cooldown(pet_play_cooldown, uid, 3600)
        if on_cd:
            await ctx.send(f"⏰ Your pet is tired! Come back in {format_time(remaining)}")
            return
        
        old_happiness = pet["happiness"]
        pet["happiness"] = min(100, pet["happiness"] + 15)
        pet["xp"] += 75
        set_cooldown(pet_play_cooldown, uid)
        
        leveled = False
        while pet["xp"] >= pet_data['xp_per_level'] * pet["level"] and pet["level"] < pet_data["max_level"]:
            pet["xp"] -= pet_data['xp_per_level'] * pet["level"]
            pet["level"] += 1
            leveled = True
        
        save_all_data()
        
        msg = f"🎾 You played with {pet_data['emoji']} {pet.get('name', pet_data['name'])}! Happiness: {old_happiness}% → {pet['happiness']}% (+75 XP)"
        if leveled:
            msg += f"\n🎉 LEVEL UP! Your pet reached level {pet['level']}! 🎉"
        await ctx.send(msg)
    
    elif action.lower() == "collect":
        pet_id = pet_equipped[uid]
        pet = player_pets[uid][pet_id]
        pet_data = pet_shop_items[pet_id]
        
        on_cd, remaining = check_cooldown(pet_cooldown, uid)
        if on_cd:
            await ctx.send(f"⏰ Come back tomorrow! ({format_time(remaining)})")
            return
        
        reward = pet_data['daily_reward'] + int(pet_data['daily_reward'] * (pet['level'] / 100)) + int(pet_data['daily_reward'] * (pet['happiness'] / 200))
        update_balance(uid, reward)
        pet["xp"] += 25
        set_cooldown(pet_cooldown, uid)
        
        leveled = False
        while pet["xp"] >= pet_data['xp_per_level'] * pet["level"] and pet["level"] < pet_data["max_level"]:
            pet["xp"] -= pet_data['xp_per_level'] * pet["level"]
            pet["level"] += 1
            leveled = True
        
        save_all_data()
        
        msg = f"💰 {pet_data['emoji']} {pet.get('name', pet_data['name'])} gave you {reward:,} petals! (+25 XP)"
        if leveled:
            msg += f"\n🎉 LEVEL UP! Your pet reached level {pet['level']}! 🎉"
        await ctx.send(msg)
    
    elif action.lower() == "rename":
        if not name:
            await ctx.send("❌ Please provide a new name! Example: `b!pet rename Fluffy`")
            return
        if len(name) > 20:
            await ctx.send("❌ Name too long! Max 20 characters.")
            return
        
        pet_id = pet_equipped[uid]
        old_name = player_pets[uid][pet_id].get('name', pet_shop_items[pet_id]['name'])
        player_pets[uid][pet_id]['name'] = name
        save_all_data()
        await ctx.send(f"✅ Your pet {old_name} is now named **{name}**!")
    
    elif action.lower() == "equip":
        if not name:
            await ctx.send("❌ Please provide a pet name! Example: `b!pet equip \"Garden Cat\"`")
            return
        
        found = None
        for pid, pet in player_pets[uid].items():
            pet_data = pet_shop_items[pid]
            if pet.get('name', pet_data['name']).lower() == name.lower():
                found = pid
                break
        
        if found:
            pet_equipped[uid] = found
            save_all_data()
            pet_data = pet_shop_items[found]
            await ctx.send(f"✅ Equipped {pet_data['emoji']} {pet_data['name']} as your active pet!")
        else:
            await ctx.send(f"❌ Could not find a pet named '{name}'!")
    
    else:
        await ctx.send("❌ Invalid action! Use: `feed`, `play`, `collect`, `rename`, or `equip`")

@bot.command()
async def petstats(ctx, member: discord.Member = None):
    target = member or ctx.author
    uid = target.id
    
    if uid not in player_pets or not player_pets[uid]:
        await ctx.send(f"❌ {target.name} doesn't have any pets!")
        return
    
    if uid not in pet_equipped:
        pet_equipped[uid] = list(player_pets[uid].keys())[0]
        save_all_data()
    
    pet_id = pet_equipped[uid]
    pet = player_pets[uid][pet_id]
    pet_data = pet_shop_items[pet_id]
    
    happiness = "❤️" * (pet["happiness"] // 10) + "🖤" * (10 - (pet["happiness"] // 10))
    xp_needed = pet_data['xp_per_level'] * pet['level']
    xp_bar = "🟢" * int((pet["xp"] / xp_needed) * 20) + "⚫" * (20 - int((pet["xp"] / xp_needed) * 20)) if xp_needed > 0 else "🟢" * 20
    
    embed = discord.Embed(title=f"🐾 {target.name}'s Pet", description=f"{pet_data['emoji']} **{pet.get('name', pet_data['name'])}** [{pet_data['rarity'].title()}]", color=0xff69b4)
    embed.add_field(name="Stats", value=f"**Level:** {pet['level']}/{pet_data['max_level']}\n**XP:** {pet['xp']:,}/{xp_needed:,}\n{xp_bar}\n**Happiness:** {happiness} {pet['happiness']}%\n**Daily Reward:** {pet_data['daily_reward'] + int(pet_data['daily_reward'] * (pet['level'] / 100)) + int(pet_data['daily_reward'] * (pet['happiness'] / 200)):,} petals", inline=False)
    await ctx.send(embed=embed)

# Duel Command
@bot.command()
async def duel(ctx, opponent: discord.Member, bet: int):
    if opponent == ctx.author:
        await ctx.send("❌ You can't duel yourself!")
        return
    if bet < 50:
        await ctx.send("❌ Minimum bet is 50 petals!")
        return
    if get_balance(ctx.author.id) < bet:
        await ctx.send(f"❌ You need {bet} petals!")
        return
    
    embed = discord.Embed(title="⚔️ Duel Challenge!", description=f"{ctx.author.mention} challenges {opponent.mention} to a duel for {bet} petals!\n\n{opponent.mention}, do you accept?", color=0xffa500)
    await ctx.send(embed=embed, view=DuelView(ctx, opponent, bet))

# Redeem Command
@bot.command()
async def redeem(ctx):
    embed = discord.Embed(title="🎟️ Redeem Code", description="Click the button below to redeem a voucher code!", color=0xff69b4)
    await ctx.send(embed=embed, view=RedeemButtonView())

# Admin Commands
@bot.command()
async def gen(ctx, code: str, value: int, uses: int):
    if ctx.author.name not in ADMINS:
        await ctx.send("❌ No permission!")
        return
    redeem_codes[code.upper()] = {"value": value, "uses": uses}
    save_all_data()
    await ctx.send(f"✅ Generated code `{code.upper()}` worth {value} petals ({uses} uses)")

@bot.command()
async def give(ctx, member: discord.Member, amount: int):
    if ctx.author.name not in ADMINS:
        await ctx.send("❌ No permission!")
        return
    update_balance(member.id, amount)
    await ctx.send(f"✅ Gave {amount} petals to {member.mention}")

@bot.command()
async def reset_cooldowns(ctx, member: discord.Member = None):
    if ctx.author.name not in ADMINS:
        await ctx.send("❌ No permission!")
        return
    target = member or ctx.author
    for cd in [beg_cooldown, farm_cooldown, hunt_cooldown, work_cooldown, daily_cooldown, weekly_cooldown, hourly_cooldown, pet_cooldown]:
        if target.id in cd:
            del cd[target.id]
    save_all_data()
    await ctx.send(f"✅ Reset all cooldowns for {target.mention}")

@bot.command()
async def add_item(ctx, member: discord.Member, item: str, qty: int = 1):
    if ctx.author.name not in ADMINS:
        await ctx.send("❌ No permission!")
        return
    item_id = None
    for key, val in shop_items.items():
        if val['name'].lower() == item.lower():
            item_id = key
            break
    if not item_id:
        await ctx.send(f"❌ Item '{item}' not found!")
        return
    add_to_inventory(member.id, item_id, qty)
    await ctx.send(f"✅ Added {qty}x {shop_items[item_id]['name']} to {member.mention}")

@bot.command()
async def add_pet(ctx, member: discord.Member, pet_name: str):
    if ctx.author.name not in ADMINS:
        await ctx.send("❌ No permission!")
        return
    pet_id = None
    for key, val in pet_shop_items.items():
        if val['name'].lower() == pet_name.lower():
            pet_id = key
            break
    if not pet_id:
        await ctx.send(f"❌ Pet '{pet_name}' not found!")
        return
    
    if member.id not in player_pets:
        player_pets[member.id] = {}
    player_pets[member.id][pet_id] = {
        "name": pet_shop_items[pet_id]['name'],
        "level": 1,
        "xp": 0,
        "happiness": 100,
        "last_fed": datetime.now(),
        "last_played": datetime.now()
    }
    save_all_data()
    await ctx.send(f"✅ Added pet {pet_shop_items[pet_id]['name']} to {member.mention}")

@bot.command()
async def remove_pet(ctx, member: discord.Member, pet_name: str):
    if ctx.author.name not in ADMINS:
        await ctx.send("❌ No permission!")
        return
    pet_id = None
    for key, val in pet_shop_items.items():
        if val['name'].lower() == pet_name.lower():
            pet_id = key
            break
    if not pet_id:
        await ctx.send(f"❌ Pet '{pet_name}' not found!")
        return
    
    if member.id in player_pets and pet_id in player_pets[member.id]:
        del player_pets[member.id][pet_id]
        if member.id in pet_equipped and pet_equipped[member.id] == pet_id:
            del pet_equipped[member.id]
        save_all_data()
        await ctx.send(f"✅ Removed pet {pet_name} from {member.mention}")
    else:
        await ctx.send(f"❌ {member.mention} doesn't own that pet!")

@bot.command()
async def setup(ctx):
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ Admin only!")
        return
    server_channels[ctx.guild.id] = ctx.channel.id
    save_all_data()
    await ctx.send(f"✅ Leaderboard channel set to {ctx.channel.mention}")

@bot.command()
@commands.is_owner()
async def add_admin(ctx, username: str):
    if username not in ADMINS:
        ADMINS.append(username)
        await ctx.send(f"✅ Added {username} as admin!")

@bot.command()
async def admins(ctx):
    await ctx.send(f"👑 Admins: {', '.join(ADMINS)}")

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
                    user = await bot.fetch_user(uid)
                    desc += f"{medal} **{i}.** {user.name} — `{bal:,}` petals\n"
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
