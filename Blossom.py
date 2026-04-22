import discord
from discord.ext import commands, tasks
from discord.ui import Button, View, Modal, TextInput
import random
import asyncio
import os
from dotenv import load_dotenv
from keep_alive import keep_alive

# --- BOT CONFIGURATION ---
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True 
bot = commands.Bot(command_prefix="b!", intents=intents)
bot.remove_command('help')

# --- ADMIN LIST ---
ADMINS = ["dispute12", "xion0624"]  # Added xion0624 as admin

# --- DATABASE ---
economy = {}
server_channels = {} 
redeem_codes = {} 

def get_balance(user_id):
    return economy.get(user_id, 0)

def update_balance(user_id, amount):
    economy[user_id] = get_balance(user_id) + amount

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
                
                # Create fancy embed for redemption
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

# --- UI: CRASH GAME (Enhanced Graphics) ---
class CrashView(View):
    def __init__(self, ctx, bet):
        super().__init__(timeout=120.0)
        self.ctx, self.bet, self.multiplier = ctx, bet, 1.0
        self.cashed_out, self.crashed = False, False
    
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
        embed.set_footer(text="Safe landing! ✈️")
        await interaction.response.edit_message(embed=embed, view=None)
    
    async def start_flight(self, msg):
        crash_at = round(random.uniform(1.1, 10.0), 2) if random.random() > 0.1 else 1.0
        flight_emoji = ["✈️", "🛩️", "🚀", "🪂", "🌠"]
        emoji_index = 0
        
        while not self.cashed_out:
            await asyncio.sleep(1.6)
            if self.cashed_out: 
                break
            self.multiplier += random.uniform(0.1, 0.4)
            emoji_index = (emoji_index + 1) % len(flight_emoji)
            
            if self.multiplier >= crash_at:
                self.crashed = True
                self.stop()
                update_balance(self.ctx.author.id, -self.bet)
                
                embed = discord.Embed(
                    title="💥 CRASH! 💥",
                    description=f"The plane exploded at **{crash_at:.2f}x** multiplier!",
                    color=0xff0000
                )
                embed.add_field(name="💔 Loss", value=f"Lost **{self.bet} petals**", inline=False)
                embed.set_footer(text="Better luck next time! 💀")
                await msg.edit(embed=embed, view=None)
                break
            
            # Create graphical flight status
            progress_bar = self.create_progress_bar(self.multiplier, crash_at)
            embed = discord.Embed(
                title=f"{flight_emoji[emoji_index]} FLIGHT STATUS",
                description=f"**Multiplier:** {self.multiplier:.2f}x\n{progress_bar}",
                color=0xffa500
            )
            embed.add_field(name="🎯 Target", value=f"{crash_at:.2f}x", inline=True)
            embed.add_field(name="💰 Current Payout", value=f"{int(self.bet * self.multiplier)} petals", inline=True)
            await msg.edit(embed=embed, view=self)
    
    def create_progress_bar(self, current, target):
        bar_length = 15
        filled = int((current / target) * bar_length)
        if filled > bar_length:
            filled = bar_length
        bar = "🟩" * filled + "⬜" * (bar_length - filled)
        return f"`{current:.2f}x`\n{bar}\n`{target:.2f}x`"

# --- UI: MINES GAME (Enhanced Graphics) ---
class MinesButton(Button):
    def __init__(self, num): 
        super().__init__(label="🌸", style=discord.ButtonStyle.secondary, row=(num-1)//3, emoji="🌸")
        self.num = num
        self.revealed_num = num
    
    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if interaction.user != view.ctx.author: 
            return
        
        if self.num in view.bombs:
            view.stop()
            update_balance(view.ctx.author.id, -view.bet)
            # Reveal all bombs
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
            
            mult = round(1.3 ** view.revealed, 2)
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
                embed.add_field(name="📊 Multiplier", value=f"**{mult}x**", inline=True)
                await i.response.edit_message(embed=embed, view=view)
            
            btn = discord.utils.get(view.children, label="💰 Cashout")
            if not btn: 
                btn = Button(label="💰 Cashout", style=discord.ButtonStyle.primary, emoji="💎", row=3)
                btn.callback = co
                view.add_item(btn)
            else: 
                btn.callback = co
            
            # Update game status
            embed = discord.Embed(
                title="🌸 Minesweeper Garden 🌸",
                description=f"**Safe tiles found:** {view.revealed}\n**Current multiplier:** {mult}x\n**Potential win:** {val} petals",
                color=0x00ff88
            )
            await interaction.response.edit_message(embed=embed, view=view)

class MinesView(View):
    def __init__(self, ctx, bet, bombs):
        super().__init__(timeout=60.0)
        self.ctx, self.bet, self.bombs, self.revealed = ctx, bet, bombs, 0
        for i in range(1, 10):
            self.add_item(MinesButton(i))

# --- UI: COLOR GAME (Enhanced Graphics) ---
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
        
        # Create fancy result display
        result_display = " 🎲 ".join(rolled)
        
        if hits > 0:
            win = view.bet * (hits + 1)
            update_balance(view.ctx.author.id, win - view.bet)
            embed = discord.Embed(
                title="🎉 VICTORY! 🎉",
                description=f"**Result:** {result_display}\n\n{interaction.user.mention} guessed **{self.color_name}** and it appeared **{hits} time(s)**!",
                color=0x00ff00
            )
            embed.add_field(name="🌸 Petals Won", value=f"+{win}", inline=True)
            embed.set_footer(text="Amazing prediction! 🌟")
        else:
            update_balance(view.ctx.author.id, -view.bet)
            embed = discord.Embed(
                title="💔 DEFEAT 💔",
                description=f"**Result:** {result_display}\n\n{interaction.user.mention} guessed **{self.color_name}** but it didn't appear!",
                color=0xff0000
            )
            embed.add_field(name="🌸 Petals Lost", value=f"-{view.bet}", inline=True)
            embed.set_footer(text="Better luck next time! 🍀")
        
        await interaction.response.edit_message(embed=embed, view=view)

class ColorView(View):
    def __init__(self, ctx, bet):
        super().__init__(timeout=30.0)
        self.ctx, self.bet = ctx, bet
        
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
        
        # Add instructions
        embed = discord.Embed(
            title="🎨 Color Predictor 🎨",
            description="Three colors will be randomly selected. Pick a color and win based on how many times it appears!",
            color=0xff69b4
        )
        embed.add_field(name="📊 Payout", value="1 appearance: 2x bet\n2 appearances: 3x bet\n3 appearances: 4x bet", inline=False)

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
                embed.set_footer(text="Keep playing to stay on top! 🌸")
                await chan.send(embed=embed)
            else:
                embed = discord.Embed(
                    title="🏆 Hourly Top Gardeners 🏆",
                    description="No petals found yet! Start playing to appear on the leaderboard! 🌸",
                    color=0xffb7c5
                )
                await chan.send(embed=embed)

@bot.event
async def on_ready():
    print(f'🌸 {bot.user} is fully loaded!')
    print(f'📊 Serving {len(bot.guilds)} servers')
    print(f'👑 Admins: {", ".join(ADMINS)}')
    if not hourly_leaderboard.is_running(): 
        hourly_leaderboard.start()

# --- ADMIN COMMANDS ---
@bot.command()
async def gen(ctx, code: str, value: int, uses: int):
    # Check if user is in admin list
    if ctx.author.name not in ADMINS:
        embed = discord.Embed(title="❌ Permission Denied", description="You don't have permission to use this command!", color=0xff0000)
        return await ctx.send(embed=embed)
    
    redeem_codes[code.upper()] = {"value": value, "uses": uses}
    embed = discord.Embed(
        title="🎟️ Voucher Created Successfully!",
        description=f"**Code:** `{code.upper()}`\n**Value:** {value} petals\n**Uses:** {uses}\n**Created by:** {ctx.author.name}",
        color=0x00ff00
    )
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def setup(ctx):
    server_channels[ctx.guild.id] = ctx.channel.id
    embed = discord.Embed(
        title="✅ Setup Complete!",
        description=f"Hourly leaderboard updates will be sent to {ctx.channel.mention}",
        color=0x00ff00
    )
    await ctx.send(embed=embed)

# --- USER COMMANDS ---
@bot.command()
async def lb(ctx):
    """Displays the top 10 players globally."""
    if not economy:
        embed = discord.Embed(
            title="🏆 Global Leaderboard 🏆",
            description="No petals found yet! Start playing to appear on the leaderboard! 🌸",
            color=0xffb7c5
        )
        return await ctx.send(embed=embed)
    
    top = sorted(economy.items(), key=lambda x: x[1], reverse=True)[:10]
    leaderboard_text = ""
    for i, (user_id, petals) in enumerate(top, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "📊"
        leaderboard_text += f"{medal} **{i}.** <@{user_id}> — `{petals}` petals\n"
    
    embed = discord.Embed(
        title="🌸 Global Leaderboard 🌸",
        description=leaderboard_text,
        color=0xffb7c5
    )
    embed.set_footer(text="Top 10 Gardeners")
    await ctx.send(embed=embed)

@bot.command()
async def beg(ctx):
    g = random.randint(10, 50)
    update_balance(ctx.author.id, g)
    
    beg_responses = [
        f"🌸 {ctx.author.mention}, a kind stranger gave you **{g} petals**!",
        f"💐 {ctx.author.mention}, you found **{g} petals** on the ground!",
        f"🌺 {ctx.author.mention}, someone dropped **{g} petals** - finders keepers!",
        f"🌻 {ctx.author.mention}, a fairy blessed you with **{g} petals**!"
    ]
    
    embed = discord.Embed(
        title="🌸 Begging Successful! 🌸",
        description=random.choice(beg_responses),
        color=0x00ff88
    )
    await ctx.send(embed=embed)

@bot.command()
async def farm(ctx):
    g = random.randint(200, 450)
    update_balance(ctx.author.id, g)
    
    embed = discord.Embed(
        title="🚜 Harvest Time! 🚜",
        description=f"{ctx.author.mention} harvested a bountiful crop of **{g} petals**!",
        color=0x8B4513
    )
    await ctx.send(embed=embed)

@bot.command()
async def hunt(ctx):
    g = random.randint(100, 300)
    update_balance(ctx.author.id, g)
    
    embed = discord.Embed(
        title="🏹 Hunting Expedition 🏹",
        description=f"{ctx.author.mention} returned from the hunt with **{g} petals**!",
        color=0x228B22
    )
    await ctx.send(embed=embed)

@bot.command()
async def bal(ctx):
    balance = get_balance(ctx.author.id)
    
    # Determine petal rank emoji
    if balance >= 10000:
        rank_emoji = "👑"
    elif balance >= 5000:
        rank_emoji = "💎"
    elif balance >= 1000:
        rank_emoji = "🌟"
    elif balance >= 500:
        rank_emoji = "⭐"
    elif balance >= 100:
        rank_emoji = "🌸"
    else:
        rank_emoji = "🌱"
    
    embed = discord.Embed(
        title=f"{rank_emoji} {ctx.author.display_name}'s Garden {rank_emoji}",
        description=f"**Petals:** `{balance}`",
        color=0xffb7c5
    )
    embed.set_footer(text="Keep growing your garden! 🌸")
    await ctx.send(embed=embed)

@bot.command()
async def crash(ctx, bet: int):
    if get_balance(ctx.author.id) < bet or bet <= 0:
        embed = discord.Embed(title="❌ Insufficient Petals!", description=f"You need {bet} petals to play!", color=0xff0000)
        return await ctx.send(embed=embed)
    
    embed = discord.Embed(
        title="✈️ CRASH GAME ✈️",
        description=f"**Bet:** {bet} petals\n**Target:** Cash out before the plane crashes!",
        color=0xffa500
    )
    msg = await ctx.send(embed=embed)
    v = CrashView(ctx, bet)
    await v.start_flight(msg)

@bot.command()
async def mines(ctx, bet: int):
    if get_balance(ctx.author.id) < bet or bet <= 0:
        embed = discord.Embed(title="❌ Insufficient Petals!", description=f"You need {bet} petals to play!", color=0xff0000)
        return await ctx.send(embed=embed)
    
    bombs = random.sample(range(1, 10), 3)
    embed = discord.Embed(
        title="💣 MINESWEEPER GARDEN 💣",
        description=f"**Bet:** {bet} petals\n**Bombs:** 3 hidden bombs\nClick on flowers to find safe spots!",
        color=0xff69b4
    )
    await ctx.send(embed=embed, view=MinesView(ctx, bet, bombs))

@bot.command()
async def color(ctx, bet: int):
    if get_balance(ctx.author.id) < bet or bet <= 0:
        embed = discord.Embed(title="❌ Insufficient Petals!", description=f"You need {bet} petals to play!", color=0xff0000)
        return await ctx.send(embed=embed)
    
    embed = discord.Embed(
        title="🎨 COLOR PREDICTOR 🎨",
        description=f"**Bet:** {bet} petals\nPick a color and see how many times it appears!",
        color=0xff69b4
    )
    await ctx.send(embed=embed, view=ColorView(ctx, bet))

@bot.command()
async def blackjack(ctx, bet: int):
    if get_balance(ctx.author.id) < bet or bet <= 0:
        embed = discord.Embed(title="❌ Insufficient Petals!", description=f"You need {bet} petals to play!", color=0xff0000)
        return await ctx.send(embed=embed)
    
    p = [random.randint(1, 11), random.randint(1, 11)]
    d = [random.randint(1, 11), random.randint(1, 11)]
    
    embed = discord.Embed(
        title="🃏 BLACKJACK 🃏",
        description=f"**Your hand:** {p} = **{sum(p)}**\n**Dealer shows:** [{d[0]}, ?]\n\nType `hit` or `stand` within 20 seconds!",
        color=0xff69b4
    )
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
                embed = discord.Embed(
                    title="🃏 BLACKJACK 🃏",
                    description=f"**Your hand:** {p} = **{sum(p)}**\n**Dealer shows:** [{d[0]}, ?]\n\nType `hit` or `stand`!",
                    color=0xff69b4
                )
                await ctx.send(embed=embed)
            else:
                break
    except asyncio.TimeoutError:
        pass
    
    pt, dt = sum(p), sum(d)
    while dt < 17:
        d.append(random.randint(1, 11))
        dt = sum(d)
    
    # Determine result
    if pt > 21:
        update_balance(ctx.author.id, -bet)
        result = "💥 BUST! You went over 21!"
        color = 0xff0000
    elif dt > 21 or pt > dt:
        update_balance(ctx.author.id, bet)
        result = "🎉 WIN! You beat the dealer!"
        color = 0x00ff00
    elif pt < dt:
        update_balance(ctx.author.id, -bet)
        result = "💔 LOSS! The dealer wins!"
        color = 0xff0000
    else:
        result = "🤝 TIE! Your bet is returned!"
        color = 0xffa500
    
    embed = discord.Embed(
        title="🃏 GAME RESULT 🃏",
        description=f"**Your hand:** {p} = **{pt}**\n**Dealer hand:** {d} = **{dt}**\n\n{result}",
        color=color
    )
    await ctx.send(embed=embed)

@bot.command()
async def dice(ctx, bet: int):
    if get_balance(ctx.author.id) < bet:
        embed = discord.Embed(title="❌ Insufficient Petals!", description=f"You need {bet} petals to play!", color=0xff0000)
        return await ctx.send(embed=embed)
    
    user_roll = random.randint(1, 6)
    bot_roll = random.randint(1, 6)
    
    dice_emojis = {
        1: "⚀", 2: "⚁", 3: "⚂",
        4: "⚃", 5: "⚄", 6: "⚅"
    }
    
    if user_roll > bot_roll:
        update_balance(ctx.author.id, bet)
        result = "🎉 WIN! 🎉"
        color = 0x00ff00
    elif user_roll < bot_roll:
        update_balance(ctx.author.id, -bet)
        result = "💔 LOSS! 💔"
        color = 0xff0000
    else:
        result = "🤝 TIE! 🤝"
        color = 0xffa500
    
    embed = discord.Embed(
        title="🎲 DICE DUEL 🎲",
        description=f"**Your roll:** {dice_emojis[user_roll]} **{user_roll}**\n**Bot's roll:** {dice_emojis[bot_roll]} **{bot_roll}**\n\n**Result:** {result}",
        color=color
    )
    await ctx.send(embed=embed)

@bot.command()
async def rps(ctx, choice: str, bet: int):
    if get_balance(ctx.author.id) < bet:
        embed = discord.Embed(title="❌ Insufficient Petals!", description=f"You need {bet} petals to play!", color=0xff0000)
        return await ctx.send(embed=embed)
    
    valid_choices = ["rock", "paper", "scissors"]
    user_choice = choice.lower()
    
    if user_choice not in valid_choices:
        embed = discord.Embed(title="❌ Invalid Choice!", description="Choose: `rock`, `paper`, or `scissors`", color=0xff0000)
        return await ctx.send(embed=embed)
    
    bot_choice = random.choice(valid_choices)
    
    choice_emojis = {
        "rock": "🪨",
        "paper": "📄",
        "scissors": "✂️"
    }
    
    if user_choice == bot_choice:
        result = "🤝 TIE! 🤝"
        color = 0xffa500
    elif (user_choice == "rock" and bot_choice == "scissors") or \
         (user_choice == "paper" and bot_choice == "rock") or \
         (user_choice == "scissors" and bot_choice == "paper"):
        update_balance(ctx.author.id, bet)
        result = "🎉 WIN! 🎉"
        color = 0x00ff00
    else:
        update_balance(ctx.author.id, -bet)
        result = "💔 LOSS! 💔"
        color = 0xff0000
    
    embed = discord.Embed(
        title="✂️ ROCK PAPER SCISSORS 📄",
        description=f"**You:** {choice_emojis[user_choice]} {user_choice}\n**Bot:** {choice_emojis[bot_choice]} {bot_choice}\n\n**Result:** {result}",
        color=color
    )
    await ctx.send(embed=embed)

@bot.command()
async def redeem(ctx):
    embed = discord.Embed(
        title="🎟️ Redeem Voucher 🎟️",
        description="Click the button below to redeem a voucher code and receive free petals!",
        color=0xff69b4
    )
    embed.set_footer(text="Enter your code in the popup window")
    await ctx.send(embed=embed, view=RedeemStarterView())

@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="🌸 Blossom Garden - Help Menu 🌸",
        description="Welcome to the Blossom Garden bot! Here's everything you can do:",
        color=0xffb7c5
    )
    
    embed.add_field(
        name="🌱 **Earning Petals**",
        value="`beg` - Beg for petals (10-50)\n`farm` - Harvest crops (200-450)\n`hunt` - Go hunting (100-300)\n`bal` - Check your balance\n`lb` - View leaderboard\n`redeem` - Redeem vouchers",
        inline=False
    )
    
    embed.add_field(
        name="🎲 **Casino Games**",
        value="`crash [bet]` - Cash out before plane crashes\n`mines [bet]` - Avoid hidden bombs\n`color [bet]` - Predict colors\n`blackjack [bet]` - Play Blackjack\n`dice [bet]` - Roll against bot\n`rps [choice] [bet]` - Rock Paper Scissors",
        inline=False
    )
    
    embed.add_field(
        name="🎟️ **Admin Commands**",
        value="`gen [code] [value] [uses]` - Generate vouchers\n`setup` - Set leaderboard channel",
        inline=False
    )
    
    embed.set_footer(text="🌸 Keep growing your garden! 🌸")
    await ctx.send(embed=embed)

# --- ADMIN CHECK COMMAND (Optional) ---
@bot.command()
@commands.is_owner()
async def add_admin(ctx, username: str):
    """Add a new admin (bot owner only)"""
    if username not in ADMINS:
        ADMINS.append(username)
        embed = discord.Embed(
            title="✅ Admin Added!",
            description=f"{username} has been added as an admin!",
            color=0x00ff00
        )
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(
            title="ℹ️ Already Admin",
            description=f"{username} is already in the admin list!",
            color=0xffa500
        )
        await ctx.send(embed=embed)

@bot.command()
@commands.is_owner()
async def remove_admin(ctx, username: str):
    """Remove an admin (bot owner only)"""
    if username in ADMINS:
        ADMINS.remove(username)
        embed = discord.Embed(
            title="✅ Admin Removed!",
            description=f"{username} has been removed from admins!",
            color=0x00ff00
        )
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(
            title="❌ Not Found",
            description=f"{username} is not in the admin list!",
            color=0xff0000
        )
        await ctx.send(embed=embed)

@bot.command()
async def admins(ctx):
    """List all bot admins"""
    embed = discord.Embed(
        title="👑 Bot Administrators 👑",
        description=f"**Admins:** {', '.join(ADMINS)}",
        color=0xffb7c5
    )
    await ctx.send(embed=embed)

keep_alive()
bot.run(TOKEN)
