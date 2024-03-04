import nextcord as discord
from nextcord.ext import commands, tasks
import random

def save_word_channel_id(channel_id):
    with open("word_channel.txt", "w") as file:
        file.write(str(channel_id))

def load_word_channel_id():
    try:
        with open("word_channel.txt", "r") as file:
            return int(file.read().strip())
    except FileNotFoundError:
        return None

class WordCog(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.post_word_channel_id = load_word_channel_id()  # ID of the channel to post the challenge
        self.current_word = None  # Current challenge word
        self.hobo_words = ["word1", "word2", "word3", "..."]  # Fill with your hobo words
        self.challenge_claimed = False  # Add a flag to track if the challenge has been claimed


        # Random responses
        self.gm_responses = ["Good morning!", "Mornin'! 🌞", "Rise and shine!"]
        self.gn_responses = ["Good night!", "Sweet dreams! 🌙", "Nighty night!"]
        self.off_responses = ["No need for that...", "Chill out!", "Hey, let's keep it friendly."]
        self.old_responses = ["Who you calling old?", "Watch your mouth kid", "Your the whippersnapper here"]
        self.word_task.start()  # Start the task when the cog is loaded

    def cog_unload(self):
        self.word_task.cancel()  # Stop the task when the cog is unloaded

    @tasks.loop(minutes=1)
    async def word_task(self):
        if self.post_word_channel_id:
            channel = self.client.get_channel(self.post_word_channel_id)
            if channel:
                self.current_word = random.choice(self.hobo_words)
                embed = discord.Embed(title="Word Challenge", description=f"First one to reply with the word **{self.current_word}** wins!")
                await channel.send(embed=embed)
            self.challenge_claimed = False  # Reset the flag when posting a new challenge


    @word_task.before_loop
    async def before_word_task(self):
        await self.client.wait_until_ready()

    @commands.Cog.listener()
    async def on_message(self, message):
        # Ensure the bot doesn't reply to itself
        if message.author.bot:
            return
        
        if message.content.lower() == "gm":
            await message.channel.send(random.choice(self.gm_responses))
        elif message.content.lower() == "gn":
            await message.channel.send(random.choice(self.gn_responses))
        elif message.content.lower() == "old":
            await message.channel.send(random.choice(self.old_responses))
        elif "fuck off" in message.content.lower():
            await message.channel.send(random.choice(self.off_responses))
        elif (message.channel.id == self.post_word_channel_id and 
            message.content == self.current_word and 
            not self.challenge_claimed):

            self.challenge_claimed = True  # Mark the challenge as claimed
            profile_cog = self.client.get_cog("ProfileCog")
            if profile_cog:
                profile_cog.add_xp(message.author.id, 50)
                profile_cog.add_tokens(message.author.id, 50)
                profile_cog.add_item(message.author.id, "mystery_box")

                await message.channel.send(f"Congratulations {message.author.mention}! You've won the challenge!")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def set_word_channel(self, ctx, channel: discord.TextChannel):
        self.post_word_channel_id = channel.id
        save_word_channel_id(channel.id)  # Save the channel ID
        await ctx.send(f"Word challenge channel set to {channel.mention}")


def setup(client):
    client.add_cog(WordCog(client))
