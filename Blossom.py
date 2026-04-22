import discord
from discord.ext import commands, tasks
from discord.ui import Button, View, Modal, TextInput
import random
import asyncio
import os
from dotenv import load_dotenv
from keep_alive import keep_alive
import math

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
slot_machines = {}  # For slot machine jackpot

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

# --- UI: CRASH GAME (Harder Difficulty) ---
class CrashView(View):
    def __init__(self, ctx, bet):
        super().__init__(timeout=120.0)
        self.ctx, self.bet, self.multiplier = ctx, bet, 1.0
        self.cashed_out, self.crashed = False, False
        crash_type = random.choice(["early", "early", "normal", "normal", "late"])
        if crash_type == "early":
            self.crash_at = round(random.uniform(1.05, 1.8), 2)
        elif crash_type == "normal":
            self.crash_at = round(random.uniform(1.5, 3.5), 2)
        else:
            self.crash_at = round(random.uniform(2.5, 5.0), 2)
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
            await asyncio.sleep(1.2)
            if self.cashed_out: 
                break
            
            self.ticks += 1
            growth = random.uniform(0.05, 0.6)
            self.multiplier += growth
            emoji_index = (emoji_index + 1) % len(flight_emoji)
            
            if random.random() < 0.05 and self.multiplier > 1.2:
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
            
            risk_percentage = min(95, int((self.multiplier / 3.5) * 100))
            
            embed = discord.Embed(
                title=f"{flight_emoji[emoji_index]} FLIGHT STATUS",
                description=f"**Current Multiplier:** {self.multiplier:.2f}x\n\n*⚠️ The higher you go, the riskier it gets!*",
                color=0xffa500
            )
            embed.add_field(name="💰 Current Payout", value=f"{int(self.bet * self.multiplier)} petals", inline=True)
            embed.add_field(name="⚠️ Crash Risk", value=f"{risk_percentage}%", inline=True)
            await msg.edit(embed=embed, view=self)

# --- UI: MINES GAME ---
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
            
            mult = round(1.25 ** view.revealed, 2)
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
        self.ctx, self.bet, self.bombs, self.revealed = ctx, bet, bombs, 0
        for i in range(1, 10):
            self.add_item(MinesButton(i))

# --- UI: COLOR GAME ---
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
            win = view.bet * (hits + 1)
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

# --- NEW GAME 1: SLOT MACHINE ---
class SlotMachineView(View):
    def __init__(self, ctx, bet):
        super().__init__(timeout=30.0)
        self.ctx, self.bet = ctx, bet
    
    @discord.ui.button(label="🎰 SPIN", style=discord.ButtonStyle.primary, emoji="🎰", row=0)
    async def spin(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            return
        
        symbols = ["🍒", "🍊", "🍋", "🍉", "⭐", "💎", "7️⃣", "🌸"]
        reels = [random.choice(symbols) for _ in range(3)]
        
        # Payout logic
        if reels[0] == reels[1] == reels[2]:
            if reels[0] == "7️⃣":
                win = self.bet * 10
            elif reels[0] == "💎":
                win = self.bet * 8
            elif reels[0] == "⭐":
                win = self.bet * 5
            elif reels[0] == "🌸":
                win = self.bet * 4
            else:
                win = self.bet * 3
            update_balance(self.ctx.author.id, win - self.bet)
            result = f"🎉 **JACKPOT!** Won {win} petals!"
            color = 0x00ff00
        elif reels[0] == reels[1] or reels[1] == reels[2] or reels[0] == reels[2]:
            win = self.bet * 2
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

# --- NEW GAME 2: COINFLIP ---
class CoinflipView(View):
    def __init__(self, ctx, bet):
        super().__init__(timeout=30.0)
        self.ctx, self.bet = bet, ctx
    
    @discord.ui.button(label="🪙 HEADS", style=discord.ButtonStyle.primary, emoji="🪙", row=0)
    async def heads(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.flip(interaction, "heads")
    
    @discord.ui.button(label="🪙 TAILS", style=discord.ButtonStyle.primary, emoji="🪙", row=0)
    async def tails(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.flip(interaction, "tails")
    
    async def flip(self, interaction: discord.Interaction, choice):
        if interaction.user != self.ctx.author:
            return
        
        result = random.choice(["heads", "tails"])
        if choice == result:
            update_balance(self.ctx.author.id, self.bet)
            win = True
        else:
            update_balance(self.ctx.author.id, -self.bet)
            win = False
        
        embed = discord.Embed(
            title="🪙 COINFLIP 🪙",
            description=f"**Your choice:** {choice.upper()}\n**Result:** {result.upper()}\n\n{'🎉 **YOU WIN!** +' + str(self.bet) + ' petals!' if win else '💔 **YOU LOSE!** -' + str(self.bet) + ' petals!'}",
            color=0x00ff00 if win else 0xff0000
        )
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()

# --- NEW GAME 3: HIGHER OR LOWER ---
class HigherLowerView(View):
    def __init__(self, ctx, bet):
        super().__init__(timeout=30.0)
        self.ctx, self.bet = bet, ctx
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
        if interaction.user != self.ctx.author or not self.game_active:
            return
        
        next_card = random.randint(1, 13)
        card_names = {1:"A", 11:"J", 12:"Q", 13:"K"}
        next_display = card_names.get(next_card, str(next_card))
        
        if (choice == "higher" and next_card > self.current_card) or (choice == "lower" and next_card < self.current_card):
            win = self.bet * 2
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

# --- NEW GAME 4: ROULETTE ---
class RouletteView(View):
    def __init__(self, ctx, bet):
        super().__init__(timeout=60.0)
        self.ctx, self.bet = ctx, bet
    
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
            return
        
        number = random.randint(0, 36)
        if number == 0:
            result = "green"
            multiplier = 14
        elif number in [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]:
            result = "red"
            multiplier = 2
        else:
            result = "black"
            multiplier = 2
        
        if choice == result:
            win = self.bet * multiplier
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

# --- NEW GAME 5: TOWER CLIMB ---
class TowerView(View):
    def __init__(self, ctx, bet):
        super().__init__(timeout=60.0)
        self.ctx, self.bet, self.floor = ctx, bet, 1
        self.multiplier = 1.0
        self.update_display()
    
    def update_display(self):
        self.multiplier = round(1.2 ** self.floor, 2)
    
    @discord.ui.button(label="⬆️ CLIMB", style=discord.ButtonStyle.success, emoji="⬆️", row=0)
    async def climb(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            return
        
        if random.random() < 0.25:  # 25% chance to fall
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

# --- NEW GAME 6: SCRATCH CARD ---
class ScratchView(View):
    def __init__(self, ctx, bet):
        super().__init__(timeout=30.0)
        self.ctx, self.bet = ctx, bet
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
        if interaction.user != self.ctx.author or self.revealed[index]:
            return
        
        self.revealed[index] = True
        button.label = str(self.values[index])
        button.disabled = True
        
        if all(self.revealed):
            if self.values[0] == self.values[1] == self.values[2]:
                win = self.bet * 5
                update_balance(self.ctx.author.id, win - self.bet)
                embed = discord.Embed(
                    title="🎫 SCRATCH CARD 🎫",
                    description=f"**{self.values[0]} | {self.values[1]} | {self.values[2]}**\n\n🎉 **JACKPOT!** Won {win} petals!",
                    color=0x00ff00
                )
            elif self.values[0] == self.values[1] or self.values[1] == self.values[2] or self.values[0] == self.values[2]:
                win = self.bet * 2
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

# --- NEW GAME 7: DICE DUEL (Enhanced) ---
class DiceDuelView(View):
    def __init__(self, ctx, bet):
        super().__init__(timeout=30.0)
        self.ctx, self.bet = ctx, bet
    
    @discord.ui.button(label="🎲 ROLL DICE", style=discord.ButtonStyle.primary, emoji="🎲", row=0)
    async def roll(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            return
        
        player_roll = random.randint(1, 6)
        bot_roll = random.randint(1, 6)
        
        dice_art = {
            1: "⚀", 2: "⚁", 3: "⚂",
            4: "⚃", 5: "⚄", 6: "⚅"
        }
        
        if player_roll > bot_roll:
            win = self.bet * 2
            update_balance(self.ctx.author.id, win - self.bet)
            result = f"🎉 **YOU WIN!** +{win} petals!"
            color = 0x00ff00
        elif player_roll < bot_roll:
            update_balance(self.ctx.author.id, -self.bet)
            result = f"💔 **YOU LOSE!** -{self.bet} petals!"
            color = 0xff0000
        else:
            result = "🤝 **TIE!** Bet returned!"
            color = 0xffa500
        
        embed = discord.Embed(
            title="🎲 DICE DUEL 🎲",
            description=f"**Your roll:** {dice_art[player_roll]} {player_roll}\n**Bot's roll:** {dice_art[bot_roll]} {bot_roll}\n\n{result}",
            color=color
        )
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()

# --- NEW GAME 8: TREASURE HUNT ---
class TreasureHuntView(View):
    def __init__(self, ctx, bet):
        super().__init__(timeout=30.0)
        self.ctx, self.bet = ctx, bet
        self.treasure_position = random.randint(1, 5)
        self.attempts = 0
    
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
    
    async def hunt(self, interaction: discord.Interaction, spot, button):
        if interaction.user != self.ctx.author or self.attempts >= 2:
            return
        
        self.attempts += 1
        if spot == self.treasure_position:
            win = self.bet * 3
            update_balance(self.ctx.author.id, win - self.bet)
            embed = discord.Embed(
                title="💎 TREASURE HUNT 💎",
                description=f"You found the treasure at spot **{spot}**!\n🎉 Won **{win} petals**!",
                color=0x00ff00
            )
            await interaction.response.edit_message(embed=embed, view=None)
            self.stop()
        elif self.attempts >= 2:
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
            await interaction.response.edit_message(content=f"Nothing at spot {spot}! Try again! (1 attempt remaining)", view=self)

# --- NEW GAME 9: RUSSIAN ROULETTE ---
class RussianRouletteView(View):
    def __init__(self, ctx, bet):
        super().__init__(timeout=30.0)
        self.ctx, self.bet = ctx, bet
        self.bullet_position = random.randint(1, 6)
        self.chamber = 1
    
    @discord.ui.button(label="🔫 PULL TRIGGER", style=discord.ButtonStyle.danger, emoji="🔫", row=0)
    async def pull(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            return
        
        if self.chamber == self.bullet_position:
            update_balance(self.ctx.author.id, -self.bet)
            embed = discord.Embed(
                title="🔫 RUSSIAN ROULETTE 🔫",
                description=f"**BANG!** The chamber was loaded!\n💔 You lost **{self.bet} petals**!",
                color=0xff0000
            )
            await interaction.response.edit_message(embed=embed, view=None)
            self.stop()
        else:
            win = self.bet * 2
            update_balance(self.ctx.author.id, win - self.bet)
            embed = discord.Embed(
                title="🔫 RUSSIAN ROULETTE 🔫",
                description=f"**Click!** The chamber was empty!\n🎉 You survived and won **{win} petals**!",
                color=0x00ff00
            )
            await interaction.response.edit_message(embed=embed, view=None)
            self.stop()

# --- NEW GAME 10: RACE BETTING ---
class RaceView(View):
    def __init__(self, ctx, bet):
        super().__init__(timeout=30.0)
        self.ctx, self.bet = ctx, bet
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
            return
        
        winner = random.randint(0, 4)
        if choice == winner:
            win = self.bet * 4
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

# --- NEW GAME 11: POKER (Simple Version) ---
class PokerView(View):
    def __init__(self, ctx, bet):
        super().__init__(timeout=30.0)
        self.ctx, self.bet = ctx, bet
    
    @discord.ui.button(label="🃏 DEAL CARDS", style=discord.ButtonStyle.primary, emoji="🃏", row=0)
    async def deal(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
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
            win = self.bet * 2
            update_balance(self.ctx.author.id, win - self.bet)
            result = f"🎉 **YOU WIN!** +{win} petals!"
            color = 0x00ff00
        elif player_score < bot_score:
            update_balance(self.ctx.author.id, -self.bet)
            result = f"💔 **YOU LOSE!** -{self.bet} petals!"
            color = 0xff0000
        else:
            result = "🤝 **TIE!** Bet returned!"
            color = 0xffa500
        
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

# --- DAILY / WEEKLY / HOURLY REWARDS ---
@bot.command()
async def daily(ctx):
    user_id = ctx.author.id
    now = asyncio.get_event_loop().time()
    
    if user_id in daily_cooldown:
        remaining = 86400 - (now - daily_cooldown[user_id])
        if remaining > 0:
            hours = int(remaining // 3600)
            minutes = int((remaining % 3600) // 60)
            return await ctx.send(f"⏰ You already claimed your daily reward! Come back in {hours}h {minutes}m!")
    
    reward = random.randint(50, 100)
    update_balance(user_id, reward)
    daily_cooldown[user_id] = now
    
    embed = discord.Embed(
        title="📅 DAILY REWARD!",
        description=f"{ctx.author.mention} received **{reward} petals**!",
        color=0x00ff00
    )
    embed.set_footer(text="Come back tomorrow for more!")
    await ctx.send(embed=embed)

@bot.command()
async def weekly(ctx):
    user_id = ctx.author.id
    now = asyncio.get_event_loop().time()
    
    if user_id in weekly_cooldown:
        remaining = 604800 - (now - weekly_cooldown[user_id])
        if remaining > 0:
            days = int(remaining // 86400)
            hours = int((remaining % 86400) // 3600)
            return await ctx.send(f"⏰ You already claimed your weekly reward! Come back in {days}d {hours}h!")
    
    reward = random.randint(200, 1000)
    update_balance(user_id, reward)
    weekly_cooldown[user_id] = now
    
    embed = discord.Embed(
        title="📅 WEEKLY REWARD!",
        description=f"{ctx.author.mention} received **{reward} petals**!",
        color=0x00ff00
    )
    embed.set_footer(text="Come back next week for more!")
    await ctx.send(embed=embed)

@bot.command()
async def hourly(ctx):
    user_id = ctx.author.id
    now = asyncio.get_event_loop().time()
    
    if user_id in hourly_cooldown:
        remaining = 3600 - (now - hourly_cooldown[user_id])
        if remaining > 0:
            minutes = int(remaining // 60)
            return await ctx.send(f"⏰ You already claimed your hourly reward! Come back in {minutes}m!")
    
    reward = random.randint(0, 30)
    update_balance(user_id, reward)
    hourly_cooldown[user_id] = now
    
    embed = discord.Embed(
        title="⏰ HOURLY REWARD!",
        description=f"{ctx.author.mention} received **{reward} petals**!",
        color=0x00ff00
    )
    await ctx.send(embed=embed)

# --- ADMIN COMMANDS ---
@bot.command()
async def gen(ctx, code: str, value: int, uses: int):
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

@bot.command()
async def give(ctx, member: discord.Member, amount: int):
    if ctx.author.name not in ADMINS:
        embed = discord.Embed(title="❌ Permission Denied", description="Only admins can use this!", color=0xff0000)
        return await ctx.send(embed=embed)
    
    update_balance(member.id, amount)
    embed = discord.Embed(
        title="✅ Petals Given!",
        description=f"Gave **{amount} petals** to {member.mention}",
        color=0x00ff00
    )
    await ctx.send(embed=embed)

# --- USER COMMANDS ---
@bot.command()
async def lb(ctx):
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

# --- ALL GAME COMMANDS ---
@bot.command()
async def crash(ctx, bet: int):
    if get_balance(ctx.author.id) < bet or bet <= 0:
        return await ctx.send("❌ Not enough petals!")
    
    embed = discord.Embed(
        title="✈️ CRASH GAME - HIGH RISK MODE ✈️",
        description=f"**Bet:** {bet} petals\n**⚠️ EXTREME RISK WARNING!** Planes crash EARLY!\n\n*Can you beat the odds?*",
        color=0xff0000
    )
    msg = await ctx.send(embed=embed)
    v = CrashView(ctx, bet)
    await v.start_flight(msg)

@bot.command()
async def mines(ctx, bet: int):
    if get_balance(ctx.author.id) < bet or bet <= 0:
        return await ctx.send("❌ Not enough petals!")
    
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
        return await ctx.send("❌ Not enough petals!")
    
    embed = discord.Embed(
        title="🎨 COLOR PREDICTOR 🎨",
        description=f"**Bet:** {bet} petals\nPick a color and see how many times it appears!",
        color=0xff69b4
    )
    await ctx.send(embed=embed, view=ColorView(ctx, bet))

@bot.command()
async def blackjack(ctx, bet: int):
    if get_balance(ctx.author.id) < bet or bet <= 0:
        return await ctx.send("❌ Not enough petals!")
    
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
        return await ctx.send("❌ Not enough petals!")
    
    embed = discord.Embed(
        title="🎲 DICE DUEL 🎲",
        description=f"**Bet:** {bet} petals\nClick the button to roll!",
        color=0xffa500
    )
    await ctx.send(embed=embed, view=DiceDuelView(ctx, bet))

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
async def slots(ctx, bet: int):
    if get_balance(ctx.author.id) < bet or bet <= 0:
        return await ctx.send("❌ Not enough petals!")
    
    embed = discord.Embed(
        title="🎰 SLOT MACHINE 🎰",
        description=f"**Bet:** {bet} petals\nClick SPIN to try your luck!",
        color=0xffa500
    )
    await ctx.send(embed=embed, view=SlotMachineView(ctx, bet))

@bot.command()
async def coinflip(ctx, bet: int):
    if get_balance(ctx.author.id) < bet or bet <= 0:
        return await ctx.send("❌ Not enough petals!")
    
    embed = discord.Embed(
        title="🪙 COINFLIP 🪙",
        description=f"**Bet:** {bet} petals\nChoose Heads or Tails!",
        color=0xffa500
    )
    await ctx.send(embed=embed, view=CoinflipView(ctx, bet))

@bot.command()
async def higherlower(ctx, bet: int):
    if get_balance(ctx.author.id) < bet or bet <= 0:
        return await ctx.send("❌ Not enough petals!")
    
    embed = discord.Embed(
        title="🎴 HIGHER OR LOWER 🎴",
        description=f"**Bet:** {bet} petals\nWill the next card be higher or lower?",
        color=0xffa500
    )
    await ctx.send(embed=embed, view=HigherLowerView(ctx, bet))

@bot.command()
async def roulette(ctx, bet: int):
    if get_balance(ctx.author.id) < bet or bet <= 0:
        return await ctx.send("❌ Not enough petals!")
    
    embed = discord.Embed(
        title="🎡 ROULETTE 🎡",
        description=f"**Bet:** {bet} petals\nBet on Red, Black, or Green!",
        color=0xffa500
    )
    await ctx.send(embed=embed, view=RouletteView(ctx, bet))

@bot.command()
async def tower(ctx, bet: int):
    if get_balance(ctx.author.id) < bet or bet <= 0:
        return await ctx.send("❌ Not enough petals!")
    
    embed = discord.Embed(
        title="🏰 TOWER CLIMB 🏰",
        description=f"**Bet:** {bet} petals\nClimb the tower and cash out before you fall!",
        color=0xffa500
    )
    await ctx.send(embed=embed, view=TowerView(ctx, bet))

@bot.command()
async def scratch(ctx, bet: int):
    if get_balance(ctx.author.id) < bet or bet <= 0:
        return await ctx.send("❌ Not enough petals!")
    
    embed = discord.Embed(
        title="🎫 SCRATCH CARD 🎫",
        description=f"**Bet:** {bet} petals\nScratch all three cards to reveal your prize!",
        color=0xffa500
    )
    await ctx.send(embed=embed, view=ScratchView(ctx, bet))

@bot.command()
async def treasure(ctx, bet: int):
    if get_balance(ctx.author.id) < bet or bet <= 0:
        return await ctx.send("❌ Not enough petals!")
    
    embed = discord.Embed(
        title="💎 TREASURE HUNT 💎",
        description=f"**Bet:** {bet} petals\nFind the treasure in 2 attempts!",
        color=0xffa500
    )
    await ctx.send(embed=embed, view=TreasureHuntView(ctx, bet))

@bot.command()
async def roulettegun(ctx, bet: int):
    if get_balance(ctx.author.id) < bet or bet <= 0:
        return await ctx.send("❌ Not enough petals!")
    
    embed = discord.Embed(
        title="🔫 RUSSIAN ROULETTE 🔫",
        description=f"**Bet:** {bet} petals\nPull the trigger and test your luck!",
        color=0xff0000
    )
    await ctx.send(embed=embed, view=RussianRouletteView(ctx, bet))

@bot.command()
async def race(ctx, bet: int):
    if get_balance(ctx.author.id) < bet or bet <= 0:
        return await ctx.send("❌ Not enough petals!")
    
    embed = discord.Embed(
        title="🏇 HORSE RACING 🏇",
        description=f"**Bet:** {bet} petals\nPick a horse and watch it race!",
        color=0xffa500
    )
    await ctx.send(embed=embed, view=RaceView(ctx, bet))

@bot.command()
async def poker(ctx, bet: int):
    if get_balance(ctx.author.id) < bet or bet <= 0:
        return await ctx.send("❌ Not enough petals!")
    
    embed = discord.Embed(
        title="🃏 POKER SHOWDOWN 🃏",
        description=f"**Bet:** {bet} petals\nFace off against the bot in 5-card poker!",
        color=0xffa500
    )
    await ctx.send(embed=embed, view=PokerView(ctx, bet))

@bot.command()
async def redeem(ctx):
    embed = discord.Embed(
        title="🎟️ Redeem Voucher 🎟️",
        description="Click the button below to redeem a voucher code and receive free petals!",
        color=0xff69b4
    )
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
        value="`beg`, `farm`, `hunt`, `daily`, `weekly`, `hourly`, `bal`, `lb`, `redeem`",
        inline=False
    )
    
    embed.add_field(
        name="🎲 **Casino Games**",
        value="`crash`, `mines`, `color`, `blackjack`, `dice`, `rps`, `slots`, `coinflip`, `higherlower`, `roulette`, `tower`, `scratch`, `treasure`, `roulettegun`, `race`, `poker`",
        inline=False
    )
    
    embed.add_field(
        name="🎟️ **Admin Commands**",
        value="`gen [code] [value] [uses]`, `setup`, `give [@user] [amount]`",
        inline=False
    )
    
    embed.set_footer(text="🌸 16+ Exciting Games! Type any command to play! 🌸")
    await ctx.send(embed=embed)

# --- ADMIN CHECK COMMANDS ---
@bot.command()
@commands.is_owner()
async def add_admin(ctx, username: str):
    if username not in ADMINS:
        ADMINS.append(username)
        embed = discord.Embed(title="✅ Admin Added!", description=f"{username} has been added as an admin!", color=0x00ff00)
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(title="ℹ️ Already Admin", description=f"{username} is already in the admin list!", color=0xffa500)
        await ctx.send(embed=embed)

@bot.command()
@commands.is_owner()
async def remove_admin(ctx, username: str):
    if username in ADMINS:
        ADMINS.remove(username)
        embed = discord.Embed(title="✅ Admin Removed!", description=f"{username} has been removed from admins!", color=0x00ff00)
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(title="❌ Not Found", description=f"{username} is not in the admin list!", color=0xff0000)
        await ctx.send(embed=embed)

@bot.command()
async def admins(ctx):
    embed = discord.Embed(title="👑 Bot Administrators 👑", description=f"**Admins:** {', '.join(ADMINS)}", color=0xffb7c5)
    await ctx.send(embed=embed)

keep_alive()
bot.run(TOKEN)
