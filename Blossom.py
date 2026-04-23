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

# --- DATABASE ---
economy = {}
server_channels = {} 
redeem_codes = {} 
daily_cooldown = {}
weekly_cooldown = {}
hourly_cooldown = {}

# --- COOLDOWN DICTIONARIES FOR FARM/BEG/HUNT/WORK ---
beg_cooldown = {}
farm_cooldown = {}
hunt_cooldown = {}
work_cooldown = {}

# --- GIFTING SYSTEM VARIABLES ---
gift_cooldown = {}
DAILY_GIFT_LIMIT = 1000000  # 1,000,000 petals per day

def get_balance(user_id):
    return economy.get(user_id, 0)

def update_balance(user_id, amount):
    economy[user_id] = get_balance(user_id) + amount

def check_cooldown(cooldown_dict, user_id, cooldown_seconds=86400):
    """Check if user is on cooldown, returns (is_on_cooldown, remaining_time)"""
    if user_id in cooldown_dict:
        last_used = cooldown_dict[user_id]
        time_passed = (datetime.now() - last_used).total_seconds()
        if time_passed < cooldown_seconds:
            remaining = cooldown_seconds - time_passed
            return True, remaining
    return False, 0

def set_cooldown(cooldown_dict, user_id):
    """Set cooldown for user"""
    cooldown_dict[user_id] = datetime.now()

def format_time(seconds):
    """Format seconds into readable time"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    
    if hours > 0:
        return f"{hours}h {minutes}m"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"

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

# --- NERFED CRASH GAME (Higher crash chance) ---
class CrashView(View):
    def __init__(self, ctx, bet):
        super().__init__(timeout=120.0)
        self.ctx = ctx
        self.bet = bet
        self.multiplier = 1.0
        self.cashed_out = False
        self.crashed = False
        # More aggressive crash pattern - higher chance of early crash
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

# --- NERFED MINES GAME (More bombs) ---
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

# --- NERFED COLOR GAME (Reduced win multiplier) ---
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

# --- NERFED COINFLIP GAME (Lower win multiplier) ---
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

# --- NERFED HIGHER OR LOWER GAME (Lower win multiplier) ---
class HigherLowerView(View):
    def __init__(self, ctx, bet):
        super().__init__(timeout=30.0)
        self.ctx = ctx
        self.bet = bet
        self.current_card = random.randint(1, 13)
        self.game_active = True
        self.update_display()
    
    def update_display(self):
        card_names = {1:"A", 11:"J", 12:"Q", 13:"K"}
        self.card_display = card_names.get(self.current_card, str(self.current_card))
    
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
        
        if (choice == "higher" and next_card > self.current_card) or (choice == "lower" and next_card < self.current_card):
            win = int(self.bet * 1.8)
            update_balance(self.ctx.author.id, win - self.bet)
            embed = discord.Embed(
                title="🎴 HIGHER OR LOWER 🎴",
                description=f"**Your card:** {self.card_display}\n**Next card:** {next_display}\n\n🎉 **CORRECT!** You won {win} petals!",
                color=0x00ff00
            )
        elif next_card == self.current_card:
            embed = discord.Embed(
                title="🎴 HIGHER OR LOWER 🎴",
                description=f"**Your card:** {self.card_display}\n**Next card:** {next_display}\n\n🤝 **TIE!** Your bet is returned!",
                color=0xffa500
            )
        else:
            update_balance(self.ctx.author.id, -self.bet)
            embed = discord.Embed(
                title="🎴 HIGHER OR LOWER 🎴",
                description=f"**Your card:** {self.card_display}\n**Next card:** {next_display}\n\n💔 **WRONG!** You lost {self.bet} petals!",
                color=0xff0000
            )
        
        self.game_active = False
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()

# --- NERFED SLOT MACHINE GAME (Lower payouts) ---
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

# --- NERFED ROULETTE GAME (Lower payouts) ---
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

# --- NERFED TOWER CLIMB (Higher fall chance) ---
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

# --- NERFED TREASURE HUNT (Lower win multiplier) ---
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

# --- DEADLY RUSSIAN ROULETTE (3 Bullets, 6 Chambers) ---
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

# --- NERFED SCRATCH CARD (Lower payouts) ---
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

# --- NERFED HORSE RACING (Lower win multiplier) ---
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

# --- NERFED POKER (Ties go to house, lower payouts) ---
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

# --- NERFED DICE DUEL (Lower win multiplier) ---
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

# --- DUEL GAME (Player vs Player) ---
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

# --- NERFED BLACKJACK (House edge increased) ---
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

# --- NERFED RPS (Lower win multiplier) ---
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

@bot.event
async def on_ready():
    print(f'🌸 {bot.user} is fully loaded!')
    print(f'📊 Serving {len(bot.guilds)} servers')
    print(f'👑 Admins: {", ".join(ADMINS)}')
    if not hourly_leaderboard.is_running(): 
        hourly_leaderboard.start()

# --- REWARD COMMANDS (NERFED) ---
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
    
    embed = discord.Embed(
        title="⏰ HOURLY REWARD!",
        description=f"{ctx.author.mention} received **{reward} petals**!",
        color=0x00ff00
    )
    await ctx.send(embed=embed)

# --- FARM, BEG, HUNT, WORK COMMANDS WITH NERFED REWARDS ---
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
    """Gift petals to another player! Usage: b!gift @player <amount>"""
    
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
    """Check your daily gifting stats"""
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

@bot.command()
async def reset_gift(ctx, user: discord.Member = None):
    """Reset a user's daily gifting limit (Admin only)"""
    if ctx.author.name not in ADMINS:
        return await ctx.send("❌ You don't have permission to use this command!")
    
    target = user if user else ctx.author
    
    if target.id in gift_cooldown:
        del gift_cooldown[target.id]
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

# --- ADMIN COMMANDS ---
@bot.command()
async def gen(ctx, code: str, value: int, uses: int):
    if ctx.author.name not in ADMINS:
        embed = discord.Embed(title="❌ Permission Denied", description="You don't have permission!", color=0xff0000)
        return await ctx.send(embed=embed)
    
    redeem_codes[code.upper()] = {"value": value, "uses": uses}
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
    
    embed = discord.Embed(
        title="✅ Cooldowns Reset!",
        description=f"Reset all daily command cooldowns for {target.mention}",
        color=0x00ff00
    )
    await ctx.send(embed=embed)

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

# --- USER COMMANDS ---
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

# --- ALL GAME COMMANDS ---
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
    
    embed = discord.Embed(title="🎴 HIGHER OR LOWER", description=f"**Bet:** {bet} petals\nWill the next card be higher or lower?", color=0xffa500)
    await ctx.send(embed=embed, view=HigherLowerView(ctx, bet))

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
async def redeem(ctx):
    embed = discord.Embed(title="🎟️ Redeem Voucher", description="Click below to redeem a voucher!", color=0xff69b4)
    await ctx.send(embed=embed, view=RedeemStarterView())

@bot.command()
async def duel(ctx, opponent: discord.Member, bet: int):
    """Challenge another player to a duel! Usage: b!duel @player <amount>"""
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
async def help(ctx):
    embed = discord.Embed(title="🌸 Blossom Garden - Help Menu", description="Here's everything you can do:", color=0xffb7c5)
    
    embed.add_field(name="🌱 **Daily Earnings**", value="`beg`, `farm`, `hunt`, `work` - Each once per day!\n`daily`, `weekly`, `hourly` - Time-based rewards!", inline=False)
    embed.add_field(name="🎁 **Gifting**", value="`gift @player <amount>` - Gift petals to friends!\n`giftstats` - Check your daily gifting limit\n*(Max 1,000,000 petals per day)*", inline=False)
    embed.add_field(name="⚔️ **PvP Game**", value="`duel @player <amount>` - Challenge other players to a duel!", inline=False)
    embed.add_field(name="🎲 **Casino Games**", value="`crash`, `mines`, `color`, `blackjack`, `dice`, `rps`, `slots`, `coinflip`, `higherlower`, `roulette`, `tower`, `scratch`, `treasure`, `roulettegun`, `race`, `poker`", inline=False)
    embed.add_field(name="ℹ️ **Info**", value="`bal` - Check balance\n`lb` - Leaderboard\n`cooldowns` - Check daily command status", inline=False)
    embed.add_field(name="🎟️ **Admin**", value="`gen`, `setup`, `give`, `reset_cooldowns`, `reset_gift`", inline=False)
    embed.set_footer(text="🌸 All games have been balanced for fair play! Duel your friends for big wins! 🌸")
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

keep_alive()
bot.run(TOKEN)
