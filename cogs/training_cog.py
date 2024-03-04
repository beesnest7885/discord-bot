import nextcord
from nextcord.ext import commands
import random
import asyncio
import datetime

def save_training_channel_id(channel_id):
    with open("training_channel.txt", "w") as file:
        file.write(str(channel_id))

def load_training_channel_id():
    try:
        with open("training_channel.txt", "r") as file:
            return int(file.read().strip())
    except FileNotFoundError:
        return None

class TrainingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.training_channel_id = None
        self.cooldown_users = {}
        self.training_texts = {
            "Jump over the obstacle!": "⬆️",
            "Dodge left!": "⬅️",
            "Dodge right!": "➡️",
            "Duck!": "⬇️"
        }
        

    @commands.command(name='set_training_channel')
    @commands.has_permissions(administrator=True)
    async def set_training_channel(self, ctx, channel: commands.TextChannelConverter()):
        self.training_channel_id = channel.id
        save_training_channel_id(channel.id)  # Save the channel ID
        print(f"Training channel ID set to: {self.training_channel_id}")  # Debug print
        await ctx.send(f"Training channel has been set to {channel.mention}")

    @commands.command()
    async def training(self, ctx):
        if ctx.channel.id != self.training_channel_id:
            print(f"Context channel ID: {ctx.channel.id}, Stored training channel ID: {self.training_channel_id}")  # Debug print
            await ctx.send("This is not the training channel!")
            return

        user_id = ctx.author.id
        cooldown_end = self.cooldown_users.get(user_id, datetime.datetime.utcnow() - datetime.timedelta(hours=1))
        if datetime.datetime.utcnow() < cooldown_end:
            await ctx.send("You are on cooldown!")
            return

        xp_cog = self.bot.get_cog("XPCog")
        level = 1
        while level <= 10:
            text, emoji = random.choice(list(self.training_texts.items()))
            embed = nextcord.Embed(title="Training Session", description=text, color=0x00ff00)
            message = await ctx.send(embed=embed)
            for reaction_emoji in self.training_texts.values():
                await message.add_reaction(reaction_emoji)

            def check(reaction, user):
                return user == ctx.author and str(reaction.emoji) == emoji

            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=5.0, check=check)
            except asyncio.TimeoutError:
                await ctx.send(f"You failed at level {level}! Better luck next time.")
                if level == 10:
                    self.cooldown_users[user_id] = datetime.datetime.utcnow() + datetime.timedelta(minutes=10)
                return
            else:
                if xp_cog:
                    xp_cog.add_xp(user_id, level * 2)
                level += 1
                await ctx.send(f"Well done! You completed level {level-1} and gained {(level-1)*5} XP!")

        # ... your existing code ...

        # Award extra rewards for completing level 10
        if level == 11:
            if xp_cog:
                xp_cog.add_xp(user_id, 50)  # Adding XP
                
            # Assuming you have a method in ProfileCog to handle tokens
            profile_cog = self.bot.get_cog("ProfileCog")
            if profile_cog:
                profile_cog.add_tokens(user_id, 1000)  # Adding tokens
                profile_cog.add_item(user_id, "mystery_box")

            await ctx.send("Congratulations! You completed all levels and gained an extra 1000 sandwich tokens!")
            self.cooldown_users[user_id] = datetime.datetime.now() + datetime.timedelta(hours=1)

def setup(client):
    client.add_cog(TrainingCog(client))
