import discord
from discord.ext import commands
import random
import asyncio
import os
from dotenv import load_dotenv
from keep_alive import keep_alive
# Load the .env file
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
keep_alive()
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="b!", intents=intents)
bot.remove_command('help')

# --- DATABASE (In-Memory) ---
economy = {}

def get_balance(user_id):
    return economy.get(user_id, 0)

def update_balance(user_id, amount):
    economy[user_id] = get_balance(user_id) + amount

# --- EVENTS ---
@bot.event
async def on_ready():
    print(f'🌸 Blossom Buddies is now active as {bot.user}')
    await bot.change_presence(activity=discord.Game(name="b!help | Tending the Garden"))

# --- CUSTOM HELP ---
@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="🌸 Blossom Buddies Instructions",
        description="Welcome! Use the commands below to collect petals and play games.",
        color=0xffb7c5
    )
    embed.add_field(name="🌱 Earn Petals", value="`b!beg`, `b!work`, `b!hunt`, `b!farm`", inline=True)
    embed.add_field(name="🎲 Mini-Games", value="`b!rps`, `b!dice`, `b!blackjack`", inline=True)
    embed.add_field(name="💰 Wallet", value="`b!balance`", inline=False)
    embed.set_footer(text="Tip: Bets require a number, e.g., b!dice 50")
    await ctx.send(embed=embed)

# --- ECONOMY COMMANDS ---
@bot.command()
async def balance(ctx):
    bal = get_balance(ctx.author.id)
    await ctx.send(f"👛 **{ctx.author.display_name}**, you have **{bal} petals**.")

@bot.command()
@commands.cooldown(1, 30, commands.BucketType.user)
async def beg(ctx):
    gain = random.randint(5, 25)
    update_balance(ctx.author.id, gain)
    await ctx.send(f"🌸 You begged a passerby and received **{gain} petals**.")

@bot.command()
@commands.cooldown(1, 60, commands.BucketType.user)
async def work(ctx):
    gain = random.randint(50, 150)
    update_balance(ctx.author.id, gain)
    await ctx.send(f"💼 You worked as a floral designer and earned **{gain} petals**.")

@bot.command()
@commands.cooldown(1, 120, commands.BucketType.user)
async def farm(ctx):
    gain = random.randint(150, 400)
    update_balance(ctx.author.id, gain)
    await ctx.send(f"🚜 Harvest time! You gathered **{gain} petals** from your garden.")

@bot.command()
@commands.cooldown(1, 60, commands.BucketType.user)
async def hunt(ctx):
    if random.random() < 0.2:
        await ctx.send("🏹 The butterflies were too fast today. You found nothing.")
    else:
        gain = random.randint(60, 120)
        update_balance(ctx.author.id, gain)
        await ctx.send(f"🏹 You caught a rare moth! Sold for **{gain} petals**.")

# --- MINI GAMES ---
@bot.command()
async def dice(ctx, bet: int):
    if get_balance(ctx.author.id) < bet or bet <= 0:
        return await ctx.send("❌ You don't have enough petals!")
    
    u_roll, b_roll = random.randint(1, 6), random.randint(1, 6)
    if u_roll > b_roll:
        update_balance(ctx.author.id, bet)
        await ctx.send(f"🎲 **Win!** You: {u_roll} | Me: {b_roll}. +{bet} petals!")
    elif u_roll < b_roll:
        update_balance(ctx.author.id, -bet)
        await ctx.send(f"🎲 **Loss!** You: {u_roll} | Me: {b_roll}. -{bet} petals.")
    else:
        await ctx.send(f"🎲 **Tie!** Both rolled {u_roll}.")

@bot.command()
async def rps(ctx, choice: str, bet: int):
    if get_balance(ctx.author.id) < bet or bet <= 0:
        return await ctx.send("❌ Insufficient petals.")
    
    options = ["rock", "paper", "scissors"]
    bot_choice = random.choice(options)
    user_choice = choice.lower()
    
    if user_choice not in options:
        return await ctx.send("Choose `rock`, `paper`, or `scissors`.")

    if user_choice == bot_choice:
        msg = "It's a tie!"
    elif (user_choice == "rock" and bot_choice == "scissors") or \
         (user_choice == "paper" and bot_choice == "rock") or \
         (user_choice == "scissors" and bot_choice == "paper"):
        update_balance(ctx.author.id, bet)
        msg = f"You won **{bet} petals**!"
    else:
        update_balance(ctx.author.id, -bet)
        msg = f"You lost **{bet} petals**."
    
    await ctx.send(f"🌸 I chose **{bot_choice}**. {msg}")

# --- COOLDOWN ERROR HANDLER ---
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏳ Slow down, sprout! Try again in {error.retry_after:.1f}s.")

bot.run(TOKEN)
