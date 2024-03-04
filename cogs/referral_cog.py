import nextcord
from nextcord.ext import commands
import json
import os
import random
from nextcord.ext.commands import has_permissions
import asyncio


intents = nextcord.Intents.default()
intents.message_content = True  # Enable message content intent

bot = commands.Bot(command_prefix='.', intents=intents)


class ReferralCodes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.referral_file = 'referrals.json'
        self.referrals = self.load_referrals()

    def load_referrals(self):
        if not os.path.isfile(self.referral_file):
            return {}
        with open(self.referral_file, 'r') as file:
            return json.load(file)

    def save_referrals(self):
        with open(self.referral_file, 'w') as file:
            json.dump(self.referrals, file, indent=4)

    @nextcord.slash_command(name="submit", description="Submit a referral code")
    async def submit(self, interaction: nextcord.Interaction):
        categories = list(self.referrals.keys())
        category_list = ", ".join(categories) if categories else "No categories available. Please speak to mod about adding it."

        # Create and start a thread
        thread = await interaction.channel.create_thread(name=f"Submit Referral Code - {interaction.user.display_name}", type=nextcord.ChannelType.public_thread)
        await thread.send(f"Available categories:\n{category_list}\n\nUse `.add <category>` when you are finished adding codes.")

        # Store the thread ID for later reference
        self.thread_id_to_category = {}
        self.thread_id_to_category[thread.id] = None

    @commands.command()
    async def add(self, ctx, category: str):
        thread_id = ctx.channel.id
        if thread_id not in self.thread_id_to_category:
            await ctx.send("This command can only be used in a submission thread.")
            return

        # Check if the category exists in referrals and has a 'codes' list
        if category not in self.referrals or 'codes' not in self.referrals[category]:
            await ctx.send(f"Category '{category}' does not exist or is not properly set up.")
            return

        # Collect codes from messages in the thread
        async for message in ctx.channel.history(limit=200):
            if message.author == ctx.author and message.content != f".add {category}":
                self.referrals[category]['codes'].append(message.content)

        # Save the codes and close the thread
        self.save_referrals()

        await ctx.send(f"Codes for {category} have been added successfully.")
        
        # Wait for a short delay
        await asyncio.sleep(5)  # Waits for 5 seconds before deleting the thread

        # Then delete the thread
        await ctx.channel.delete()



    # ... [Other parts of your class]

    @nextcord.slash_command(name="redeem_referral_codes", description="Redeem a referral code")
    async def redeem_code(self, interaction: nextcord.Interaction):
        user_id = str(interaction.user.id)  # Convert user ID to string for JSON compatibility
        categories = list(self.referrals.keys())
        if not categories:
            await interaction.response.send_message("No categories available.", ephemeral=True)
            return

        # Create a dropdown menu for categories
        select_menu = nextcord.ui.Select(
            options=[nextcord.SelectOption(label=category) for category in categories],
            placeholder="Choose a category",
            min_values=1,
            max_values=1
        )

        async def select_callback(interaction: nextcord.Interaction):
            category = select_menu.values[0]
            if category not in self.referrals or not self.referrals[category]['codes']:
                await interaction.response.send_message("No codes available for this category.", ephemeral=True)
                return

            # Check if the user has already claimed a code in this category
            if user_id in self.referrals[category].get('claimed_users', []):
                await interaction.response.send_message("You have already claimed a code in this category.", ephemeral=True)
                return

            code = random.choice(self.referrals[category]['codes'])
            self.referrals[category]['codes'].remove(code)

            # Record that the user has claimed a code in this category
            self.referrals[category].setdefault('claimed_users', []).append(user_id)
            self.save_referrals()

            await interaction.response.send_message(f"Your referral code for {category} is: {code}", ephemeral=True)

        select_menu.callback = select_callback
        view = nextcord.ui.View()
        view.add_item(select_menu)
        await interaction.response.send_message("Please select a category:", view=view, ephemeral=True)


    @commands.command(name="add_cat")
    @has_permissions(administrator=True)
    async def add_category(self, ctx, category: str = None):
        if category is None:
            await ctx.send("Please enter the category name:")
            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel
            category_msg = await self.bot.wait_for('message', check=check)
            category = category_msg.content.strip()

        if category in self.referrals:
            await ctx.send(f"Category '{category}' already exists.")
            return

        # Ask for the maximum number of codes a user can claim
        await ctx.send(f"Enter the maximum number of codes a user can claim for {category}:")
        def check_max_claims(m):
            return m.author == ctx.author and m.channel == ctx.channel
        max_claims_msg = await self.bot.wait_for('message', check=check_max_claims)
        
        # Validate and convert the maximum claims input
        try:
            max_claims = int(max_claims_msg.content)
            if max_claims < 1:
                raise ValueError
        except ValueError:
            await ctx.send("Please enter a valid positive integer for the maximum number of claims.")
            return

        # Add the category with the maximum claim limit
        self.referrals[category] = {'codes': [], 'max_claims': max_claims, 'claimed_users': []}
        self.save_referrals()
        await ctx.send(f"Category '{category}' added with a maximum of {max_claims} claims.")


        # Rest of your code...


    

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        if error.param.name == 'category':
            await ctx.send("You must specify a category name. Usage: `.add_cat [category_name]`")
    elif isinstance(error, commands.CommandInvokeError):
        await ctx.send(f"Command error: {error.original}")
    else:
        await ctx.send(f"An error occurred: {error}")
    

def setup(bot):
    bot.add_cog(ReferralCodes(bot))
    
