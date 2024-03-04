import nextcord as discord
from nextcord.ext import commands
from nextcord.ui import Button, View
import json
import random

class LootboxCog(commands.Cog):
    def __init__(self, client):
        self.client = client
        
    def load_lootbox_list(self):
        with open('lootbox_list.json', 'r') as f:
            return json.load(f)


    @commands.command()
    async def lootbox(self, ctx):
        """Shows the number of lootboxes a user has and provides buttons to open them."""
        profile_cog = self.client.get_cog("ProfileCog")
        lootboxes = self.load_lootbox_list()

        user_data = profile_cog.get_user_data(ctx.author.id)
        user_inventory = user_data['inventory']

        # Count the total number of lootboxes (not just types)
        lootbox_count = sum(user_inventory.count(box["name"]) for box in lootboxes)

        if lootbox_count == 0:
            await ctx.send("You don't have any lootboxes.")
            return

        # Prepare the embed message
        embed = discord.Embed(title="Your Lootboxes", color=0x00ff00)
        embed.add_field(name="Boxes Count", value=lootbox_count, inline=False)


        # Buttons
        open_one_button = Button(label="Open One", style=discord.ButtonStyle.green)
        open_all_button = Button(label="Open All", style=discord.ButtonStyle.red)

        async def open_one_callback(interaction):
            user_id = interaction.user.id
            user_lootboxes = [box for box in lootboxes if profile_cog.has_item(user_id, box["name"])]

            if not user_lootboxes:
                no_box_embed = discord.Embed(title="No Lootboxes", description="You don't have any lootboxes to open.", color=discord.Color.red())
                await interaction.response.send_message(embed=no_box_embed, ephemeral=True)
                return

            # Randomly select one lootbox to open
            selected_box = random.choice(user_lootboxes)

            # Logic to open the selected lootbox and give rewards
            tokens = random.randint(selected_box["tokens"]["min"], selected_box["tokens"]["max"])
            profile_cog.update_profile(user_id, tokens=tokens)

            # Select items from the lootbox
            if selected_box["name"] == "mystery_box":
                won_items = random.sample(selected_box["items"], 6)
            else:
                won_items = random.sample(selected_box["items"], 4)

            for item in won_items:
                profile_cog.update_profile(user_id, item=item)

            # Remove one instance of the lootbox from user inventory
            profile_cog.remove_item_from_inventory(user_id, selected_box["name"], tokens_to_add=0)

            # Create embed for response
            open_box_embed = discord.Embed(title=f"Lootbox Opened: {selected_box['name']}", color=discord.Color.green())
            open_box_embed.add_field(name="Tokens Won", value=str(tokens), inline=False)

            # Organize won items in a grid-like format (2 columns)
            for i in range(0, len(won_items), 2):
                items_row = ', '.join(won_items[i:i + 2])
                open_box_embed.add_field(name="\u200B", value=items_row, inline=True)

            await interaction.response.send_message(embed=open_box_embed, ephemeral=True)

        async def open_all_callback(interaction):
            user_id = interaction.user.id
            user_lootboxes = [box for box in lootboxes if profile_cog.has_item(user_id, box["name"])]

            if not user_lootboxes:
                no_box_embed = discord.Embed(title="No Lootboxes", description="You don't have any lootboxes to open.", color=discord.Color.red())
                await interaction.response.send_message(embed=no_box_embed, ephemeral=True)
                return

            total_tokens = 0
            total_items = []

            for box in user_lootboxes:
                user_data = profile_cog.get_user_data(user_id)
                lootbox_count = user_data['inventory'].count(box["name"])

                for _ in range(lootbox_count):
                    tokens = random.randint(box["tokens"]["min"], box["tokens"]["max"])
                    total_tokens += tokens
                    profile_cog.update_profile(user_id, tokens=tokens)

                    if box["name"] == "mystery_box":
                        won_items = random.sample(box["items"], 6)
                    else:
                        won_items = random.sample(box["items"], 4)

                    total_items.extend(won_items)
                    for item in won_items:
                        profile_cog.update_profile(user_id, item=item)

                    profile_cog.remove_item_from_inventory(user_id, box["name"], tokens_to_add=0)

            # Create embed for response
            open_all_embed = discord.Embed(title="Lootboxes Opened", color=discord.Color.green())
            open_all_embed.add_field(name="Total Tokens Won", value=str(total_tokens), inline=False)

            # Limit the number of items displayed to avoid exceeding embed limits
            displayed_items = total_items[:20]  # Adjust the number as needed
            if len(total_items) > len(displayed_items):
                more_items_count = len(total_items) - len(displayed_items)
                displayed_items.append(f"...and {more_items_count} more items")

            # Organize won items in a grid-like format
            for i in range(0, len(displayed_items), 2):
                items_row = ', '.join(displayed_items[i:i + 2])
                open_all_embed.add_field(name="\u200B", value=items_row, inline=True)

            await interaction.response.send_message(embed=open_all_embed, ephemeral=True)


        open_one_button.callback = open_one_callback
        open_all_button.callback = open_all_callback

        view = View()
        view.add_item(open_one_button)
        view.add_item(open_all_button)

        await ctx.send(embed=embed, view=view)

    # ... [rest of your existing code] ...

    @commands.command()
    async def lootbox_list(self, ctx):
        """Displays all available lootboxes."""

        # Load lootbox data from lootbox_list.json
        with open('lootbox_list.json', 'r') as file:
            lootboxes = json.load(file)

        if not lootboxes:
            await ctx.send("There are no available lootboxes.")
            return

        # Prepare the embed message
        embed = discord.Embed(title="Available Lootboxes", color=0x00ff00)
        
        for box_name, box_details in lootboxes.items():
            # Customize this to show whatever details you want about the lootbox
            tokens_range = f"{box_details['tokens']['min']} - {box_details['tokens']['max']}"
            items_list = ', '.join(box_details['items'])
            embed.add_field(name=box_name, value=f"Tokens: {tokens_range}\nItems: {items_list}", inline=False)

        await ctx.send(embed=embed)



def setup(client):
    client.add_cog(LootboxCog(client))
