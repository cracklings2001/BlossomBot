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

# Try to import pymongo, but don't fail if not installed
try:
    from pymongo import MongoClient
    MONGO_AVAILABLE = True
except ImportError:
    MONGO_AVAILABLE = False
    print("⚠️ pymongo not installed, using local file storage")

# --- PERMANENT DATABASE SYSTEM for RENDER (MongoDB Atlas) ---
# Check if running on Render
IS_RENDER = os.getenv('RENDER', False)

# MongoDB Connection - Initialize as None first
mongo_client = None
db = None
economy_collection = None
inventory_collection = None
pets_collection = None
cooldowns_collection = None
redeem_collection = None
channels_collection = None
buffs_collection = None
USE_MONGODB = False

# Get MongoDB URI from environment
MONGODB_URI = os.getenv('MONGODB_URI')

if MONGODB_URI and MONGO_AVAILABLE:
    try:
        mongo_client = MongoClient(MONGODB_URI)
        db = mongo_client['blossom_garden_bot']
        
        # MongoDB Collections
        economy_collection = db['economy']
        inventory_collection = db['inventory']
        pets_collection = db['pets']
        cooldowns_collection = db['cooldowns']
        redeem_collection = db['redeem']
        channels_collection = db['channels']
        buffs_collection = db['buffs']
        
        USE_MONGODB = True
        print("✅ Connected to MongoDB Atlas for persistent storage!")
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        print("⚠️ Falling back to local file storage")
        USE_MONGODB = False
elif MONGODB_URI and not MONGO_AVAILABLE:
    print("⚠️ pymongo not installed. Install with: pip install pymongo dnspython")
    print("⚠️ Falling back to local file storage")
else:
    print("⚠️ MONGODB_URI not found in environment variables")
    print("⚠️ Using local file storage (data will persist locally but not across Render restarts)")

# File paths for local backup
DATA_FILES = {
    'economy': 'data/economy.json',
    'inventory': 'data/inventory.json',
    'pets': 'data/pets.json',
    'cooldowns': 'data/cooldowns.json',
    'shop': 'data/shop.json',
    'redeem': 'data/redeem.json',
    'channels': 'data/channels.json',
    'buffs': 'data/buffs.json'
}

# Create data directory if it doesn't exist
if not os.path.exists('data'):
    os.makedirs('data')

# Initialize all global variables
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

def load_all_data():
    """Load all data from MongoDB or local files"""
    global economy, player_inventory, player_pets, pet_equipped, player_buffs, player_permanents
    global beg_cooldown, farm_cooldown, hunt_cooldown, work_cooldown
    global daily_cooldown, weekly_cooldown, hourly_cooldown, gift_cooldown
    global pet_feed_cooldown, pet_play_cooldown, pet_cooldown
    global redeem_codes, server_channels, USE_MONGODB
    
    if USE_MONGODB and MONGODB_URI:
        try:
            # Load from MongoDB
            economy_data = economy_collection.find_one({'_id': 'economy'})
            temp_economy = economy_data.get('data', {}) if economy_data else {}
            economy = {int(k): v for k, v in temp_economy.items()}
            
            inventory_data = inventory_collection.find_one({'_id': 'inventory'})
            temp_inventory = inventory_data.get('data', {}) if inventory_data else {}
            player_inventory = {int(k): v for k, v in temp_inventory.items()}
            
            pets_data = pets_collection.find_one({'_id': 'pets'})
            temp_pets = pets_data.get('data', {}) if pets_data else {}
            player_pets = {int(k): v for k, v in temp_pets.items()}
            
            pet_equipped_data = pets_collection.find_one({'_id': 'pet_equipped'})
            pet_equipped = pet_equipped_data.get('data', {}) if pet_equipped_data else {}
            pet_equipped = {int(k): v for k, v in pet_equipped.items()}
            
            buffs_data = buffs_collection.find_one({'_id': 'buffs'})
            temp_buffs = buffs_data.get('data', {}) if buffs_data else {}
            player_buffs = {int(k): v for k, v in temp_buffs.items()}
            
            cooldowns_data = cooldowns_collection.find_one({'_id': 'cooldowns'})
            cooldowns = cooldowns_data.get('data', {}) if cooldowns_data else {}
            
            # Reset cooldown dictionaries
            beg_cooldown.clear()
            farm_cooldown.clear()
            hunt_cooldown.clear()
            work_cooldown.clear()
            daily_cooldown.clear()
            weekly_cooldown.clear()
            hourly_cooldown.clear()
            gift_cooldown.clear()
            pet_feed_cooldown.clear()
            pet_play_cooldown.clear()
            pet_cooldown.clear()
            
            # Process cooldowns
            for user_id, data in cooldowns.items():
                user_id_int = int(user_id)
                if 'beg' in data:
                    beg_cooldown[user_id_int] = datetime.fromisoformat(data['beg'])
                if 'farm' in data:
                    farm_cooldown[user_id_int] = datetime.fromisoformat(data['farm'])
                if 'hunt' in data:
                    hunt_cooldown[user_id_int] = datetime.fromisoformat(data['hunt'])
                if 'work' in data:
                    work_cooldown[user_id_int] = datetime.fromisoformat(data['work'])
                if 'daily' in data:
                    daily_cooldown[user_id_int] = datetime.fromisoformat(data['daily'])
                if 'weekly' in data:
                    weekly_cooldown[user_id_int] = datetime.fromisoformat(data['weekly'])
                if 'hourly' in data:
                    hourly_cooldown[user_id_int] = datetime.fromisoformat(data['hourly'])
                if 'gift' in data:
                    gift_cooldown[user_id_int] = (datetime.fromisoformat(data['gift']['date']), data['gift']['amount'])
                if 'pet_feed' in data:
                    pet_feed_cooldown[user_id_int] = datetime.fromisoformat(data['pet_feed'])
                if 'pet_play' in data:
                    pet_play_cooldown[user_id_int] = datetime.fromisoformat(data['pet_play'])
                if 'pet_reward' in data:
                    pet_cooldown[user_id_int] = datetime.fromisoformat(data['pet_reward'])
            
            redeem_data = redeem_collection.find_one({'_id': 'redeem'})
            redeem_codes = redeem_data.get('data', {}) if redeem_data else {}
            
            channels_data = channels_collection.find_one({'_id': 'channels'})
            temp_channels = channels_data.get('data', {}) if channels_data else {}
            server_channels = {int(k): v for k, v in temp_channels.items()}
            
            player_permanents = {}
            
            print("✅ Loaded all data from MongoDB Atlas")
        except Exception as e:
            print(f"❌ Error loading from MongoDB: {e}")
            print("⚠️ Falling back to local file storage")
            USE_MONGODB = False
            load_from_files()
    else:
        load_from_files()

def load_from_files():
    """Load data from local JSON files (backup)"""
    global economy, player_inventory, player_pets, pet_equipped, player_buffs, player_permanents
    global beg_cooldown, farm_cooldown, hunt_cooldown, work_cooldown
    global daily_cooldown, weekly_cooldown, hourly_cooldown, gift_cooldown
    global pet_feed_cooldown, pet_play_cooldown, pet_cooldown
    global redeem_codes, server_channels
    
    try:
        with open(DATA_FILES['economy'], 'r') as f:
            temp_economy = json.load(f)
            economy = {int(k): v for k, v in temp_economy.items()}
    except:
        economy = {}
    
    try:
        with open(DATA_FILES['inventory'], 'r') as f:
            temp_inventory = json.load(f)
            player_inventory = {int(k): v for k, v in temp_inventory.items()}
    except:
        player_inventory = {}
    
    try:
        with open(DATA_FILES['pets'], 'r') as f:
            temp_pets = json.load(f)
            player_pets = {int(k): v for k, v in temp_pets.items()}
    except:
        player_pets = {}
    
    try:
        with open(DATA_FILES['pets'] + '_equipped', 'r') as f:
            temp_equipped = json.load(f)
            pet_equipped = {int(k): v for k, v in temp_equipped.items()}
    except:
        pet_equipped = {}
    
    try:
        with open(DATA_FILES['buffs'], 'r') as f:
            temp_buffs = json.load(f)
            player_buffs = {int(k): v for k, v in temp_buffs.items()}
    except:
        player_buffs = {}
    
    # Clear cooldown dictionaries
    beg_cooldown.clear()
    farm_cooldown.clear()
    hunt_cooldown.clear()
    work_cooldown.clear()
    daily_cooldown.clear()
    weekly_cooldown.clear()
    hourly_cooldown.clear()
    gift_cooldown.clear()
    pet_feed_cooldown.clear()
    pet_play_cooldown.clear()
    pet_cooldown.clear()
    
    try:
        with open(DATA_FILES['cooldowns'], 'r') as f:
            cooldowns = json.load(f)
            for user_id, data in cooldowns.items():
                user_id_int = int(user_id)
                if 'beg' in data:
                    beg_cooldown[user_id_int] = datetime.fromisoformat(data['beg'])
                if 'farm' in data:
                    farm_cooldown[user_id_int] = datetime.fromisoformat(data['farm'])
                if 'hunt' in data:
                    hunt_cooldown[user_id_int] = datetime.fromisoformat(data['hunt'])
                if 'work' in data:
                    work_cooldown[user_id_int] = datetime.fromisoformat(data['work'])
                if 'daily' in data:
                    daily_cooldown[user_id_int] = datetime.fromisoformat(data['daily'])
                if 'weekly' in data:
                    weekly_cooldown[user_id_int] = datetime.fromisoformat(data['weekly'])
                if 'hourly' in data:
                    hourly_cooldown[user_id_int] = datetime.fromisoformat(data['hourly'])
                if 'gift' in data:
                    gift_cooldown[user_id_int] = (datetime.fromisoformat(data['gift']['date']), data['gift']['amount'])
                if 'pet_feed' in data:
                    pet_feed_cooldown[user_id_int] = datetime.fromisoformat(data['pet_feed'])
                if 'pet_play' in data:
                    pet_play_cooldown[user_id_int] = datetime.fromisoformat(data['pet_play'])
                if 'pet_reward' in data:
                    pet_cooldown[user_id_int] = datetime.fromisoformat(data['pet_reward'])
    except:
        pass
    
    try:
        with open(DATA_FILES['redeem'], 'r') as f:
            redeem_codes = json.load(f)
    except:
        redeem_codes = {}
    
    try:
        with open(DATA_FILES['channels'], 'r') as f:
            temp_channels = json.load(f)
            server_channels = {int(k): v for k, v in temp_channels.items()}
    except:
        server_channels = {}
    
    player_permanents = {}
    print("✅ Loaded data from local files")

def save_all_data():
    """Save all data to MongoDB or local files"""
    if USE_MONGODB and MONGODB_URI:
        try:
            # Save to MongoDB
            economy_collection.update_one({'_id': 'economy'}, {'$set': {'data': economy}}, upsert=True)
            inventory_collection.update_one({'_id': 'inventory'}, {'$set': {'data': player_inventory}}, upsert=True)
            pets_collection.update_one({'_id': 'pets'}, {'$set': {'data': player_pets}}, upsert=True)
            pets_collection.update_one({'_id': 'pet_equipped'}, {'$set': {'data': pet_equipped}}, upsert=True)
            buffs_collection.update_one({'_id': 'buffs'}, {'$set': {'data': player_buffs}}, upsert=True)
            
            # Save cooldowns
            cooldowns = {}
            all_users = set(list(beg_cooldown.keys()) + list(farm_cooldown.keys()) + list(hunt_cooldown.keys()) + 
                            list(work_cooldown.keys()) + list(daily_cooldown.keys()) + list(weekly_cooldown.keys()) + 
                            list(hourly_cooldown.keys()) + list(gift_cooldown.keys()) + list(pet_feed_cooldown.keys()) + 
                            list(pet_play_cooldown.keys()) + list(pet_cooldown.keys()))
            
            for user_id in all_users:
                cooldowns[str(user_id)] = {}
                if user_id in beg_cooldown:
                    cooldowns[str(user_id)]['beg'] = beg_cooldown[user_id].isoformat()
                if user_id in farm_cooldown:
                    cooldowns[str(user_id)]['farm'] = farm_cooldown[user_id].isoformat()
                if user_id in hunt_cooldown:
                    cooldowns[str(user_id)]['hunt'] = hunt_cooldown[user_id].isoformat()
                if user_id in work_cooldown:
                    cooldowns[str(user_id)]['work'] = work_cooldown[user_id].isoformat()
                if user_id in daily_cooldown:
                    cooldowns[str(user_id)]['daily'] = daily_cooldown[user_id].isoformat()
                if user_id in weekly_cooldown:
                    cooldowns[str(user_id)]['weekly'] = weekly_cooldown[user_id].isoformat()
                if user_id in hourly_cooldown:
                    cooldowns[str(user_id)]['hourly'] = hourly_cooldown[user_id].isoformat()
                if user_id in gift_cooldown:
                    cooldowns[str(user_id)]['gift'] = {
                        'date': gift_cooldown[user_id][0].isoformat(),
                        'amount': gift_cooldown[user_id][1]
                    }
                if user_id in pet_feed_cooldown:
                    cooldowns[str(user_id)]['pet_feed'] = pet_feed_cooldown[user_id].isoformat()
                if user_id in pet_play_cooldown:
                    cooldowns[str(user_id)]['pet_play'] = pet_play_cooldown[user_id].isoformat()
                if user_id in pet_cooldown:
                    cooldowns[str(user_id)]['pet_reward'] = pet_cooldown[user_id].isoformat()
            
            cooldowns_collection.update_one({'_id': 'cooldowns'}, {'$set': {'data': cooldowns}}, upsert=True)
            redeem_collection.update_one({'_id': 'redeem'}, {'$set': {'data': redeem_codes}}, upsert=True)
            channels_collection.update_one({'_id': 'channels'}, {'$set': {'data': server_channels}}, upsert=True)
            
            print("💾 Saved all data to MongoDB Atlas")
        except Exception as e:
            print(f"❌ Error saving to MongoDB: {e}")
            save_to_files()
    else:
        save_to_files()

def save_to_files():
    """Save data to local JSON files (backup)"""
    # Convert int keys to string for JSON serialization
    economy_str_keys = {str(k): v for k, v in economy.items()}
    inventory_str_keys = {str(k): v for k, v in player_inventory.items()}
    pets_str_keys = {str(k): v for k, v in player_pets.items()}
    pet_equipped_str_keys = {str(k): v for k, v in pet_equipped.items()}
    buffs_str_keys = {str(k): v for k, v in player_buffs.items()}
    channels_str_keys = {str(k): v for k, v in server_channels.items()}
    
    with open(DATA_FILES['economy'], 'w') as f:
        json.dump(economy_str_keys, f, indent=4)
    with open(DATA_FILES['inventory'], 'w') as f:
        json.dump(inventory_str_keys, f, indent=4)
    with open(DATA_FILES['pets'], 'w') as f:
        json.dump(pets_str_keys, f, indent=4)
    with open(DATA_FILES['pets'] + '_equipped', 'w') as f:
        json.dump(pet_equipped_str_keys, f, indent=4)
    with open(DATA_FILES['buffs'], 'w') as f:
        json.dump(buffs_str_keys, f, indent=4)
    
    # Save cooldowns
    cooldowns = {}
    all_users = set(list(beg_cooldown.keys()) + list(farm_cooldown.keys()) + list(hunt_cooldown.keys()) + 
                    list(work_cooldown.keys()) + list(daily_cooldown.keys()) + list(weekly_cooldown.keys()) + 
                    list(hourly_cooldown.keys()) + list(gift_cooldown.keys()) + list(pet_feed_cooldown.keys()) + 
                    list(pet_play_cooldown.keys()) + list(pet_cooldown.keys()))
    
    for user_id in all_users:
        cooldowns[str(user_id)] = {}
        if user_id in beg_cooldown:
            cooldowns[str(user_id)]['beg'] = beg_cooldown[user_id].isoformat()
        if user_id in farm_cooldown:
            cooldowns[str(user_id)]['farm'] = farm_cooldown[user_id].isoformat()
        if user_id in hunt_cooldown:
            cooldowns[str(user_id)]['hunt'] = hunt_cooldown[user_id].isoformat()
        if user_id in work_cooldown:
            cooldowns[str(user_id)]['work'] = work_cooldown[user_id].isoformat()
        if user_id in daily_cooldown:
            cooldowns[str(user_id)]['daily'] = daily_cooldown[user_id].isoformat()
        if user_id in weekly_cooldown:
            cooldowns[str(user_id)]['weekly'] = weekly_cooldown[user_id].isoformat()
        if user_id in hourly_cooldown:
            cooldowns[str(user_id)]['hourly'] = hourly_cooldown[user_id].isoformat()
        if user_id in gift_cooldown:
            cooldowns[str(user_id)]['gift'] = {
                'date': gift_cooldown[user_id][0].isoformat(),
                'amount': gift_cooldown[user_id][1]
            }
        if user_id in pet_feed_cooldown:
            cooldowns[str(user_id)]['pet_feed'] = pet_feed_cooldown[user_id].isoformat()
        if user_id in pet_play_cooldown:
            cooldowns[str(user_id)]['pet_play'] = pet_play_cooldown[user_id].isoformat()
        if user_id in pet_cooldown:
            cooldowns[str(user_id)]['pet_reward'] = pet_cooldown[user_id].isoformat()
    
    with open(DATA_FILES['cooldowns'], 'w') as f:
        json.dump(cooldowns, f, indent=4)
    with open(DATA_FILES['redeem'], 'w') as f:
        json.dump(redeem_codes, f, indent=4)
    with open(DATA_FILES['channels'], 'w') as f:
        json.dump(channels_str_keys, f, indent=4)

def update_balance(user_id, amount):
    global economy
    economy[user_id] = economy.get(user_id, 0) + amount
    if economy[user_id] <= 0:
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
    seconds = int(seconds % 60)
    
    if hours > 0:
        return f"{hours}h {minutes}m"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"

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

# Load all data
load_all_data()

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
        "name": "🛡️ Protection Amulet",
        "emoji": "🛡️",
        "price": 30000,
        "description": "Protects you from one loss in any game",
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

DAILY_GIFT_LIMIT = 1000000

# --- UI: REDEEM MODAL ---
class RedeemModal(Modal, title="🌸 Redeem Petals - Enter Your Code"):
    code_input = TextInput(label="Voucher Code", placeholder="Enter your magical code...", min_length=1, max_length=20, style=discord.TextStyle.short)
    
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
                
                embed = discord.Embed(
                    title="🌸 Voucher Redeemed!",
                    description=f"{interaction.user.mention} successfully claimed **{data['value']} petals**!",
                    color=0xff69b4
                )
                embed.set_footer(text=f"Remaining uses: {data['uses'] if 'uses' in data else 0}")
                await interaction.response.send_message(embed=embed, ephemeral=False)
            else: 
                await interaction.response.send_message("🥀 **Code Expired!** This voucher has no remaining uses.", ephemeral=True)
        else: 
            await interaction.response.send_message("❌ **Invalid Code!** Please check and try again.", ephemeral=True)

class RedeemStarterView(View):
    @discord.ui.button(label="🎟️ Enter Voucher Code", style=discord.ButtonStyle.primary, emoji="🌸")
    async def open_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RedeemModal())

# --- NERFED CRASH GAME ---
class CrashView(View):
    def __init__(self, ctx, bet):
        super().__init__(timeout=120.0)
        self.ctx = ctx
        self.bet = bet
        self.multiplier = 1.0
        self.cashed_out = False
        self.crashed = False
        crash_type = random.choice(["early", "early", "early", "normal", "normal", "late"])
        if crash_type == "early":
            self.crash_at = round(random.uniform(1.05, 1.5), 2)
        elif crash_type == "normal":
            self.crash_at = round(random.uniform(1.3, 2.5), 2)
        else:
            self.crash_at = round(random.uniform(2.0, 4.0), 2)
        self.ticks = 0
    
    @discord.ui.button(label="💰 Cash Out Now!", style=discord.ButtonStyle.success, emoji="💎")
    async def cash_out(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author or self.cashed_out or self.crashed: 
            return
        self.cashed_out = True
        self.stop()
        win = int(self.bet * self.multiplier)
        update_balance(self.ctx.author.id, win - self.bet)
        
        embed = discord.Embed(
            title="✈️ SUCCESSFUL CASHOUT!",
            description=f"{self.ctx.author.mention} landed safely at **{self.multiplier:.2f}x** multiplier!",
            color=0x00ff00
        )
        embed.add_field(name="🌸 Petals Won", value=f"**{win}**", inline=True)
        embed.add_field(name="📊 Multiplier", value=f"**{self.multiplier:.2f}x**", inline=True)
        await interaction.response.edit_message(embed=embed, view=None)
    
    async def start_flight(self, msg):
        flight_emoji = ["✈️", "🛩️", "🚀", "💀", "⚠️"]
        emoji_index = 0
        
        while not self.cashed_out:
            await asyncio.sleep(1.0)
            if self.cashed_out: 
                break
            
            self.ticks += 1
            growth = random.uniform(0.08, 0.7)
            self.multiplier += growth
            emoji_index = (emoji_index + 1) % len(flight_emoji)
            
            if random.random() < 0.12 and self.multiplier > 1.2:
                self.crashed = True
                self.stop()
                update_balance(self.ctx.author.id, -self.bet)
                
                embed = discord.Embed(
                    title="💥 SUDDEN CRASH! 💥",
                    description=f"The plane experienced unexpected engine failure!",
                    color=0xff0000
                )
                embed.add_field(name="💔 Loss", value=f"Lost **{self.bet} petals**", inline=False)
                embed.add_field(name="📊 Multiplier at Crash", value=f"**{self.multiplier:.2f}x**", inline=False)
                await msg.edit(embed=embed, view=None)
                break
            
            if self.multiplier >= self.crash_at:
                self.crashed = True
                self.stop()
                update_balance(self.ctx.author.id, -self.bet)
                
                embed = discord.Embed(
                    title="💥 CRASH! 💥",
                    description=f"The plane crashed into the mountains!",
                    color=0xff0000
                )
                embed.add_field(name="💔 Loss", value=f"Lost **{self.bet} petals**", inline=False)
                embed.add_field(name="📊 Crash Point", value=f"**{self.crash_at:.2f}x**", inline=False)
                await msg.edit(embed=embed, view=None)
                break
            
            risk_percentage = min(95, int((self.multiplier / 3.0) * 100))
            
            embed = discord.Embed(
                title=f"{flight_emoji[emoji_index]} FLIGHT STATUS",
                description=f"**Current Multiplier:** {self.multiplier:.2f}x\n\n*⚠️ The higher you go, the riskier it gets!*",
                color=0xffa500
            )
            embed.add_field(name="💰 Current Payout", value=f"{int(self.bet * self.multiplier)} petals", inline=True)
            embed.add_field(name="⚠️ Crash Risk", value=f"{risk_percentage}%", inline=True)
            await msg.edit(embed=embed, view=self)

# --- NERFED MINES GAME ---
class MinesButton(Button):
    def __init__(self, num): 
        super().__init__(label="🌸", style=discord.ButtonStyle.secondary, row=(num-1)//3, emoji="🌸")
        self.num = num
    
    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if interaction.user != view.ctx.author: 
            return
        
        if self.num in view.bombs:
            view.stop()
            update_balance(view.ctx.author.id, -view.bet)
            for c in view.children: 
                if hasattr(c, 'num') and c.num in view.bombs:
                    c.style, c.label, c.emoji = discord.ButtonStyle.danger, "💣", None
                elif hasattr(c, 'num'):
                    c.style, c.disabled = discord.ButtonStyle.secondary, True
                else:
                    c.disabled = True
            
            embed = discord.Embed(
                title="💥 BOOM! Game Over 💥",
                description=f"{interaction.user.mention} stepped on a bomb!",
                color=0xff0000
            )
            embed.add_field(name="💔 Loss", value=f"Lost **{view.bet} petals**", inline=False)
            await interaction.response.edit_message(embed=embed, view=view)
        else:
            view.revealed += 1
            self.style, self.label, self.disabled, self.emoji = discord.ButtonStyle.success, "🍃", True, None
            
            mult = round(1.15 ** view.revealed, 2)
            val = int(view.bet * mult)
            
            async def co(i):
                view.stop()
                update_balance(view.ctx.author.id, val - view.bet)
                for c in view.children: 
                    c.disabled = True
                embed = discord.Embed(
                    title="💰 CASHOUT SUCCESSFUL! 💰",
                    description=f"{i.user.mention} escaped with their petals!",
                    color=0x00ff00
                )
                embed.add_field(name="🌸 Petals Won", value=f"**{val}**", inline=True)
                embed.add_field(name="🍃 Safe Tiles", value=f"**{view.revealed}**", inline=True)
                await i.response.edit_message(embed=embed, view=view)
            
            btn = discord.utils.get(view.children, label="💰 Cashout")
            if not btn: 
                btn = Button(label="💰 Cashout", style=discord.ButtonStyle.primary, emoji="💎", row=3)
                btn.callback = co
                view.add_item(btn)
            
            embed = discord.Embed(
                title="🌸 Minesweeper Garden 🌸",
                description=f"**Safe tiles found:** {view.revealed}\n**Current multiplier:** {mult}x\n**Potential win:** {val} petals",
                color=0x00ff88
            )
            await interaction.response.edit_message(embed=embed, view=view)

class MinesView(View):
    def __init__(self, ctx, bet, bombs):
        super().__init__(timeout=60.0)
        self.ctx = ctx
        self.bet = bet
        self.bombs = bombs
        self.revealed = 0
        for i in range(1, 10):
            self.add_item(MinesButton(i))

# --- NERFED COLOR GAME ---
class ColorButton(Button):
    def __init__(self, name, emoji, style_color):
        super().__init__(label=name, emoji=emoji, style=style_color)
        self.color_name = name
    
    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if interaction.user != view.ctx.author:
            return
        
        view.stop()
        colors = ["🟡 Yellow", "🔴 Red", "⚪ White", "🟢 Green", "🌸 Pink", "🔵 Blue"]
        rolled = [random.choice(colors) for _ in range(3)]
        hits = rolled.count(f"{self.emoji} {self.color_name}")
        
        for c in view.children:
            c.disabled = True
        
        result_display = " 🎲 ".join(rolled)
        
        if hits > 0:
            win = view.bet * hits
            update_balance(view.ctx.author.id, win - view.bet)
            embed = discord.Embed(
                title="🎉 VICTORY! 🎉",
                description=f"**Result:** {result_display}\n\n{interaction.user.mention} guessed **{self.color_name}** and it appeared **{hits} time(s)**!",
                color=0x00ff00
            )
            embed.add_field(name="🌸 Petals Won", value=f"+{win}", inline=True)
        else:
            update_balance(view.ctx.author.id, -view.bet)
            embed = discord.Embed(
                title="💔 DEFEAT 💔",
                description=f"**Result:** {result_display}\n\n{interaction.user.mention} guessed **{self.color_name}** but it didn't appear!",
                color=0xff0000
            )
            embed.add_field(name="🌸 Petals Lost", value=f"-{view.bet}", inline=True)
        
        await interaction.response.edit_message(embed=embed, view=view)

class ColorView(View):
    def __init__(self, ctx, bet):
        super().__init__(timeout=30.0)
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

# --- NERFED COINFLIP GAME ---
class CoinflipView(View):
    def __init__(self, ctx, bet):
        super().__init__(timeout=30.0)
        self.ctx = ctx
        self.bet = bet
    
    @discord.ui.button(label="🪙 HEADS", style=discord.ButtonStyle.primary, emoji="🪙", row=0)
    async def heads(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.flip(interaction, "heads")
    
    @discord.ui.button(label="🪙 TAILS", style=discord.ButtonStyle.primary, emoji="🪙", row=0)
    async def tails(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.flip(interaction, "tails")
    
    async def flip(self, interaction: discord.Interaction, choice):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ This isn't your game!", ephemeral=True)
            return
        
        result = random.choice(["heads", "tails"])
        if choice == result:
            win = int(self.bet * 0.9)
            update_balance(self.ctx.author.id, win)
            embed = discord.Embed(
                title="🪙 COINFLIP 🪙",
                description=f"**Your choice:** {choice.upper()}\n**Result:** {result.upper()}\n\n🎉 **YOU WIN!** +{win} petals!",
                color=0x00ff00
            )
        else:
            update_balance(self.ctx.author.id, -self.bet)
            embed = discord.Embed(
                title="🪙 COINFLIP 🪙",
                description=f"**Your choice:** {choice.upper()}\n**Result:** {result.upper()}\n\n💔 **YOU LOSE!** -{self.bet} petals!",
                color=0xff0000
            )
        
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()

# --- FIXED HIGHER OR LOWER GAME ---
class HigherLowerView(View):
    def __init__(self, ctx, bet, current_card, card_display, card_emoji):
        super().__init__(timeout=30.0)
        self.ctx = ctx
        self.bet = bet
        self.current_card = current_card
        self.card_display = card_display
        self.card_emoji = card_emoji
        self.game_active = True
    
    @discord.ui.button(label="⬆️ HIGHER", style=discord.ButtonStyle.success, emoji="⬆️", row=0)
    async def higher(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.guess(interaction, "higher")
    
    @discord.ui.button(label="⬇️ LOWER", style=discord.ButtonStyle.danger, emoji="⬇️", row=0)
    async def lower(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.guess(interaction, "lower")
    
    async def guess(self, interaction: discord.Interaction, choice):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ This isn't your game!", ephemeral=True)
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
            win = int(self.bet * 1.8)
            update_balance(self.ctx.author.id, win - self.bet)
            
            embed = discord.Embed(
                title="🎴 HIGHER OR LOWER 🎴",
                description=f"**Your Card:** {current_card_visual}\n**Next Card:** {next_card_visual}\n\n📈 **{choice.upper()}** was correct!\n\n🎉 **YOU WIN!** +{win} petals!",
                color=0x00ff00
            )
            embed.add_field(name="📊 Result", value=f"{self.card_display} → {next_display} ({'Higher' if next_card > self.current_card else 'Lower' if next_card < self.current_card else 'Same'})", inline=False)
            
        elif next_card == self.current_card:
            embed = discord.Embed(
                title="🎴 HIGHER OR LOWER 🎴",
                description=f"**Your Card:** {current_card_visual}\n**Next Card:** {next_card_visual}\n\n🤝 **TIE!** The cards are equal!\n\n💫 Your bet of **{self.bet} petals** has been returned!",
                color=0xffa500
            )
            embed.add_field(name="📊 Result", value=f"{self.card_display} → {next_display} (Same card!)", inline=False)
            
        else:
            update_balance(self.ctx.author.id, -self.bet)
            embed = discord.Embed(
                title="🎴 HIGHER OR LOWER 🎴",
                description=f"**Your Card:** {current_card_visual}\n**Next Card:** {next_card_visual}\n\n📉 **{choice.upper()}** was wrong!\n\n💔 **YOU LOSE!** -{self.bet} petals!",
                color=0xff0000
            )
            embed.add_field(name="📊 Result", value=f"{self.card_display} → {next_display} ({'Higher' if next_card > self.current_card else 'Lower' if next_card < self.current_card else 'Same'})", inline=False)
        
        self.game_active = False
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()

# --- NERFED SLOT MACHINE ---
class SlotMachineView(View):
    def __init__(self, ctx, bet):
        super().__init__(timeout=30.0)
        self.ctx = ctx
        self.bet = bet
    
    @discord.ui.button(label="🎰 SPIN", style=discord.ButtonStyle.primary, emoji="🎰", row=0)
    async def spin(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ This isn't your game!", ephemeral=True)
            return
        
        symbols = ["🍒", "🍊", "🍋", "🍉", "⭐", "💎", "7️⃣", "🌸"]
        reels = [random.choice(symbols) for _ in range(3)]
        
        if reels[0] == reels[1] == reels[2]:
            if reels[0] == "7️⃣":
                win = self.bet * 6
            elif reels[0] == "💎":
                win = self.bet * 5
            elif reels[0] == "⭐":
                win = self.bet * 4
            elif reels[0] == "🌸":
                win = self.bet * 3
            else:
                win = self.bet * 2
            update_balance(self.ctx.author.id, win - self.bet)
            result = f"🎉 **JACKPOT!** Won {win} petals!"
            color = 0x00ff00
        elif reels[0] == reels[1] or reels[1] == reels[2] or reels[0] == reels[2]:
            win = int(self.bet * 1.5)
            update_balance(self.ctx.author.id, win - self.bet)
            result = f"🎊 **MATCH!** Won {win} petals!"
            color = 0xffa500
        else:
            update_balance(self.ctx.author.id, -self.bet)
            result = f"💔 **NO MATCH!** Lost {self.bet} petals!"
            color = 0xff0000
        
        embed = discord.Embed(
            title="🎰 SLOT MACHINE 🎰",
            description=f"` {reels[0]} | {reels[1]} | {reels[2]} `\n\n{result}",
            color=color
        )
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()

# --- NERFED ROULETTE ---
class RouletteView(View):
    def __init__(self, ctx, bet):
        super().__init__(timeout=60.0)
        self.ctx = ctx
        self.bet = bet
    
    @discord.ui.button(label="🔴 RED", style=discord.ButtonStyle.danger, emoji="🔴", row=0)
    async def red(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.spin(interaction, "red")
    
    @discord.ui.button(label="⚫ BLACK", style=discord.ButtonStyle.secondary, emoji="⚫", row=0)
    async def black(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.spin(interaction, "black")
    
    @discord.ui.button(label="🟢 GREEN", style=discord.ButtonStyle.success, emoji="🟢", row=0)
    async def green(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.spin(interaction, "green")
    
    async def spin(self, interaction: discord.Interaction, choice):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ This isn't your game!", ephemeral=True)
            return
        
        number = random.randint(0, 36)
        if number == 0:
            result = "green"
            multiplier = 12
        elif number in [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]:
            result = "red"
            multiplier = 2
        else:
            result = "black"
            multiplier = 2
        
        if choice == result:
            if result == "green":
                win = self.bet * multiplier
            else:
                win = int(self.bet * 1.8)
            update_balance(self.ctx.author.id, win - self.bet)
            embed = discord.Embed(
                title="🎡 ROULETTE 🎡",
                description=f"**Ball landed on:** {number} ({result.upper()})\n**Your bet:** {choice.upper()}\n\n🎉 **YOU WIN!** +{win} petals!",
                color=0x00ff00
            )
        else:
            update_balance(self.ctx.author.id, -self.bet)
            embed = discord.Embed(
                title="🎡 ROULETTE 🎡",
                description=f"**Ball landed on:** {number} ({result.upper()})\n**Your bet:** {choice.upper()}\n\n💔 **YOU LOSE!** -{self.bet} petals!",
                color=0xff0000
            )
        
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()

# --- NERFED TOWER CLIMB ---
class TowerView(View):
    def __init__(self, ctx, bet):
        super().__init__(timeout=60.0)
        self.ctx = ctx
        self.bet = bet
        self.floor = 1
        self.multiplier = 1.0
        self.update_display()
    
    def update_display(self):
        self.multiplier = round(1.1 ** self.floor, 2)
    
    @discord.ui.button(label="⬆️ CLIMB", style=discord.ButtonStyle.success, emoji="⬆️", row=0)
    async def climb(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ This isn't your game!", ephemeral=True)
            return
        
        if random.random() < 0.4:
            update_balance(self.ctx.author.id, -self.bet)
            embed = discord.Embed(
                title="🏰 TOWER CLIMB 🏰",
                description=f"You fell from floor **{self.floor}**!\n💔 Lost **{self.bet} petals**!",
                color=0xff0000
            )
            await interaction.response.edit_message(embed=embed, view=None)
            self.stop()
        else:
            self.floor += 1
            self.update_display()
            potential_win = int(self.bet * self.multiplier)
            embed = discord.Embed(
                title="🏰 TOWER CLIMB 🏰",
                description=f"You reached **floor {self.floor}**!\n📊 Multiplier: **{self.multiplier}x**\n💰 Potential win: **{potential_win} petals**\n\n*Click CASHOUT to secure your win, or CLIMB higher!*",
                color=0xffa500
            )
            await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="💰 CASHOUT", style=discord.ButtonStyle.primary, emoji="💰", row=0)
    async def cashout(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ This isn't your game!", ephemeral=True)
            return
        
        win = int(self.bet * self.multiplier)
        update_balance(self.ctx.author.id, win - self.bet)
        embed = discord.Embed(
            title="🏰 TOWER CLIMB 🏰",
            description=f"You climbed to floor **{self.floor}** and cashed out!\n🎉 Won **{win} petals**!",
            color=0x00ff00
        )
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()

# --- NERFED TREASURE HUNT ---
class TreasureHuntView(View):
    def __init__(self, ctx, bet):
        super().__init__(timeout=30.0)
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
            await interaction.response.send_message("❌ This isn't your game!", ephemeral=True)
            return
        
        if self.attempts >= self.max_attempts:
            return
        
        self.attempts += 1
        if spot == self.treasure_position:
            win = int(self.bet * 2.5)
            update_balance(self.ctx.author.id, win - self.bet)
            embed = discord.Embed(
                title="💎 TREASURE HUNT 💎",
                description=f"You found the treasure at spot **{spot}**!\n🎉 Won **{win} petals**!",
                color=0x00ff00
            )
            await interaction.response.edit_message(embed=embed, view=None)
            self.stop()
        elif self.attempts >= self.max_attempts:
            update_balance(self.ctx.author.id, -self.bet)
            embed = discord.Embed(
                title="💎 TREASURE HUNT 💎",
                description=f"You didn't find the treasure! It was at spot **{self.treasure_position}**.\n💔 Lost **{self.bet} petals**!",
                color=0xff0000
            )
            await interaction.response.edit_message(embed=embed, view=None)
            self.stop()
        else:
            button.disabled = True
            remaining = self.max_attempts - self.attempts
            await interaction.response.edit_message(content=f"Nothing at spot {spot}! Try again! ({remaining} attempt{'s' if remaining > 1 else ''} remaining)", view=self)

# --- DEADLY RUSSIAN ROULETTE (3 Bullets) ---
class RussianRouletteView(View):
    def __init__(self, ctx, bet):
        super().__init__(timeout=30.0)
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
            await interaction.response.send_message("❌ This isn't your game!", ephemeral=True)
            return
        
        self.spins += 1
        
        if self.chambers[self.current_chamber]:
            update_balance(self.ctx.author.id, -self.bet)
            embed = discord.Embed(
                title="💀 RUSSIAN ROULETTE 💀",
                description=f"**BANG! BANG! BANG!**\nChamber {self.current_chamber + 1} had a bullet!\n💔 You lost **{self.bet} petals**!",
                color=0xff0000
            )
            embed.add_field(name="💀 Bullets Remaining", value=f"{sum(self.chambers)}/6 chambers loaded", inline=False)
            await interaction.response.edit_message(embed=embed, view=None)
            self.stop()
            return
        
        self.current_chamber += 1
        remaining_bullets = sum(self.chambers[self.current_chamber:])
        
        if self.spins >= self.max_spins:
            win = self.bet * 3
            update_balance(self.ctx.author.id, win - self.bet)
            
            embed = discord.Embed(
                title="🔫 RUSSIAN ROULETTE 🔫",
                description=f"**Click! Click! Click!**\nSomehow you survived {self.max_spins} pulls with 3 bullets loaded!\n🎉 You won **{int(win)} petals**!",
                color=0x00ff00
            )
            embed.add_field(name="💀 Bullets Remaining", value=f"{remaining_bullets} bullets still in chambers", inline=False)
            await interaction.response.edit_message(embed=embed, view=None)
            self.stop()
            return
        
        remaining_pulls = self.max_spins - self.spins
        survival_chance = self.calculate_survival_chance()
        
        embed = discord.Embed(
            title="🔫 RUSSIAN ROULETTE 🔫",
            description=f"**Click!** Chamber {self.current_chamber} was empty!\nYou have **{remaining_pulls}** pull(s) remaining.\n💀 {remaining_bullets} bullet(s) still in the {6 - self.current_chamber} remaining chambers!",
            color=0xffa500
        )
        embed.add_field(name="📊 Survival Chance", value=f"{survival_chance:.1f}%", inline=True)
        embed.add_field(name="💰 Potential Win", value=f"{int(self.bet * 3)} petals", inline=True)
        embed.add_field(name="🎯 Risk Level", value="🔴🔴🔴 EXTREME", inline=False)
        await interaction.response.edit_message(embed=embed, view=self)
    
    def calculate_survival_chance(self):
        remaining_chambers = 6 - self.current_chamber
        remaining_bullets = sum(self.chambers[self.current_chamber:])
        remaining_pulls = self.max_spins - self.spins
        
        if remaining_pulls <= 0 or remaining_chambers <= 0:
            return 100.0
        
        chance = 1.0
        for i in range(remaining_pulls):
            if remaining_chambers - i <= 0:
                chance = 0
                break
            chance *= (remaining_chambers - i - remaining_bullets) / (remaining_chambers - i)
        
        return chance * 100
    
    @discord.ui.button(label="💰 CASHOUT EARLY", style=discord.ButtonStyle.success, emoji="💰", row=1)
    async def cashout(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ This isn't your game!", ephemeral=True)
            return
        
        remaining_bullets = sum(self.chambers[self.current_chamber:])
        
        if self.spins == 0:
            cashout_amount = int(self.bet * 0.7)
            risk_text = "🛡️ Coward's Way Out"
        elif self.spins == 1:
            cashout_amount = int(self.bet * 1.2)
            risk_text = "😅 Smart Move"
        elif self.spins == 2:
            cashout_amount = int(self.bet * 2.0)
            risk_text = "🎲 Bold Decision"
        else:
            cashout_amount = int(self.bet * 2.8)
            risk_text = "🔥 Risk Taker"
        
        update_balance(self.ctx.author.id, cashout_amount - self.bet)
        
        embed = discord.Embed(
            title="🔫 RUSSIAN ROULETTE 🔫",
            description=f"You cashed out after **{self.spins}** pull(s)!\n🏆 **{risk_text}**\n💰 You won **{cashout_amount} petals**!",
            color=0x00ff00
        )
        embed.add_field(name="💀 Bullets Still Loaded", value=f"{remaining_bullets} bullets in remaining chambers", inline=False)
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()

# --- NERFED SCRATCH CARD ---
class ScratchView(View):
    def __init__(self, ctx, bet):
        super().__init__(timeout=30.0)
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
            await interaction.response.send_message("❌ This isn't your game!", ephemeral=True)
            return
        
        if self.revealed[index]:
            return
        
        self.revealed[index] = True
        button.label = str(self.values[index])
        button.disabled = True
        
        if all(self.revealed):
            if self.values[0] == self.values[1] == self.values[2]:
                win = self.bet * 3
                update_balance(self.ctx.author.id, win - self.bet)
                embed = discord.Embed(
                    title="🎫 SCRATCH CARD 🎫",
                    description=f"**{self.values[0]} | {self.values[1]} | {self.values[2]}**\n\n🎉 **JACKPOT!** Won {win} petals!",
                    color=0x00ff00
                )
            elif self.values[0] == self.values[1] or self.values[1] == self.values[2] or self.values[0] == self.values[2]:
                win = int(self.bet * 1.5)
                update_balance(self.ctx.author.id, win - self.bet)
                embed = discord.Embed(
                    title="🎫 SCRATCH CARD 🎫",
                    description=f"**{self.values[0]} | {self.values[1]} | {self.values[2]}**\n\n🎊 **MATCH!** Won {win} petals!",
                    color=0xffa500
                )
            else:
                update_balance(self.ctx.author.id, -self.bet)
                embed = discord.Embed(
                    title="🎫 SCRATCH CARD 🎫",
                    description=f"**{self.values[0]} | {self.values[1]} | {self.values[2]}**\n\n💔 **NO MATCH!** Lost {self.bet} petals!",
                    color=0xff0000
                )
            await interaction.response.edit_message(embed=embed, view=None)
            self.stop()
        else:
            await interaction.response.edit_message(content=f"Scratched! {self.values[index]} revealed! Keep scratching!", view=self)

# --- NERFED HORSE RACING ---
class RaceView(View):
    def __init__(self, ctx, bet):
        super().__init__(timeout=30.0)
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
            await interaction.response.send_message("❌ This isn't your game!", ephemeral=True)
            return
        
        winner = random.randint(0, 4)
        if choice == winner:
            win = int(self.bet * 3.5)
            update_balance(self.ctx.author.id, win - self.bet)
            embed = discord.Embed(
                title="🏇 HORSE RACING 🏇",
                description=f"**Winner:** {self.horses[winner]}\n**Your bet:** {self.horses[choice]}\n\n🎉 **YOU WIN!** +{win} petals!",
                color=0x00ff00
            )
        else:
            update_balance(self.ctx.author.id, -self.bet)
            embed = discord.Embed(
                title="🏇 HORSE RACING 🏇",
                description=f"**Winner:** {self.horses[winner]}\n**Your bet:** {self.horses[choice]}\n\n💔 **YOU LOSE!** -{self.bet} petals!",
                color=0xff0000
            )
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()

# --- NERFED POKER ---
class PokerView(View):
    def __init__(self, ctx, bet):
        super().__init__(timeout=30.0)
        self.ctx = ctx
        self.bet = bet
    
    @discord.ui.button(label="🃏 DEAL CARDS", style=discord.ButtonStyle.primary, emoji="🃏", row=0)
    async def deal(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ This isn't your game!", ephemeral=True)
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
            win = int(self.bet * 1.8)
            update_balance(self.ctx.author.id, win - self.bet)
            result = f"🎉 **YOU WIN!** +{win} petals!"
            color = 0x00ff00
        else:
            update_balance(self.ctx.author.id, -self.bet)
            result = f"💔 **YOU LOSE!** -{self.bet} petals!"
            color = 0xff0000
        
        embed = discord.Embed(
            title="🃏 POKER SHOWDOWN 🃏",
            description=f"**Your hand:** {player_display}\n**Bot's hand:** {bot_display}\n\n{result}",
            color=color
        )
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

# --- DICE DUEL ---
class DiceDuelView(View):
    def __init__(self, ctx, bet):
        super().__init__(timeout=30.0)
        self.ctx = ctx
        self.bet = bet
    
    @discord.ui.button(label="🎲 ROLL DICE", style=discord.ButtonStyle.primary, emoji="🎲", row=0)
    async def roll(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ This isn't your game!", ephemeral=True)
            return
        
        player_roll = random.randint(1, 6)
        bot_roll = random.randint(1, 6)
        
        dice_art = {
            1: "⚀", 2: "⚁", 3: "⚂",
            4: "⚃", 5: "⚄", 6: "⚅"
        }
        
        if player_roll > bot_roll:
            win = int(self.bet * 1.8)
            update_balance(self.ctx.author.id, win - self.bet)
            result = f"🎉 **YOU WIN!** +{win} petals!"
            color = 0x00ff00
        elif player_roll < bot_roll:
            update_balance(self.ctx.author.id, -self.bet)
            result = f"💔 **YOU LOSE!** -{self.bet} petals!"
            color = 0xff0000
        else:
            update_balance(self.ctx.author.id, -self.bet)
            result = f"💔 **TIE GOES TO HOUSE!** -{self.bet} petals!"
            color = 0xff0000
        
        embed = discord.Embed(
            title="🎲 DICE DUEL 🎲",
            description=f"**Your roll:** {dice_art[player_roll]} {player_roll}\n**Bot's roll:** {dice_art[bot_roll]} {bot_roll}\n\n{result}",
            color=color
        )
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()

# --- DUEL GAME ---
class DuelView(View):
    def __init__(self, ctx, opponent, bet):
        super().__init__(timeout=60.0)
        self.ctx = ctx
        self.opponent = opponent
        self.bet = bet
        self.accepted = False
        self.weapons = ["🗡️ Sword", "🏹 Bow", "🔮 Magic", "💣 Bomb", "⚔️ Axe", "🔫 Pistol"]
        self.player_health = 100
        self.opponent_health = 100
        self.turn = None
        self.buttons_disabled = False
    
    @discord.ui.button(label="✅ Accept Duel", style=discord.ButtonStyle.success, emoji="⚔️", row=0)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.opponent:
            await interaction.response.send_message("❌ Only the challenged player can accept this duel!", ephemeral=True)
            return
        
        if self.accepted:
            await interaction.response.send_message("❌ This duel has already been accepted!", ephemeral=True)
            return
        
        if get_balance(self.opponent.id) < self.bet:
            await interaction.response.send_message(f"❌ {self.opponent.mention} doesn't have enough petals to accept this duel!", ephemeral=True)
            self.stop()
            return
        
        self.accepted = True
        
        for child in self.children:
            if child.label == "✅ Accept Duel":
                self.remove_item(child)
        
        embed = discord.Embed(
            title="⚔️ DUEL ACCEPTED! ⚔️",
            description=f"{self.opponent.mention} accepted the duel!\n\n**💀 Choose your weapon to start the battle! 💀**\n\n{self.ctx.author.mention} attacks first!",
            color=0xffa500
        )
        embed.add_field(name="📊 Stats", value=f"Both players have 100 HP\nBet: **{self.bet} petals**", inline=False)
        
        self.add_weapon_buttons()
        self.turn = 'player'
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    def add_weapon_buttons(self):
        for i, weapon in enumerate(self.weapons):
            button = Button(label=weapon, style=discord.ButtonStyle.primary, row=i//2, emoji=weapon.split()[0])
            button.callback = self.create_weapon_callback(weapon)
            self.add_item(button)
        
        surrender = Button(label="🏳️ Surrender", style=discord.ButtonStyle.danger, emoji="🏳️", row=3)
        surrender.callback = self.surrender_callback
        self.add_item(surrender)
    
    def create_weapon_callback(self, weapon):
        async def callback(interaction: discord.Interaction):
            if self.buttons_disabled:
                await interaction.response.send_message("⏳ The battle is already in progress!", ephemeral=True)
                return
            
            if self.turn == 'player' and interaction.user == self.ctx.author:
                await self.fight(interaction, weapon, 'player')
            elif self.turn == 'opponent' and interaction.user == self.opponent:
                await self.fight(interaction, weapon, 'opponent')
            else:
                await interaction.response.send_message("❌ It's not your turn!", ephemeral=True)
        return callback
    
    async def surrender_callback(self, interaction: discord.Interaction):
        if interaction.user == self.ctx.author:
            loser = self.ctx.author
            winner = self.opponent
        elif interaction.user == self.opponent:
            loser = self.opponent
            winner = self.ctx.author
        else:
            await interaction.response.send_message("❌ You're not in this duel!", ephemeral=True)
            return
        
        update_balance(loser.id, -self.bet)
        update_balance(winner.id, self.bet)
        
        embed = discord.Embed(
            title="🏳️ SURRENDER! 🏳️",
            description=f"{loser.mention} surrendered the duel!\n\n🎉 **{winner.mention} wins {self.bet} petals!**",
            color=0xff0000
        )
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()
    
    async def fight(self, interaction: discord.Interaction, weapon, attacker):
        self.buttons_disabled = True
        
        weapon_damage = {
            "🗡️ Sword": random.randint(15, 35),
            "🏹 Bow": random.randint(10, 40),
            "🔮 Magic": random.randint(5, 45),
            "💣 Bomb": random.randint(20, 30),
            "⚔️ Axe": random.randint(15, 35),
            "🔫 Pistol": random.randint(10, 40)
        }
        
        is_critical = random.random() < 0.2
        damage = weapon_damage[weapon]
        if is_critical:
            damage = int(damage * 1.5)
        
        is_miss = random.random() < 0.1
        
        if attacker == 'player':
            attacker_user = self.ctx.author
            defender = self.opponent
            defender_health = self.opponent_health
        else:
            attacker_user = self.opponent
            defender = self.ctx.author
            defender_health = self.player_health
        
        if is_miss:
            damage_dealt = 0
            hit_text = f"**{weapon} MISSED!** {attacker_user.display_name}'s attack failed completely!"
        else:
            damage_dealt = damage
            hit_text = f"**{weapon} hit for {damage} damage!**" + (" 💥 **CRITICAL HIT!** 💥" if is_critical else "")
        
        if defender_health == self.opponent_health:
            self.opponent_health = max(0, defender_health - damage_dealt)
        else:
            self.player_health = max(0, defender_health - damage_dealt)
        
        embed = discord.Embed(
            title="⚔️ EPIC DUEL ⚔️",
            description=f"**{attacker_user.display_name}** attacks with {weapon}!\n{hit_text}",
            color=0xff6600
        )
        
        player_bar = self.create_health_bar(self.player_health)
        opponent_bar = self.create_health_bar(self.opponent_health)
        
        embed.add_field(name=f"💚 {self.ctx.author.display_name}", value=f"{player_bar} `{self.player_health}/100`", inline=False)
        embed.add_field(name=f"💚 {self.opponent.display_name}", value=f"{opponent_bar} `{self.opponent_health}/100`", inline=False)
        
        if self.player_health <= 0:
            update_balance(self.ctx.author.id, -self.bet)
            update_balance(self.opponent.id, self.bet)
            embed.add_field(name="💀 GAME OVER 💀", value=f"**{self.opponent.mention} wins the duel!**\n🎉 Won **{self.bet} petals**!", inline=False)
            await interaction.response.edit_message(embed=embed, view=None)
            self.stop()
            return
        elif self.opponent_health <= 0:
            update_balance(self.ctx.author.id, self.bet)
            update_balance(self.opponent.id, -self.bet)
            embed.add_field(name="💀 GAME OVER 💀", value=f"**{self.ctx.author.mention} wins the duel!**\n🎉 Won **{self.bet} petals**!", inline=False)
            await interaction.response.edit_message(embed=embed, view=None)
            self.stop()
            return
        
        self.turn = 'opponent' if attacker == 'player' else 'player'
        embed.set_footer(text=f"🔁 {defender.display_name}'s turn to attack! Choose your weapon...")
        
        self.buttons_disabled = False
        await interaction.response.edit_message(embed=embed, view=self)
    
    def create_health_bar(self, health):
        filled = int(health / 10)
        empty = 10 - filled
        return "█" * filled + "░" * empty

class DuelRequestView(View):
    def __init__(self, ctx, opponent, bet):
        super().__init__(timeout=30.0)
        self.ctx = ctx
        self.opponent = opponent
        self.bet = bet
        self.accepted = False
    
    @discord.ui.button(label="✅ Accept Duel", style=discord.ButtonStyle.success, emoji="⚔️")
    async def accept_duel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.opponent:
            await interaction.response.send_message("❌ Only the challenged player can accept this duel!", ephemeral=True)
            return
        
        self.accepted = True
        
        if get_balance(self.ctx.author.id) < self.bet:
            await interaction.response.send_message(f"❌ {self.ctx.author.mention} doesn't have enough petals for this duel!", ephemeral=True)
            self.stop()
            return
        
        if get_balance(self.opponent.id) < self.bet:
            await interaction.response.send_message(f"❌ {self.opponent.mention} doesn't have enough petals to accept this duel!", ephemeral=True)
            self.stop()
            return
        
        embed = discord.Embed(
            title="⚔️ DUEL STARTING! ⚔️",
            description=f"{self.opponent.mention} accepted the challenge!\nGet ready to battle!",
            color=0x00ff00
        )
        await interaction.response.edit_message(embed=embed, view=None)
        
        duel_view = DuelView(self.ctx, self.opponent, self.bet)
        duel_embed = discord.Embed(
            title="⚔️ PREPARE FOR BATTLE! ⚔️",
            description=f"{self.ctx.author.mention} vs {self.opponent.mention}\n\n**Bet:** {self.bet} petals\n**Both players:** 100 HP\n\n{self.ctx.author.mention} attacks first!\n\n💀 Choose your weapon to strike! 💀",
            color=0xffa500
        )
        await interaction.followup.send(embed=duel_embed, view=duel_view)
        self.stop()
    
    @discord.ui.button(label="❌ Decline", style=discord.ButtonStyle.danger, emoji="❌")
    async def decline_duel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.opponent:
            await interaction.response.send_message("❌ Only the challenged player can decline this duel!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="❌ DUEL DECLINED",
            description=f"{self.opponent.mention} declined the duel challenge!",
            color=0xff0000
        )
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()

# --- SHOP UI VIEWS ---
class ShopView(View):
    def __init__(self, ctx, page=0):
        super().__init__(timeout=60.0)
        self.ctx = ctx
        self.page = page
        self.items_per_page = 5
        self.items_list = list(shop_items.items())
        self.total_pages = (len(self.items_list) + self.items_per_page - 1) // self.items_per_page
        
        self.update_buttons()
    
    def update_buttons(self):
        self.clear_items()
        
        start_idx = self.page * self.items_per_page
        end_idx = min(start_idx + self.items_per_page, len(self.items_list))
        
        for i in range(start_idx, end_idx):
            item_id, item_data = self.items_list[i]
            button = Button(
                label=f"{item_data['emoji']} {item_data['name']} - {item_data['price']:,}🌸",
                style=discord.ButtonStyle.secondary,
                custom_id=f"buy_{item_id}"
            )
            button.callback = self.create_buy_callback(item_id, item_data)
            self.add_item(button)
        
        if self.page > 0:
            prev_btn = Button(label="◀️ Previous", style=discord.ButtonStyle.primary)
            prev_btn.callback = self.previous_page
            self.add_item(prev_btn)
        
        page_btn = Button(label=f"📄 Page {self.page + 1}/{self.total_pages}", style=discord.ButtonStyle.secondary, disabled=True)
        self.add_item(page_btn)
        
        if self.page < self.total_pages - 1:
            next_btn = Button(label="Next ▶️", style=discord.ButtonStyle.primary)
            next_btn.callback = self.next_page
            self.add_item(next_btn)
        
        inv_btn = Button(label="🎒 My Inventory", style=discord.ButtonStyle.success, emoji="🎒", row=2)
        inv_btn.callback = self.show_inventory
        self.add_item(inv_btn)
        
        close_btn = Button(label="❌ Close", style=discord.ButtonStyle.danger, emoji="❌", row=2)
        close_btn.callback = self.close_shop
        self.add_item(close_btn)
    
    def create_buy_callback(self, item_id, item_data):
        async def callback(interaction: discord.Interaction):
            if interaction.user != self.ctx.author:
                await interaction.response.send_message("❌ This shop isn't for you!", ephemeral=True)
                return
            
            balance = get_balance(interaction.user.id)
            price = item_data['price']
            
            if balance < price:
                await interaction.response.send_message(f"❌ You don't have enough petals! Need **{price:,}** petals, you have **{balance:,}**", ephemeral=True)
                return
            
            embed = discord.Embed(
                title=f"🛒 Confirm Purchase",
                description=f"Are you sure you want to buy **{item_data['emoji']} {item_data['name']}** for **{price:,} petals**?\n\n{item_data['description']}",
                color=0xffa500
            )
            
            confirm_view = ConfirmPurchaseView(self.ctx, item_id, item_data, price)
            await interaction.response.send_message(embed=embed, view=confirm_view, ephemeral=True)
        
        return callback
    
    async def previous_page(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ This shop isn't for you!", ephemeral=True)
            return
        self.page -= 1
        self.update_buttons()
        await self.update_shop_message(interaction)
    
    async def next_page(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ This shop isn't for you!", ephemeral=True)
            return
        self.page += 1
        self.update_buttons()
        await self.update_shop_message(interaction)
    
    async def show_inventory(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ This isn't your inventory!", ephemeral=True)
            return
        await self.display_inventory(interaction)
    
    async def close_shop(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ This shop isn't for you!", ephemeral=True)
            return
        await interaction.response.edit_message(content="🛒 Shop closed!", embed=None, view=None)
        self.stop()
    
    async def update_shop_message(self, interaction: discord.Interaction):
        embed = self.create_shop_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    def create_shop_embed(self):
        embed = discord.Embed(
            title="🌸 Petal Shop 🌸",
            description="Welcome to the Petal Shop! Browse our magical items:",
            color=0xff69b4
        )
        
        start_idx = self.page * self.items_per_page
        end_idx = min(start_idx + self.items_per_page, len(self.items_list))
        
        for i in range(start_idx, end_idx):
            item_id, item_data = self.items_list[i]
            embed.add_field(
                name=f"{item_data['emoji']} {item_data['name']}",
                value=f"**Price:** {item_data['price']:,} petals\n**Description:** {item_data['description']}\n**Type:** {item_data['type'].title()}",
                inline=False
            )
        
        balance = get_balance(self.ctx.author.id)
        embed.set_footer(text=f"Your Balance: {balance:,} petals | Page {self.page + 1}/{self.total_pages}")
        
        return embed
    
    async def display_inventory(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        inventory = get_inventory(user_id)
        
        if not inventory:
            embed = discord.Embed(
                title="🎒 Your Inventory",
                description="You don't have any items yet! Visit the shop with `b!shop` to buy some!",
                color=0xffa500
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🎒 Your Inventory",
            description="Here are all the items you own:",
            color=0x00ff88
        )
        
        total_value = 0
        for item_id, quantity in inventory.items():
            if item_id in shop_items:
                item_data = shop_items[item_id]
                item_value = item_data['price'] * quantity
                total_value += item_value
                embed.add_field(
                    name=f"{item_data['emoji']} {item_data['name']} x{quantity}",
                    value=f"Value: {item_value:,} petals | {item_data['description']}",
                    inline=False
                )
        
        embed.set_footer(text=f"Total Inventory Value: {total_value:,} petals")
        await interaction.response.send_message(embed=embed, ephemeral=True)

class ConfirmPurchaseView(View):
    def __init__(self, ctx, item_id, item_data, price):
        super().__init__(timeout=30.0)
        self.ctx = ctx
        self.item_id = item_id
        self.item_data = item_data
        self.price = price
    
    @discord.ui.button(label="✅ Confirm", style=discord.ButtonStyle.success, emoji="✅")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ This isn't your purchase!", ephemeral=True)
            return
        
        balance = get_balance(interaction.user.id)
        
        if balance < self.price:
            await interaction.response.send_message(f"❌ You no longer have enough petals! Need **{self.price:,}** petals", ephemeral=True)
            self.stop()
            return
        
        update_balance(interaction.user.id, -self.price)
        add_to_inventory(interaction.user.id, self.item_id)
        
        if self.item_id == "mystery_box":
            reward = random.choice([500, 1000, 2500, 5000, 10000, 25000])
            update_balance(interaction.user.id, reward)
            embed = discord.Embed(
                title="🎁 Mystery Box Opened! 🎁",
                description=f"You opened the mystery box and found **{reward:,} petals** inside!",
                color=0x00ff00
            )
        else:
            embed = discord.Embed(
                title="✅ Purchase Successful!",
                description=f"You bought **{self.item_data['emoji']} {self.item_data['name']}** for **{self.price:,} petals**!",
                color=0x00ff00
            )
        
        embed.add_field(name="📊 New Balance", value=f"{get_balance(interaction.user.id):,} petals", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        self.stop()
    
    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.danger, emoji="❌")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ This isn't your purchase!", ephemeral=True)
            return
        
        await interaction.response.send_message("❌ Purchase cancelled!", ephemeral=True)
        self.stop()

# --- PET SHOP UI VIEWS ---
class PetShopView(View):
    def __init__(self, ctx, page=0):
        super().__init__(timeout=60.0)
        self.ctx = ctx
        self.page = page
        self.items_per_page = 4
        self.items_list = list(pet_shop_items.items())
        self.total_pages = (len(self.items_list) + self.items_per_page - 1) // self.items_per_page
        
        self.update_buttons()
    
    def update_buttons(self):
        self.clear_items()
        
        start_idx = self.page * self.items_per_page
        end_idx = min(start_idx + self.items_per_page, len(self.items_list))
        
        for i in range(start_idx, end_idx):
            pet_id, pet_data = self.items_list[i]
            price_str = f"{pet_data['price']:,}"
            button = Button(
                label=f"{pet_data['emoji']} {pet_data['name']} - {price_str}🌸",
                style=discord.ButtonStyle.secondary,
                custom_id=f"buy_pet_{pet_id}"
            )
            button.callback = self.create_buy_callback(pet_id, pet_data)
            self.add_item(button)
        
        if self.page > 0:
            prev_btn = Button(label="◀️ Previous", style=discord.ButtonStyle.primary)
            prev_btn.callback = self.previous_page
            self.add_item(prev_btn)
        
        page_btn = Button(label=f"📄 Page {self.page + 1}/{self.total_pages}", style=discord.ButtonStyle.secondary, disabled=True)
        self.add_item(page_btn)
        
        if self.page < self.total_pages - 1:
            next_btn = Button(label="Next ▶️", style=discord.ButtonStyle.primary)
            next_btn.callback = self.next_page
            self.add_item(next_btn)
        
        my_pets_btn = Button(label="🐾 My Pets", style=discord.ButtonStyle.success, emoji="🐾", row=2)
        my_pets_btn.callback = self.show_my_pets
        self.add_item(my_pets_btn)
        
        close_btn = Button(label="❌ Close", style=discord.ButtonStyle.danger, emoji="❌", row=2)
        close_btn.callback = self.close_shop
        self.add_item(close_btn)
    
    def create_buy_callback(self, pet_id, pet_data):
        async def callback(interaction: discord.Interaction):
            if interaction.user != self.ctx.author:
                await interaction.response.send_message("❌ This shop isn't for you!", ephemeral=True)
                return
            
            balance = get_balance(interaction.user.id)
            price = pet_data['price']
            
            if balance < price:
                await interaction.response.send_message(f"❌ You don't have enough petals! Need **{price:,}** petals, you have **{balance:,}**", ephemeral=True)
                return
            
            if interaction.user.id in player_pets and pet_id in player_pets[interaction.user.id]:
                await interaction.response.send_message(f"❌ You already own {pet_data['emoji']} {pet_data['name']}! You can't have duplicates.", ephemeral=True)
                return
            
            embed = discord.Embed(
                title=f"🐾 Confirm Pet Purchase",
                description=f"Are you sure you want to buy **{pet_data['emoji']} {pet_data['name']}** for **{price:,} petals**?\n\n{pet_data['description']}\n\n✨ **Daily Reward:** {pet_data['daily_reward']:,} petals\n📈 **Max Level:** {pet_data['max_level']}\n⭐ **Rarity:** {pet_data['rarity'].title()}",
                color=0xffa500
            )
            
            confirm_view = ConfirmPetPurchaseView(self.ctx, pet_id, pet_data, price)
            await interaction.response.send_message(embed=embed, view=confirm_view, ephemeral=True)
        
        return callback
    
    async def previous_page(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ This shop isn't for you!", ephemeral=True)
            return
        self.page -= 1
        self.update_buttons()
        await self.update_shop_message(interaction)
    
    async def next_page(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ This shop isn't for you!", ephemeral=True)
            return
        self.page += 1
        self.update_buttons()
        await self.update_shop_message(interaction)
    
    async def show_my_pets(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ This isn't your pet menu!", ephemeral=True)
            return
        await self.display_my_pets(interaction)
    
    async def close_shop(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ This shop isn't for you!", ephemeral=True)
            return
        await interaction.response.edit_message(content="🐾 Pet shop closed!", embed=None, view=None)
        self.stop()
    
    async def update_shop_message(self, interaction: discord.Interaction):
        embed = self.create_shop_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    def create_shop_embed(self):
        embed = discord.Embed(
            title="🐾 Magical Pet Shop 🐾",
            description="Welcome to the Pet Shop! Adopt a magical companion:",
            color=0xff69b4
        )
        
        start_idx = self.page * self.items_per_page
        end_idx = min(start_idx + self.items_per_page, len(self.items_list))
        
        for i in range(start_idx, end_idx):
            pet_id, pet_data = self.items_list[i]
            embed.add_field(
                name=f"{pet_data['emoji']} {pet_data['name']} [{pet_data['rarity'].title()}]",
                value=f"**Price:** {pet_data['price']:,} petals\n**Daily Reward:** {pet_data['daily_reward']:,} petals\n**Max Level:** {pet_data['max_level']}\n**Description:** {pet_data['description']}",
                inline=False
            )
        
        balance = get_balance(self.ctx.author.id)
        embed.set_footer(text=f"Your Balance: {balance:,} petals | Page {self.page + 1}/{self.total_pages}")
        
        return embed
    
    async def display_my_pets(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        
        if user_id not in player_pets or not player_pets[user_id]:
            embed = discord.Embed(
                title="🐾 Your Pets",
                description="You don't have any pets yet! Visit the pet shop with `b!petshop` to adopt one!",
                color=0xffa500
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        embed = discord.Embed(
            title=f"🐾 {interaction.user.display_name}'s Pets",
            description="Here are all your magical companions:",
            color=0x00ff88
        )
        
        for pet_id, pet in player_pets[user_id].items():
            pet_data = pet_shop_items[pet_id]
            equipped = "✅ EQUIPPED" if user_id in pet_equipped and pet_equipped[user_id] == pet_id else ""
            
            happiness_bar = "❤️" * (pet["happiness"] // 10) + "🖤" * (10 - (pet["happiness"] // 10))
            
            embed.add_field(
                name=f"{pet_data['emoji']} {pet.get('name', pet_data['name'])} {equipped}",
                value=f"**Level:** {pet['level']}/{pet_data['max_level']}\n**XP:** {pet['xp']:,}/{pet_data['xp_per_level'] * pet['level']:,}\n**Happiness:** {happiness_bar} {pet['happiness']}%\n**Daily Reward:** {pet_data['daily_reward'] + int(pet_data['daily_reward'] * (pet['level'] / 100)) + int(pet_data['daily_reward'] * (pet['happiness'] / 200)):,} petals",
                inline=False
            )
        
        embed.set_footer(text="Use b!pet equip <name> to equip | b!pet feed | b!pet play | b!pet collect")
        await interaction.response.send_message(embed=embed, ephemeral=True)

class ConfirmPetPurchaseView(View):
    def __init__(self, ctx, pet_id, pet_data, price):
        super().__init__(timeout=30.0)
        self.ctx = ctx
        self.pet_id = pet_id
        self.pet_data = pet_data
        self.price = price
    
    @discord.ui.button(label="✅ Adopt", style=discord.ButtonStyle.success, emoji="✅")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ This isn't your purchase!", ephemeral=True)
            return
        
        balance = get_balance(interaction.user.id)
        
        if balance < self.price:
            await interaction.response.send_message(f"❌ You no longer have enough petals! Need **{self.price:,}** petals", ephemeral=True)
            self.stop()
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
        
        embed = discord.Embed(
            title="🐾 Pet Adopted! 🐾",
            description=f"You adopted **{self.pet_data['emoji']} {self.pet_data['name']}** for **{self.price:,} petals**!\n\nYour new companion is ready to explore with you!",
            color=0x00ff00
        )
        embed.add_field(name="✨ Daily Reward", value=f"{self.pet_data['daily_reward']:,} petals per day", inline=True)
        embed.add_field(name="📊 New Balance", value=f"{get_balance(interaction.user.id):,} petals", inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        self.stop()
    
    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.danger, emoji="❌")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ This isn't your purchase!", ephemeral=True)
            return
        
        await interaction.response.send_message("❌ Adoption cancelled!", ephemeral=True)
        self.stop()

# --- AUTO-SAVE TASK ---
async def auto_save():
    while True:
        await asyncio.sleep(60)
        save_all_data()
        print("💾 Auto-saved all data!")

# --- AUTOMATED TASKS ---
@tasks.loop(hours=1)
async def hourly_leaderboard():
    for g_id, c_id in server_channels.items():
        chan = bot.get_channel(c_id)
        if chan and economy:
            top = sorted(economy.items(), key=lambda x: x[1], reverse=True)[:5]
            if top:
                leaderboard_text = ""
                for i, (user_id, petals) in enumerate(top, 1):
                    medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "📊"
                    leaderboard_text += f"{medal} **{i}.** <@{user_id}> — `{petals}` petals\n"
                
                embed = discord.Embed(
                    title="🏆 Hourly Top Gardeners 🏆",
                    description=leaderboard_text,
                    color=0xffb7c5
                )
                await chan.send(embed=embed)
            else:
                embed = discord.Embed(
                    title="🏆 Hourly Top Gardeners 🏆",
                    description="No petals found yet! Start playing! 🌸",
                    color=0xffb7c5
                )
                await chan.send(embed=embed)

# --- REWARD COMMANDS ---
@bot.command()
async def daily(ctx):
    user_id = ctx.author.id
    now = datetime.now()
    
    if user_id in daily_cooldown:
        time_passed = (now - daily_cooldown[user_id]).total_seconds()
        if time_passed < 86400:
            remaining = 86400 - time_passed
            hours = int(remaining // 3600)
            minutes = int((remaining % 3600) // 60)
            return await ctx.send(f"⏰ You already claimed your daily reward! Come back in {hours}h {minutes}m!")
    
    reward = random.randint(300, 700)
    update_balance(user_id, reward)
    daily_cooldown[user_id] = now
    save_all_data()
    
    embed = discord.Embed(
        title="📅 DAILY REWARD!",
        description=f"{ctx.author.mention} received **{reward} petals**!",
        color=0x00ff00
    )
    await ctx.send(embed=embed)

@bot.command()
async def weekly(ctx):
    user_id = ctx.author.id
    now = datetime.now()
    
    if user_id in weekly_cooldown:
        time_passed = (now - weekly_cooldown[user_id]).total_seconds()
        if time_passed < 604800:
            remaining = 604800 - time_passed
            days = int(remaining // 86400)
            hours = int((remaining % 86400) // 3600)
            return await ctx.send(f"⏰ You already claimed your weekly reward! Come back in {days}d {hours}h!")
    
    reward = random.randint(2000, 5000)
    update_balance(user_id, reward)
    weekly_cooldown[user_id] = now
    save_all_data()
    
    embed = discord.Embed(
        title="📅 WEEKLY REWARD!",
        description=f"{ctx.author.mention} received **{reward} petals**!",
        color=0x00ff00
    )
    await ctx.send(embed=embed)

@bot.command()
async def hourly(ctx):
    user_id = ctx.author.id
    now = datetime.now()
    
    if user_id in hourly_cooldown:
        time_passed = (now - hourly_cooldown[user_id]).total_seconds()
        if time_passed < 3600:
            remaining = 3600 - time_passed
            minutes = int(remaining // 60)
            return await ctx.send(f"⏰ You already claimed your hourly reward! Come back in {minutes}m!")
    
    reward = random.randint(30, 80)
    update_balance(user_id, reward)
    hourly_cooldown[user_id] = now
    save_all_data()
    
    embed = discord.Embed(
        title="⏰ HOURLY REWARD!",
        description=f"{ctx.author.mention} received **{reward} petals**!",
        color=0x00ff00
    )
    await ctx.send(embed=embed)

# --- DAILY COMMANDS ---
@bot.command()
async def beg(ctx):
    user_id = ctx.author.id
    
    on_cooldown, remaining = check_cooldown(beg_cooldown, user_id)
    if on_cooldown:
        time_str = format_time(remaining)
        embed = discord.Embed(
            title="⏰ Too Soon!",
            description=f"You already begged today! Come back in **{time_str}**",
            color=0xff0000
        )
        embed.set_footer(text="You can only beg once per day!")
        return await ctx.send(embed=embed)
    
    reward = random.randint(30, 100)
    update_balance(user_id, reward)
    set_cooldown(beg_cooldown, user_id)
    
    beg_responses = [
        f"🌸 A kind stranger gave you **{reward} petals**!",
        f"💐 You found **{reward} petals** on the ground!",
        f"🌺 Someone dropped **{reward} petals** - finders keepers!",
        f"🌻 A fairy blessed you with **{reward} petals**!",
        f"🎭 A mysterious benefactor donated **{reward} petals** to you!"
    ]
    
    embed = discord.Embed(
        title="🌸 Begging Successful! 🌸",
        description=random.choice(beg_responses),
        color=0x00ff88
    )
    embed.set_footer(text="Come back tomorrow for more petals!")
    await ctx.send(embed=embed)

@bot.command()
async def farm(ctx):
    user_id = ctx.author.id
    
    on_cooldown, remaining = check_cooldown(farm_cooldown, user_id)
    if on_cooldown:
        time_str = format_time(remaining)
        embed = discord.Embed(
            title="⏰ Too Soon!",
            description=f"Your crops are still growing! Come back in **{time_str}**",
            color=0xff0000
        )
        embed.set_footer(text="You can only farm once per day!")
        return await ctx.send(embed=embed)
    
    reward = random.randint(120, 300)
    update_balance(user_id, reward)
    set_cooldown(farm_cooldown, user_id)
    
    farm_responses = [
        f"🚜 You harvested a bountiful crop of **{reward} petals**!",
        f"🌾 Your fields yielded **{reward} petals** today!",
        f"🍎 The apple trees gave you **{reward} petals**!",
        f"🌽 The corn harvest brought **{reward} petals**!",
        f"🍓 Your strawberry patch produced **{reward} petals**!"
    ]
    
    embed = discord.Embed(
        title="🚜 Harvest Time! 🚜",
        description=random.choice(farm_responses),
        color=0x8B4513
    )
    embed.set_footer(text="Your crops will grow back tomorrow!")
    await ctx.send(embed=embed)

@bot.command()
async def hunt(ctx):
    user_id = ctx.author.id
    
    on_cooldown, remaining = check_cooldown(hunt_cooldown, user_id)
    if on_cooldown:
        time_str = format_time(remaining)
        embed = discord.Embed(
            title="⏰ Too Soon!",
            description=f"The forest needs time to replenish! Come back in **{time_str}**",
            color=0xff0000
        )
        embed.set_footer(text="You can only hunt once per day!")
        return await ctx.send(embed=embed)
    
    reward = random.randint(60, 200)
    update_balance(user_id, reward)
    set_cooldown(hunt_cooldown, user_id)
    
    hunt_responses = [
        f"🏹 You tracked down a deer and found **{reward} petals**!",
        f"🐗 Your hunting expedition brought **{reward} petals**!",
        f"🦌 You discovered a hidden stash worth **{reward} petals**!",
        f"🐇 Your traps caught enough for **{reward} petals**!",
        f"🦊 You found a treasure while hunting: **{reward} petals**!"
    ]
    
    embed = discord.Embed(
        title="🏹 Hunting Expedition! 🏹",
        description=random.choice(hunt_responses),
        color=0x228B22
    )
    embed.set_footer(text="The animals will return tomorrow!")
    await ctx.send(embed=embed)

@bot.command()
async def work(ctx):
    user_id = ctx.author.id
    
    on_cooldown, remaining = check_cooldown(work_cooldown, user_id)
    if on_cooldown:
        time_str = format_time(remaining)
        embed = discord.Embed(
            title="⏰ Too Soon!",
            description=f"You're tired from work! Come back in **{time_str}**",
            color=0xff0000
        )
        embed.set_footer(text="You can only work once per day!")
        return await ctx.send(embed=embed)
    
    reward = random.randint(90, 250)
    update_balance(user_id, reward)
    set_cooldown(work_cooldown, user_id)
    
    work_responses = [
        f"💼 You completed your daily shift and earned **{reward} petals**!",
        f"🏢 Your boss gave you a bonus of **{reward} petals**!",
        f"📊 You finished all your tasks and received **{reward} petals**!",
        f"🎯 Your hard work paid off with **{reward} petals**!",
        f"⭐ You got employee of the day and won **{reward} petals**!"
    ]
    
    embed = discord.Embed(
        title="💼 Work Complete! 💼",
        description=random.choice(work_responses),
        color=0x4169E1
    )
    embed.set_footer(text="Come back tomorrow for another day of work!")
    await ctx.send(embed=embed)

# --- GIFTING SYSTEM ---
@bot.command()
async def gift(ctx, member: discord.Member, amount: int):
    if member == ctx.author:
        return await ctx.send("❌ You can't gift petals to yourself!")
    
    if member.bot:
        return await ctx.send("❌ You can't gift petals to a bot!")
    
    if amount <= 0:
        return await ctx.send("❌ Gift amount must be positive!")
    
    sender_balance = get_balance(ctx.author.id)
    if sender_balance < amount:
        return await ctx.send(f"❌ You don't have enough petals! You have **{sender_balance}** petals but tried to gift **{amount}**!")
    
    user_id = ctx.author.id
    today = datetime.now().date()
    
    if user_id in gift_cooldown:
        last_gift_date, total_gifted = gift_cooldown[user_id]
        if last_gift_date == today:
            if total_gifted + amount > DAILY_GIFT_LIMIT:
                remaining = DAILY_GIFT_LIMIT - total_gifted
                return await ctx.send(f"❌ You've reached your daily gifting limit! You can only gift **{DAILY_GIFT_LIMIT:,}** petals per day.\nYou have **{remaining:,}** petals remaining today!")
            new_total = total_gifted + amount
        else:
            new_total = amount
    else:
        new_total = amount
    
    if amount > DAILY_GIFT_LIMIT:
        return await ctx.send(f"❌ You can only gift up to **{DAILY_GIFT_LIMIT:,}** petals per day!")
    
    update_balance(ctx.author.id, -amount)
    update_balance(member.id, amount)
    
    gift_cooldown[user_id] = (today, new_total)
    save_all_data()
    
    embed = discord.Embed(
        title="🎁 GIFT SENT! 🎁",
        description=f"{ctx.author.mention} gifted **{amount:,} petals** to {member.mention}!",
        color=0xff69b4
    )
    
    remaining_today = DAILY_GIFT_LIMIT - new_total
    embed.add_field(name="📊 Your Daily Gifting Status", value=f"Used today: **{new_total:,}** / {DAILY_GIFT_LIMIT:,}\nRemaining: **{remaining_today:,}** petals", inline=False)
    embed.set_footer(text=f"Your new balance: {get_balance(ctx.author.id):,} petals")
    
    await ctx.send(embed=embed)

@bot.command()
async def giftstats(ctx):
    user_id = ctx.author.id
    today = datetime.now().date()
    
    if user_id in gift_cooldown:
        last_gift_date, total_gifted = gift_cooldown[user_id]
        if last_gift_date == today:
            remaining = DAILY_GIFT_LIMIT - total_gifted
            embed = discord.Embed(
                title="🎁 Your Daily Gifting Stats",
                description=f"**Today's Gifts:** {total_gifted:,} / {DAILY_GIFT_LIMIT:,} petals",
                color=0xff69b4
            )
            embed.add_field(name="✅ Remaining Today", value=f"{remaining:,} petals", inline=True)
            embed.add_field(name="📅 Reset Time", value="Midnight UTC", inline=True)
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="🎁 Your Daily Gifting Stats",
                description=f"**Today's Gifts:** 0 / {DAILY_GIFT_LIMIT:,} petals",
                color=0xff69b4
            )
            embed.add_field(name="✅ Remaining Today", value=f"{DAILY_GIFT_LIMIT:,} petals", inline=True)
            embed.add_field(name="📅 Reset Time", value="Midnight UTC", inline=True)
            await ctx.send(embed=embed)
    else:
        embed = discord.Embed(
            title="🎁 Your Daily Gifting Stats",
            description=f"**Today's Gifts:** 0 / {DAILY_GIFT_LIMIT:,} petals",
            color=0xff69b4
        )
        embed.add_field(name="✅ Remaining Today", value=f"{DAILY_GIFT_LIMIT:,} petals", inline=True)
        embed.add_field(name="📅 Reset Time", value="Midnight UTC", inline=True)
        await ctx.send(embed=embed)

# --- ADMIN COMMANDS ---
@bot.command()
async def gen(ctx, code: str, value: int, uses: int):
    if ctx.author.name not in ADMINS:
        embed = discord.Embed(title="❌ Permission Denied", description="You don't have permission!", color=0xff0000)
        return await ctx.send(embed=embed)
    
    redeem_codes[code.upper()] = {"value": value, "uses": uses}
    save_all_data()
    embed = discord.Embed(
        title="🎟️ Voucher Created!",
        description=f"**Code:** `{code.upper()}`\n**Value:** {value} petals\n**Uses:** {uses}",
        color=0x00ff00
    )
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def setup(ctx):
    server_channels[ctx.guild.id] = ctx.channel.id
    save_all_data()
    embed = discord.Embed(title="✅ Setup Complete!", description=f"Leaderboard updates to {ctx.channel.mention}", color=0x00ff00)
    await ctx.send(embed=embed)

@bot.command()
async def give(ctx, member: discord.Member, amount: int):
    if ctx.author.name not in ADMINS:
        embed = discord.Embed(title="❌ Permission Denied", description="Only admins can use this!", color=0xff0000)
        return await ctx.send(embed=embed)
    
    update_balance(member.id, amount)
    embed = discord.Embed(title="✅ Petals Given!", description=f"Gave **{amount} petals** to {member.mention}", color=0x00ff00)
    await ctx.send(embed=embed)

@bot.command()
async def reset_cooldowns(ctx, user: discord.Member = None):
    if ctx.author.name not in ADMINS:
        return await ctx.send("❌ You don't have permission to use this command!")
    
    target = user if user else ctx.author
    
    if target.id in beg_cooldown:
        del beg_cooldown[target.id]
    if target.id in farm_cooldown:
        del farm_cooldown[target.id]
    if target.id in hunt_cooldown:
        del hunt_cooldown[target.id]
    if target.id in work_cooldown:
        del work_cooldown[target.id]
    
    save_all_data()
    embed = discord.Embed(
        title="✅ Cooldowns Reset!",
        description=f"Reset all daily command cooldowns for {target.mention}",
        color=0x00ff00
    )
    await ctx.send(embed=embed)

@bot.command()
async def reset_gift(ctx, user: discord.Member = None):
    if ctx.author.name not in ADMINS:
        return await ctx.send("❌ You don't have permission to use this command!")
    
    target = user if user else ctx.author
    
    if target.id in gift_cooldown:
        del gift_cooldown[target.id]
        save_all_data()
        embed = discord.Embed(
            title="✅ Gift Cooldown Reset!",
            description=f"Reset daily gifting limit for {target.mention}",
            color=0x00ff00
        )
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(
            title="ℹ️ No Cooldown Found",
            description=f"{target.mention} hasn't gifted any petals today!",
            color=0xffa500
        )
        await ctx.send(embed=embed)

@bot.command()
async def add_item(ctx, member: discord.Member, item: str, quantity: int = 1):
    if ctx.author.name not in ADMINS:
        return await ctx.send("❌ You don't have permission to use this command!")
    
    item_id = None
    for key, value in shop_items.items():
        if value['name'].lower() == item.lower():
            item_id = key
            break
    
    if not item_id:
        return await ctx.send(f"❌ Item '{item}' not found!")
    
    add_to_inventory(member.id, item_id, quantity)
    embed = discord.Embed(
        title="✅ Item Added!",
        description=f"Added **{quantity}x {shop_items[item_id]['emoji']} {shop_items[item_id]['name']}** to {member.mention}",
        color=0x00ff00
    )
    await ctx.send(embed=embed)

@bot.command()
async def remove_item(ctx, member: discord.Member, item: str, quantity: int = 1):
    if ctx.author.name not in ADMINS:
        return await ctx.send("❌ You don't have permission to use this command!")
    
    item_id = None
    for key, value in shop_items.items():
        if value['name'].lower() == item.lower():
            item_id = key
            break
    
    if not item_id:
        return await ctx.send(f"❌ Item '{item}' not found!")
    
    if has_item(member.id, item_id, quantity):
        remove_from_inventory(member.id, item_id, quantity)
        embed = discord.Embed(
            title="✅ Item Removed!",
            description=f"Removed **{quantity}x {shop_items[item_id]['emoji']} {shop_items[item_id]['name']}** from {member.mention}",
            color=0x00ff00
        )
    else:
        embed = discord.Embed(
            title="❌ Not Enough Items!",
            description=f"{member.mention} doesn't have {quantity}x {shop_items[item_id]['emoji']} {shop_items[item_id]['name']}!",
            color=0xff0000
        )
    await ctx.send(embed=embed)

@bot.command()
async def add_pet(ctx, member: discord.Member, pet_name: str):
    if ctx.author.name not in ADMINS:
        return await ctx.send("❌ You don't have permission to use this command!")
    
    pet_id = None
    for key, value in pet_shop_items.items():
        if value['name'].lower() == pet_name.lower():
            pet_id = key
            break
    
    if not pet_id:
        return await ctx.send(f"❌ Pet '{pet_name}' not found!")
    
    if member.id not in player_pets:
        player_pets[member.id] = {}
    
    if pet_id in player_pets[member.id]:
        return await ctx.send(f"❌ {member.mention} already owns {pet_shop_items[pet_id]['emoji']} {pet_name}!")
    
    player_pets[member.id][pet_id] = {
        "name": pet_shop_items[pet_id]['name'],
        "level": 1,
        "xp": 0,
        "happiness": 100,
        "last_fed": datetime.now(),
        "last_played": datetime.now()
    }
    
    save_all_data()
    embed = discord.Embed(
        title="✅ Pet Added!",
        description=f"Added **{pet_shop_items[pet_id]['emoji']} {pet_name}** to {member.mention}",
        color=0x00ff00
    )
    await ctx.send(embed=embed)

@bot.command()
async def remove_pet(ctx, member: discord.Member, pet_name: str):
    if ctx.author.name not in ADMINS:
        return await ctx.send("❌ You don't have permission to use this command!")
    
    pet_id = None
    for key, value in pet_shop_items.items():
        if value['name'].lower() == pet_name.lower():
            pet_id = key
            break
    
    if not pet_id:
        return await ctx.send(f"❌ Pet '{pet_name}' not found!")
    
    if member.id in player_pets and pet_id in player_pets[member.id]:
        del player_pets[member.id][pet_id]
        
        if member.id in pet_equipped and pet_equipped[member.id] == pet_id:
            del pet_equipped[member.id]
        
        save_all_data()
        embed = discord.Embed(
            title="✅ Pet Removed!",
            description=f"Removed **{pet_shop_items[pet_id]['emoji']} {pet_name}** from {member.mention}",
            color=0x00ff00
        )
    else:
        embed = discord.Embed(
            title="❌ Pet Not Found!",
            description=f"{member.mention} doesn't own {pet_name}!",
            color=0xff0000
        )
    await ctx.send(embed=embed)

# --- USER COMMANDS ---
@bot.command()
async def cooldowns(ctx):
    user_id = ctx.author.id
    
    embed = discord.Embed(
        title="⏰ Your Daily Command Status",
        description="Here's when you can use your daily commands again:",
        color=0xffb7c5
    )
    
    on_cooldown, remaining = check_cooldown(beg_cooldown, user_id)
    if on_cooldown:
        embed.add_field(name="🌸 Beg", value=f"Available in: {format_time(remaining)}", inline=False)
    else:
        embed.add_field(name="🌸 Beg", value="✅ Available now!", inline=False)
    
    on_cooldown, remaining = check_cooldown(farm_cooldown, user_id)
    if on_cooldown:
        embed.add_field(name="🚜 Farm", value=f"Available in: {format_time(remaining)}", inline=False)
    else:
        embed.add_field(name="🚜 Farm", value="✅ Available now!", inline=False)
    
    on_cooldown, remaining = check_cooldown(hunt_cooldown, user_id)
    if on_cooldown:
        embed.add_field(name="🏹 Hunt", value=f"Available in: {format_time(remaining)}", inline=False)
    else:
        embed.add_field(name="🏹 Hunt", value="✅ Available now!", inline=False)
    
    on_cooldown, remaining = check_cooldown(work_cooldown, user_id)
    if on_cooldown:
        embed.add_field(name="💼 Work", value=f"Available in: {format_time(remaining)}", inline=False)
    else:
        embed.add_field(name="💼 Work", value="✅ Available now!", inline=False)
    
    await ctx.send(embed=embed)

@bot.command()
async def lb(ctx):
    if not economy:
        embed = discord.Embed(title="🏆 Leaderboard", description="No petals found yet!", color=0xffb7c5)
        return await ctx.send(embed=embed)
    
    top = sorted(economy.items(), key=lambda x: x[1], reverse=True)[:10]
    leaderboard_text = ""
    for i, (user_id, petals) in enumerate(top, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "📊"
        leaderboard_text += f"{medal} **{i}.** <@{user_id}> — `{petals}` petals\n"
    
    embed = discord.Embed(title="🌸 Global Leaderboard", description=leaderboard_text, color=0xffb7c5)
    await ctx.send(embed=embed)

@bot.command()
async def bal(ctx):
    balance = get_balance(ctx.author.id)
    rank_emoji = "👑" if balance >= 10000 else "💎" if balance >= 5000 else "🌟" if balance >= 1000 else "⭐" if balance >= 500 else "🌸" if balance >= 100 else "🌱"
    embed = discord.Embed(title=f"{rank_emoji} {ctx.author.display_name}'s Garden", description=f"**Petals:** `{balance}`", color=0xffb7c5)
    await ctx.send(embed=embed)

# --- INVENTORY AND SHOP COMMANDS ---
@bot.command()
async def shop(ctx, page: int = 1):
    if page < 1:
        page = 1
    
    view = ShopView(ctx, page - 1)
    embed = view.create_shop_embed()
    await ctx.send(embed=embed, view=view)

@bot.command()
async def inventory(ctx, member: discord.Member = None):
    target = member if member else ctx.author
    
    inventory = get_inventory(target.id)
    
    if not inventory:
        embed = discord.Embed(
            title="🎒 Inventory",
            description=f"{target.mention} doesn't have any items yet!",
            color=0xffa500
        )
        await ctx.send(embed=embed)
        return
    
    embed = discord.Embed(
        title=f"🎒 {target.display_name}'s Inventory",
        description="Here are all the items they own:",
        color=0x00ff88
    )
    
    total_value = 0
    for item_id, quantity in inventory.items():
        if item_id in shop_items:
            item_data = shop_items[item_id]
            item_value = item_data['price'] * quantity
            total_value += item_value
            embed.add_field(
                name=f"{item_data['emoji']} {item_data['name']} x{quantity}",
                value=f"Value: {item_value:,} petals",
                inline=False
            )
    
    embed.set_footer(text=f"Total Inventory Value: {total_value:,} petals")
    await ctx.send(embed=embed)

@bot.command()
async def use(ctx, *, item: str):
    item_id = None
    
    for key, value in shop_items.items():
        if value['name'].lower() == item.lower():
            item_id = key
            break
    
    if not item_id:
        return await ctx.send(f"❌ Item '{item}' not found! Check `b!inventory` to see your items")
    
    if not has_item(ctx.author.id, item_id):
        return await ctx.send(f"❌ You don't have {shop_items[item_id]['emoji']} {shop_items[item_id]['name']}!")
    
    if item_id == "lucky_charm":
        expiry = datetime.now() + timedelta(hours=24)
        player_buffs[ctx.author.id] = {"luck": True, "expires": expiry}
        remove_from_inventory(ctx.author.id, item_id)
        
        embed = discord.Embed(
            title="🍀 Lucky Charm Activated!",
            description=f"{ctx.author.mention} used a Lucky Charm!\nYou have 5% better odds in games for 24 hours!",
            color=0x00ff00
        )
        embed.add_field(name="⏰ Expires", value=f"<t:{int(expiry.timestamp())}:R>", inline=False)
        await ctx.send(embed=embed)
    
    elif item_id == "xp_boost":
        expiry = datetime.now() + timedelta(hours=24)
        player_buffs[ctx.author.id] = {"xp_boost": True, "expires": expiry}
        remove_from_inventory(ctx.author.id, item_id)
        
        embed = discord.Embed(
            title="⚡ XP Boost Activated!",
            description=f"{ctx.author.mention} used an XP Boost!\nDaily rewards doubled for 24 hours!",
            color=0x00ff00
        )
        embed.add_field(name="⏰ Expires", value=f"<t:{int(expiry.timestamp())}:R>", inline=False)
        await ctx.send(embed=embed)
    
    elif item_id == "protection_amulet":
        player_buffs[ctx.author.id] = player_buffs.get(ctx.author.id, {})
        player_buffs[ctx.author.id]["protection"] = player_buffs[ctx.author.id].get("protection", 0) + 1
        remove_from_inventory(ctx.author.id, item_id)
        
        embed = discord.Embed(
            title="🛡️ Protection Amulet Activated!",
            description=f"{ctx.author.mention} used a Protection Amulet!\nYou're protected from your next loss!",
            color=0x00ff00
        )
        await ctx.send(embed=embed)
    
    elif item_id == "double_win":
        player_buffs[ctx.author.id] = player_buffs.get(ctx.author.id, {})
        player_buffs[ctx.author.id]["double_win"] = player_buffs[ctx.author.id].get("double_win", 0) + 1
        remove_from_inventory(ctx.author.id, item_id)
        
        embed = discord.Embed(
            title="🎰 Double Win Token Activated!",
            description=f"{ctx.author.mention} used a Double Win Token!\nYour next win will be doubled!",
            color=0x00ff00
        )
        await ctx.send(embed=embed)
    
    elif item_id == "mystery_box":
        reward = random.choice([500, 1000, 2500, 5000, 10000, 25000])
        update_balance(ctx.author.id, reward)
        remove_from_inventory(ctx.author.id, item_id)
        
        embed = discord.Embed(
            title="🎁 Mystery Box Opened! 🎁",
            description=f"{ctx.author.mention} opened a mystery box and found **{reward:,} petals** inside!",
            color=0x00ff00
        )
        await ctx.send(embed=embed)
    
    elif item_id == "bank_vault":
        player_permanents[ctx.author.id] = player_permanents.get(ctx.author.id, {})
        player_permanents[ctx.author.id]["bank_vault"] = True
        remove_from_inventory(ctx.author.id, item_id)
        
        embed = discord.Embed(
            title="🏦 Bank Vault Activated!",
            description=f"{ctx.author.mention} unlocked a Bank Vault!\nYour daily gift limit is now **1,500,000** petals!",
            color=0x00ff00
        )
        await ctx.send(embed=embed)
    
    else:
        item_data = shop_items[item_id]
        remove_from_inventory(ctx.author.id, item_id)
        embed = discord.Embed(
            title=f"{item_data['emoji']} Item Used!",
            description=f"{ctx.author.mention} used {item_data['name']}!\n*You admire its beauty before it disappears...*",
            color=0xff69b4
        )
        await ctx.send(embed=embed)
    
    save_all_data()

@bot.command()
async def buffs(ctx):
    user_id = ctx.author.id
    now = datetime.now()
    
    embed = discord.Embed(
        title="✨ Your Active Buffs ✨",
        color=0xff69b4
    )
    
    has_buffs = False
    
    if user_id in player_buffs:
        buffs = player_buffs[user_id]
        
        if "luck" in buffs and buffs["luck"]:
            expiry = buffs.get("expires")
            if expiry and expiry > now:
                has_buffs = True
                embed.add_field(name="🍀 Lucky Charm", value=f"5% better odds\nExpires: <t:{int(expiry.timestamp())}:R>", inline=False)
            else:
                del buffs["luck"]
        
        if "xp_boost" in buffs and buffs["xp_boost"]:
            expiry = buffs.get("expires")
            if expiry and expiry > now:
                has_buffs = True
                embed.add_field(name="⚡ XP Boost", value=f"Doubled daily rewards\nExpires: <t:{int(expiry.timestamp())}:R>", inline=False)
            else:
                del buffs["xp_boost"]
        
        if "protection" in buffs and buffs["protection"] > 0:
            has_buffs = True
            embed.add_field(name="🛡️ Protection Amulets", value=f"{buffs['protection']} remaining\nProtects from your next loss(es)", inline=False)
        
        if "double_win" in buffs and buffs["double_win"] > 0:
            has_buffs = True
            embed.add_field(name="🎰 Double Win Tokens", value=f"{buffs['double_win']} remaining\nDoubles your next win(s)", inline=False)
    
    if user_id in player_permanents:
        perms = player_permanents[user_id]
        if "bank_vault" in perms and perms["bank_vault"]:
            has_buffs = True
            embed.add_field(name="🏦 Bank Vault", value="Daily gift limit: **1,500,000** petals (up from 1,000,000)", inline=False)
    
    if not has_buffs:
        embed.description = "You have no active buffs! Visit the shop with `b!shop` to buy some!"
    else:
        embed.set_footer(text="Use items with b!use <item name>")
    
    await ctx.send(embed=embed)

# --- PET COMMANDS ---
@bot.command()
async def petshop(ctx, page: int = 1):
    if page < 1:
        page = 1
    
    view = PetShopView(ctx, page - 1)
    embed = view.create_shop_embed()
    await ctx.send(embed=embed, view=view)

@bot.command()
async def mypets(ctx):
    user_id = ctx.author.id
    
    if user_id not in player_pets or not player_pets[user_id]:
        embed = discord.Embed(
            title="🐾 Your Pets",
            description="You don't have any pets yet! Visit the pet shop with `b!petshop` to adopt one!",
            color=0xffa500
        )
        await ctx.send(embed=embed)
        return
    
    embed = discord.Embed(
        title=f"🐾 {ctx.author.display_name}'s Pets",
        description="Here are all your magical companions:",
        color=0x00ff88
    )
    
    for pet_id, pet in player_pets[user_id].items():
        pet_data = pet_shop_items[pet_id]
        equipped = "✅ **EQUIPPED**" if user_id in pet_equipped and pet_equipped[user_id] == pet_id else ""
        
        happiness_bar = "❤️" * (pet["happiness"] // 10) + "🖤" * (10 - (pet["happiness"] // 10))
        xp_needed = pet_data['xp_per_level'] * pet['level']
        
        embed.add_field(
            name=f"{pet_data['emoji']} {pet.get('name', pet_data['name'])} {equipped}",
            value=f"**Level:** {pet['level']}/{pet_data['max_level']}\n**XP:** {pet['xp']:,}/{xp_needed:,}\n**Happiness:** {happiness_bar} {pet['happiness']}%\n**Daily Reward:** {pet_data['daily_reward'] + int(pet_data['daily_reward'] * (pet['level'] / 100)) + int(pet_data['daily_reward'] * (pet['happiness'] / 200)):,} petals",
            inline=False
        )
    
    embed.set_footer(text="Use b!pet <name> to interact | b!pet equip <name> | b!pet rename <name> <new name>")
    await ctx.send(embed=embed)

@bot.command()
async def pet(ctx, action: str = None, *, name: str = None):
    user_id = ctx.author.id
    
    if user_id not in pet_equipped:
        if user_id in player_pets and player_pets[user_id]:
            first_pet = list(player_pets[user_id].keys())[0]
            pet_equipped[user_id] = first_pet
            save_all_data()
        else:
            return await ctx.send("❌ You don't have any pets! Visit `b!petshop` to adopt one!")
    
    if action is None:
        pet_id = pet_equipped[user_id]
        pet = player_pets[user_id][pet_id]
        pet_data = pet_shop_items[pet_id]
        
        happiness_bar = "❤️" * (pet["happiness"] // 10) + "🖤" * (10 - (pet["happiness"] // 10))
        xp_needed = pet_data['xp_per_level'] * pet['level']
        xp_bar_length = 20
        xp_filled = int((pet["xp"] / xp_needed) * xp_bar_length) if xp_needed > 0 else xp_bar_length
        xp_bar = "🟢" * min(xp_filled, xp_bar_length) + "⚫" * max(0, xp_bar_length - xp_filled)
        
        embed = discord.Embed(
            title=f"🐾 Your Active Pet: {pet_data['emoji']} {pet.get('name', pet_data['name'])}",
            description=f"**Level:** {pet['level']}/{pet_data['max_level']}\n**XP:** {pet['xp']:,}/{xp_needed:,}\n{xp_bar}\n**Happiness:** {happiness_bar} {pet['happiness']}%\n**Daily Reward:** {pet_data['daily_reward'] + int(pet_data['daily_reward'] * (pet['level'] / 100)) + int(pet_data['daily_reward'] * (pet['happiness'] / 200)):,} petals",
            color=0xff69b4
        )
        embed.add_field(name="📋 Actions", value="• `b!pet feed` - Feed your pet\n• `b!pet play` - Play with your pet\n• `b!pet collect` - Collect daily reward\n• `b!pet equip <name>` - Equip a different pet\n• `b!pet rename <name>` - Rename your pet", inline=False)
        embed.set_footer(text="Happy pets give better rewards! Keep them happy!")
        
        await ctx.send(embed=embed)
    
    elif action.lower() == "equip":
        if not name:
            return await ctx.send("❌ Please specify which pet to equip! Example: `b!pet equip \"Garden Cat\"`")
        
        found_pet = None
        found_pet_id = None
        
        for pet_id, pet in player_pets[user_id].items():
            pet_data = pet_shop_items[pet_id]
            if pet.get('name', pet_data['name']).lower() == name.lower():
                found_pet = pet
                found_pet_id = pet_id
                break
        
        if found_pet:
            pet_equipped[user_id] = found_pet_id
            save_all_data()
            pet_data = pet_shop_items[found_pet_id]
            await ctx.send(f"✅ You equipped **{pet_data['emoji']} {found_pet.get('name', pet_data['name'])}** as your active pet!")
        else:
            await ctx.send(f"❌ Could not find a pet named '{name}'!")
    
    elif action.lower() == "rename":
        if not name:
            return await ctx.send("❌ Please specify a new name! Example: `b!pet rename Fluffy`")
        
        if len(name) > 20:
            return await ctx.send("❌ Pet name must be 20 characters or less!")
        
        pet_id = pet_equipped[user_id]
        old_name = player_pets[user_id][pet_id].get('name', pet_shop_items[pet_id]['name'])
        player_pets[user_id][pet_id]['name'] = name
        save_all_data()
        
        await ctx.send(f"✅ Your pet **{old_name}** has been renamed to **{name}**!")
    
    elif action.lower() == "feed":
        pet_id = pet_equipped[user_id]
        pet = player_pets[user_id][pet_id]
        pet_data = pet_shop_items[pet_id]
        
        on_cooldown, remaining = check_cooldown(pet_feed_cooldown, user_id, 1800)
        if on_cooldown:
            time_str = format_time(remaining)
            return await ctx.send(f"⏰ Your pet is still full! Come back in **{time_str}**")
        
        old_happiness = pet["happiness"]
        pet["happiness"] = min(100, pet["happiness"] + 20)
        pet["last_fed"] = datetime.now()
        set_cooldown(pet_feed_cooldown, user_id)
        
        pet["xp"] += 50
        
        leveled_up = False
        xp_needed = pet_data['xp_per_level'] * pet['level']
        while pet["xp"] >= xp_needed and pet["level"] < pet_data["max_level"]:
            pet["xp"] -= xp_needed
            pet["level"] += 1
            leveled_up = True
            xp_needed = pet_data['xp_per_level'] * pet['level']
        
        embed = discord.Embed(
            title=f"🍖 Feeding {pet_data['emoji']} {pet.get('name', pet_data['name'])}",
            description=f"You fed your pet! Happiness increased from {old_happiness}% to {pet['happiness']}%! +50 XP",
            color=0x00ff00
        )
        
        if leveled_up:
            embed.add_field(name="🎉 LEVEL UP! 🎉", value=f"Your pet reached level {pet['level']}!", inline=False)
        
        save_all_data()
        await ctx.send(embed=embed)
    
    elif action.lower() == "play":
        pet_id = pet_equipped[user_id]
        pet = player_pets[user_id][pet_id]
        pet_data = pet_shop_items[pet_id]
        
        on_cooldown, remaining = check_cooldown(pet_play_cooldown, user_id, 3600)
        if on_cooldown:
            time_str = format_time(remaining)
            return await ctx.send(f"⏰ Your pet is tired from playing! Come back in **{time_str}**")
        
        old_happiness = pet["happiness"]
        pet["happiness"] = min(100, pet["happiness"] + 15)
        pet["last_played"] = datetime.now()
        set_cooldown(pet_play_cooldown, user_id)
        
        pet["xp"] += 75
        
        leveled_up = False
        xp_needed = pet_data['xp_per_level'] * pet['level']
        while pet["xp"] >= xp_needed and pet["level"] < pet_data["max_level"]:
            pet["xp"] -= xp_needed
            pet["level"] += 1
            leveled_up = True
            xp_needed = pet_data['xp_per_level'] * pet['level']
        
        embed = discord.Embed(
            title=f"🎾 Playing with {pet_data['emoji']} {pet.get('name', pet_data['name'])}",
            description=f"You played with your pet! Happiness increased from {old_happiness}% to {pet['happiness']}%! +75 XP",
            color=0x00ff00
        )
        
        if leveled_up:
            embed.add_field(name="🎉 LEVEL UP! 🎉", value=f"Your pet reached level {pet['level']}!", inline=False)
        
        save_all_data()
        await ctx.send(embed=embed)
    
    elif action.lower() == "collect":
        pet_id = pet_equipped[user_id]
        pet = player_pets[user_id][pet_id]
        pet_data = pet_shop_items[pet_id]
        
        now = datetime.now()
        if user_id in pet_cooldown and (now - pet_cooldown[user_id]).total_seconds() < 86400:
            remaining = 86400 - (now - pet_cooldown[user_id]).total_seconds()
            hours = int(remaining // 3600)
            minutes = int((remaining % 3600) // 60)
            return await ctx.send(f"⏰ You already collected your pet's daily reward! Come back in {hours}h {minutes}m!")
        
        base_reward = pet_data['daily_reward']
        level_bonus = int(base_reward * (pet['level'] / 100))
        happiness_bonus = int(base_reward * (pet['happiness'] / 200))
        reward = base_reward + level_bonus + happiness_bonus
        
        update_balance(user_id, reward)
        pet_cooldown[user_id] = now
        
        pet["xp"] += 25
        
        leveled_up = False
        xp_needed = pet_data['xp_per_level'] * pet['level']
        while pet["xp"] >= xp_needed and pet["level"] < pet_data["max_level"]:
            pet["xp"] -= xp_needed
            pet["level"] += 1
            leveled_up = True
            xp_needed = pet_data['xp_per_level'] * pet['level']
        
        embed = discord.Embed(
            title=f"💰 Daily Reward from {pet_data['emoji']} {pet.get('name', pet_data['name'])}",
            description=f"Your pet gave you **{reward:,} petals**! +25 XP",
            color=0x00ff00
        )
        
        if leveled_up:
            embed.add_field(name="🎉 LEVEL UP! 🎉", value=f"Your pet reached level {pet['level']}!", inline=False)
        
        embed.add_field(name="📊 New Balance", value=f"{get_balance(user_id):,} petals", inline=False)
        
        save_all_data()
        await ctx.send(embed=embed)
    
    else:
        await ctx.send("❌ Invalid action! Use: `feed`, `play`, `collect`, `equip`, or `rename`")

@bot.command()
async def petstats(ctx, member: discord.Member = None):
    target = member if member else ctx.author
    user_id = target.id
    
    if user_id not in pet_equipped:
        if user_id in player_pets and player_pets[user_id]:
            first_pet = list(player_pets[user_id].keys())[0]
            pet_equipped[user_id] = first_pet
            save_all_data()
        else:
            return await ctx.send(f"❌ {target.mention} doesn't have any pets yet!")
    
    pet_id = pet_equipped[user_id]
    pet = player_pets[user_id][pet_id]
    pet_data = pet_shop_items[pet_id]
    
    happiness_bar = "❤️" * (pet["happiness"] // 10) + "🖤" * (10 - (pet["happiness"] // 10))
    xp_needed = pet_data['xp_per_level'] * pet['level']
    xp_bar_length = 20
    xp_filled = int((pet["xp"] / xp_needed) * xp_bar_length) if xp_needed > 0 else xp_bar_length
    xp_bar = "🟢" * min(xp_filled, xp_bar_length) + "⚫" * max(0, xp_bar_length - xp_filled)
    
    embed = discord.Embed(
        title=f"🐾 {target.display_name}'s Pet",
        description=f"{pet_data['emoji']} **{pet.get('name', pet_data['name'])}** [{pet_data['rarity'].title()}]",
        color=0xff69b4
    )
    embed.add_field(name="📊 Stats", value=f"**Level:** {pet['level']}/{pet_data['max_level']}\n**XP:** {pet['xp']:,}/{xp_needed:,}\n{xp_bar}\n**Happiness:** {happiness_bar} {pet['happiness']}%\n**Daily Reward:** {pet_data['daily_reward'] + int(pet_data['daily_reward'] * (pet['level'] / 100)) + int(pet_data['daily_reward'] * (pet['happiness'] / 200)):,} petals", inline=False)
    
    await ctx.send(embed=embed)

# --- GAME COMMANDS ---
@bot.command()
async def blackjack(ctx, bet: int):
    if get_balance(ctx.author.id) < bet or bet <= 0:
        return await ctx.send("❌ Not enough petals!")
    
    p = [random.randint(1, 11), random.randint(1, 11)]
    d = [random.randint(1, 11), random.randint(1, 11)]
    
    embed = discord.Embed(title="🃏 BLACKJACK", description=f"**Your hand:** {p} = **{sum(p)}**\n**Dealer shows:** [{d[0]}, ?]\n\nType `hit` or `stand`!", color=0xff69b4)
    await ctx.send(embed=embed)
    
    def check(m): 
        return m.author == ctx.author and m.content.lower() in ['hit', 'stand']
    
    try:
        while sum(p) < 21:
            msg = await bot.wait_for('message', check=check, timeout=20)
            if msg.content.lower() == 'hit':
                p.append(random.randint(1, 11))
                if sum(p) > 21:
                    break
                embed = discord.Embed(title="🃏 BLACKJACK", description=f"**Your hand:** {p} = **{sum(p)}**\nType `hit` or `stand`!", color=0xff69b4)
                await ctx.send(embed=embed)
            else:
                break
    except:
        pass
    
    pt, dt = sum(p), sum(d)
    while dt < 17:
        d.append(random.randint(1, 11))
        dt = sum(d)
    
    if pt > 21:
        update_balance(ctx.author.id, -bet)
        result = "💥 BUST! You went over 21!"
        color = 0xff0000
    elif dt > 21:
        win = int(bet * 0.95)
        update_balance(ctx.author.id, win)
        result = f"🎉 WIN! Dealer busted! You won {win} petals!"
        color = 0x00ff00
    elif pt > dt:
        win = int(bet * 0.95)
        update_balance(ctx.author.id, win)
        result = f"🎉 WIN! You beat the dealer! You won {win} petals!"
        color = 0x00ff00
    elif pt <= dt:
        update_balance(ctx.author.id, -bet)
        result = "💔 LOSS! The dealer wins!"
        color = 0xff0000
    
    embed = discord.Embed(title="🃏 GAME RESULT", description=f"**Your hand:** {p} = **{pt}**\n**Dealer hand:** {d} = **{dt}**\n\n{result}", color=color)
    await ctx.send(embed=embed)

@bot.command()
async def rps(ctx, choice: str, bet: int):
    if get_balance(ctx.author.id) < bet:
        return await ctx.send("❌ Not enough petals!")
    
    valid_choices = ["rock", "paper", "scissors"]
    user_choice = choice.lower()
    
    if user_choice not in valid_choices:
        return await ctx.send("❌ Invalid choice! Choose: `rock`, `paper`, or `scissors`")
    
    bot_choice = random.choice(valid_choices)
    choice_emojis = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}
    
    if user_choice == bot_choice:
        update_balance(ctx.author.id, -bet)
        result = f"💔 TIE GOES TO HOUSE! -{bet} petals!"
        color = 0xff0000
    elif (user_choice == "rock" and bot_choice == "scissors") or (user_choice == "paper" and bot_choice == "rock") or (user_choice == "scissors" and bot_choice == "paper"):
        win = int(bet * 0.9)
        update_balance(ctx.author.id, win)
        result = f"🎉 WIN! +{win} petals!"
        color = 0x00ff00
    else:
        update_balance(ctx.author.id, -bet)
        result = f"💔 LOSS! -{bet} petals!"
        color = 0xff0000
    
    embed = discord.Embed(title="✂️ RPS", description=f"**You:** {choice_emojis[user_choice]} {user_choice}\n**Bot:** {choice_emojis[bot_choice]} {bot_choice}\n\n{result}", color=color)
    await ctx.send(embed=embed)

@bot.command()
async def crash(ctx, bet: int):
    if get_balance(ctx.author.id) < bet or bet <= 0:
        return await ctx.send("❌ Not enough petals!")
    
    embed = discord.Embed(title="✈️ CRASH GAME", description=f"**Bet:** {bet} petals\n⚠️ HIGH RISK! Cash out before the plane crashes!", color=0xff0000)
    msg = await ctx.send(embed=embed)
    v = CrashView(ctx, bet)
    await v.start_flight(msg)

@bot.command()
async def mines(ctx, bet: int):
    if get_balance(ctx.author.id) < bet or bet <= 0:
        return await ctx.send("❌ Not enough petals!")
    
    bombs = random.sample(range(1, 10), 4)
    embed = discord.Embed(title="💣 MINESWEEPER", description=f"**Bet:** {bet} petals\n⚠️ 4 bombs hidden! Find safe flowers!", color=0xff69b4)
    await ctx.send(embed=embed, view=MinesView(ctx, bet, bombs))

@bot.command()
async def color(ctx, bet: int):
    if get_balance(ctx.author.id) < bet or bet <= 0:
        return await ctx.send("❌ Not enough petals!")
    
    embed = discord.Embed(title="🎨 COLOR PREDICTOR", description=f"**Bet:** {bet} petals\nPick a color!", color=0xff69b4)
    await ctx.send(embed=embed, view=ColorView(ctx, bet))

@bot.command()
async def dice(ctx, bet: int):
    if get_balance(ctx.author.id) < bet:
        return await ctx.send("❌ Not enough petals!")
    
    embed = discord.Embed(title="🎲 DICE DUEL", description=f"**Bet:** {bet} petals\nClick the button to roll!", color=0xffa500)
    await ctx.send(embed=embed, view=DiceDuelView(ctx, bet))

@bot.command()
async def slots(ctx, bet: int):
    if get_balance(ctx.author.id) < bet or bet <= 0:
        return await ctx.send("❌ Not enough petals!")
    
    embed = discord.Embed(title="🎰 SLOT MACHINE", description=f"**Bet:** {bet} petals\nClick SPIN to try your luck!", color=0xffa500)
    await ctx.send(embed=embed, view=SlotMachineView(ctx, bet))

@bot.command()
async def coinflip(ctx, bet: int):
    if get_balance(ctx.author.id) < bet or bet <= 0:
        return await ctx.send("❌ Not enough petals!")
    
    embed = discord.Embed(title="🪙 COINFLIP", description=f"**Bet:** {bet} petals\nChoose Heads or Tails!", color=0xffa500)
    await ctx.send(embed=embed, view=CoinflipView(ctx, bet))

@bot.command()
async def higherlower(ctx, bet: int):
    if get_balance(ctx.author.id) < bet or bet <= 0:
        return await ctx.send("❌ Not enough petals!")
    
    card_names = {1:"A", 11:"J", 12:"Q", 13:"K"}
    current_card = random.randint(1, 13)
    current_display = card_names.get(current_card, str(current_card))
    
    card_emojis = {
        1: "🃏", 2: "2️⃣", 3: "3️⃣", 4: "4️⃣", 5: "5️⃣", 
        6: "6️⃣", 7: "7️⃣", 8: "8️⃣", 9: "9️⃣", 10: "🔟",
        11: "👑", 12: "👸", 13: "🤴"
    }
    current_emoji = card_emojis.get(current_card, "🎴")
    
    embed = discord.Embed(
        title="🎴 HIGHER OR LOWER 🎴", 
        description=f"**Your Card:** {current_emoji} **{current_display}**\n\n**💰 Bet:** {bet} petals\n\n⬆️ Will the next card be **HIGHER** or **LOWER**? ⬇️\n\n*Click a button to guess!*",
        color=0xffa500
    )
    embed.set_footer(text="Aces are low (1), Kings are high (13)")
    
    view = HigherLowerView(ctx, bet, current_card, current_display, current_emoji)
    await ctx.send(embed=embed, view=view)

@bot.command()
async def roulette(ctx, bet: int):
    if get_balance(ctx.author.id) < bet or bet <= 0:
        return await ctx.send("❌ Not enough petals!")
    
    embed = discord.Embed(title="🎡 ROULETTE", description=f"**Bet:** {bet} petals\nBet on Red, Black, or Green!", color=0xffa500)
    await ctx.send(embed=embed, view=RouletteView(ctx, bet))

@bot.command()
async def tower(ctx, bet: int):
    if get_balance(ctx.author.id) < bet or bet <= 0:
        return await ctx.send("❌ Not enough petals!")
    
    embed = discord.Embed(title="🏰 TOWER CLIMB", description=f"**Bet:** {bet} petals\nClimb the tower and cash out!", color=0xffa500)
    await ctx.send(embed=embed, view=TowerView(ctx, bet))

@bot.command()
async def scratch(ctx, bet: int):
    if get_balance(ctx.author.id) < bet or bet <= 0:
        return await ctx.send("❌ Not enough petals!")
    
    embed = discord.Embed(title="🎫 SCRATCH CARD", description=f"**Bet:** {bet} petals\nScratch all three cards!", color=0xffa500)
    await ctx.send(embed=embed, view=ScratchView(ctx, bet))

@bot.command()
async def treasure(ctx, bet: int):
    if get_balance(ctx.author.id) < bet or bet <= 0:
        return await ctx.send("❌ Not enough petals!")
    
    embed = discord.Embed(title="💎 TREASURE HUNT", description=f"**Bet:** {bet} petals\nFind the treasure in 2 attempts! (6 spots)", color=0xffa500)
    await ctx.send(embed=embed, view=TreasureHuntView(ctx, bet))

@bot.command()
async def roulettegun(ctx, bet: int):
    if get_balance(ctx.author.id) < bet or bet <= 0:
        return await ctx.send("❌ Not enough petals!")
    
    embed = discord.Embed(
        title="💀 RUSSIAN ROULETTE - EXTREME MODE 💀",
        description=f"**Bet:** {bet} petals\n⚠️ **3 BULLETS, 6 CHAMBERS!**\n💀 50% chance to die on first pull!\nPull the trigger up to 3 times or cash out early!\n\n*Each safe pull increases your reward multiplier!*",
        color=0xff0000
    )
    embed.add_field(name="💀 Death Odds", value="First pull: 50%\nSecond pull: 60%\nThird pull: 75%", inline=True)
    embed.add_field(name="💰 Max Win", value=f"{bet * 3} petals (3x bet)", inline=True)
    await ctx.send(embed=embed, view=RussianRouletteView(ctx, bet))

@bot.command()
async def race(ctx, bet: int):
    if get_balance(ctx.author.id) < bet or bet <= 0:
        return await ctx.send("❌ Not enough petals!")
    
    embed = discord.Embed(title="🏇 HORSE RACING", description=f"**Bet:** {bet} petals\nPick a horse to win!", color=0xffa500)
    await ctx.send(embed=embed, view=RaceView(ctx, bet))

@bot.command()
async def poker(ctx, bet: int):
    if get_balance(ctx.author.id) < bet or bet <= 0:
        return await ctx.send("❌ Not enough petals!")
    
    embed = discord.Embed(title="🃏 POKER", description=f"**Bet:** {bet} petals\nFace off against the bot!", color=0xffa500)
    await ctx.send(embed=embed, view=PokerView(ctx, bet))

@bot.command()
async def duel(ctx, opponent: discord.Member, bet: int):
    if opponent == ctx.author:
        return await ctx.send("❌ You can't duel yourself!")
    
    if opponent.bot:
        return await ctx.send("❌ You can't duel a bot!")
    
    if bet <= 0:
        return await ctx.send("❌ Bet must be positive!")
    
    if bet < 50:
        return await ctx.send("❌ Minimum duel bet is 50 petals!")
    
    if get_balance(ctx.author.id) < bet:
        return await ctx.send(f"❌ You don't have enough petals! You need **{bet} petals** to start this duel!")
    
    embed = discord.Embed(
        title="⚔️ DUEL CHALLENGE! ⚔️",
        description=f"{ctx.author.mention} has challenged {opponent.mention} to a duel!\n\n**💰 Bet:** {bet} petals\n**💀 Winner takes all!**\n\n{opponent.mention}, do you accept the challenge?",
        color=0xffa500
    )
    embed.add_field(name="⚔️ Combat Rules", value="• Turn-based combat\n• Choose weapons to attack\n• Critical hits possible!\n• 10% chance to miss\n• First to 0 HP loses\n• Surrender option available", inline=False)
    
    view = DuelRequestView(ctx, opponent, bet)
    await ctx.send(embed=embed, view=view)

@bot.command()
async def redeem(ctx):
    embed = discord.Embed(title="🎟️ Redeem Voucher", description="Click below to redeem a voucher!", color=0xff69b4)
    await ctx.send(embed=embed, view=RedeemStarterView())

@bot.command()
async def help(ctx):
    embed = discord.Embed(title="🌸 Blossom Garden - Help Menu", description="Here's everything you can do:", color=0xffb7c5)
    
    embed.add_field(name="🌱 **Daily Earnings**", value="`beg`, `farm`, `hunt`, `work` - Each once per day!\n`daily`, `weekly`, `hourly` - Time-based rewards!", inline=False)
    embed.add_field(name="🐾 **Pets**", value="`petshop` - Adopt magical pets (1M - 250M petals)\n`mypets` - View your pets\n`pet` - Interact with your pet (feed/play/collect)\n`petstats` - View pet stats", inline=False)
    embed.add_field(name="🛒 **Shop & Items**", value="`shop` - Browse and buy items\n`inventory` - Check your items\n`use <item>` - Use an item\n`buffs` - Check active buffs", inline=False)
    embed.add_field(name="🎁 **Gifting**", value="`gift @player <amount>` - Gift petals to friends!\n`giftstats` - Check your daily gifting limit\n*(Max 1,000,000 petals per day)*", inline=False)
    embed.add_field(name="⚔️ **PvP Game**", value="`duel @player <amount>` - Challenge other players to a duel!", inline=False)
    embed.add_field(name="🎲 **Casino Games**", value="`crash`, `mines`, `color`, `blackjack`, `dice`, `rps`, `slots`, `coinflip`, `higherlower`, `roulette`, `tower`, `scratch`, `treasure`, `roulettegun`, `race`, `poker`", inline=False)
    embed.add_field(name="ℹ️ **Info**", value="`bal` - Check balance\n`lb` - Leaderboard\n`cooldowns` - Check daily command status", inline=False)
    embed.add_field(name="🎟️ **Admin**", value="`gen`, `setup`, `give`, `reset_cooldowns`, `reset_gift`, `add_item`, `remove_item`, `add_pet`, `remove_pet`", inline=False)
    embed.set_footer(text="🌸 All data is saved permanently with MongoDB! Adopt pets for daily rewards! 🌸")
    await ctx.send(embed=embed)

# --- ADMIN MANAGEMENT ---
@bot.command()
@commands.is_owner()
async def add_admin(ctx, username: str):
    if username not in ADMINS:
        ADMINS.append(username)
        await ctx.send(f"✅ Added {username} as admin!")

@bot.command()
@commands.is_owner()
async def remove_admin(ctx, username: str):
    if username in ADMINS:
        ADMINS.remove(username)
        await ctx.send(f"✅ Removed {username} from admins!")

@bot.command()
async def admins(ctx):
    await ctx.send(f"👑 **Admins:** {', '.join(ADMINS)}")

# --- START THE BOT ---
@bot.event
async def on_ready():
    print(f'🌸 {bot.user} is fully loaded!')
    print(f'📊 Serving {len(bot.guilds)} servers')
    print(f'👑 Admins: {", ".join(ADMINS)}')
    print(f'💾 Database mode: {"MongoDB Atlas" if USE_MONGODB else "Local File"}')
    
    # Start auto-save task
    bot.loop.create_task(auto_save())
    
    if not hourly_leaderboard.is_running(): 
        hourly_leaderboard.start()

keep_alive()
bot.run(TOKEN)
