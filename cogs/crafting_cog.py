import nextcord as discord
from nextcord.ext import commands
import json
from nextcord.ui import Select, View
from nextcord import SelectOption
from nextcord.ui import Button, View

class CraftingCog(commands.Cog):
    def __init__(self, client):
        self.client = client
        with open('crafting.json', 'r') as f:
            self.recipes = json.load(f)

    class CraftingView(View):
        def __init__(self, craftable_items, ctx, recipes, profile_cog):
            super().__init__(timeout=60)
            self.ctx = ctx
            self.recipes = recipes
            self.profile_cog = profile_cog

            # Dropdown for selecting items
            options = [SelectOption(label=item, value=item) for item in craftable_items]
            self.select = Select(placeholder='Select an item to craft...', options=options)
            self.select.callback = self.on_select
            self.add_item(self.select)

            # Craft button
            self.craft_button = Button(label="Craft", style=discord.ButtonStyle.green, disabled=True)
            self.craft_button.callback = self.craft_item
            self.add_item(self.craft_button)

            # Close button
            self.close_button = Button(label="Close", style=discord.ButtonStyle.red)
            self.close_button.callback = self.close_menu
            self.add_item(self.close_button)

        async def on_select(self, interaction: discord.Interaction):
            # Enable the craft button when an item is selected
            self.craft_button.disabled = False
            await interaction.response.edit_message(view=self)  # Update the message to reflect the change in view



        async def craft_item(self, interaction: discord.Interaction):
            selected_item = self.select.values[0]
            user_id = interaction.user.id
            user_data = self.profile_cog.get_user_data(user_id)

            # Retrieve the recipe for the selected item
            recipe = self.recipes[selected_item]["recipes"][0]  # Assuming the first recipe is used

            # Check if the user has the required items and tokens
            can_craft = True
            for required_item, amount in recipe["cost"].items():
                if user_data["inventory"].count(required_item) < amount:
                    can_craft = False
                    break

            token_cost = recipe.get("token_cost", 0)
            if user_data["tokens"] < token_cost:
                can_craft = False

            if can_craft:
                # Deduct required items and tokens from the user's inventory
                for required_item, amount in recipe["cost"].items():
                    for _ in range(amount):
                        self.profile_cog.remove_item_from_inventory(user_id, required_item)
                self.profile_cog.remove_tokens(user_id, token_cost)

                # Add the crafted item to the user's inventory
                self.profile_cog.add_item(user_id, selected_item)

                # Confirmation message
                confirmation_embed = discord.Embed(title="Crafting Successful", description=f"You successfully crafted {selected_item}.", color=discord.Color.green())
                await interaction.response.send_message(embed=confirmation_embed, ephemeral=True)
            else:
                # Failure message
                error_embed = discord.Embed(title="Crafting Failed", description="You do not have the required items or tokens.", color=discord.Color.red())
                await interaction.response.send_message(embed=error_embed, ephemeral=True)


        async def close_menu(self, interaction: discord.Interaction):
            # Stop the view to close the menu
            self.stop()
            await interaction.response.send_message("Crafting menu closed.", ephemeral=True)

    @commands.command()
    async def craft(self, ctx):
        profile_cog = self.client.get_cog("ProfileCog")
        user_data = profile_cog.get_user_data(ctx.author.id)

        craftable_items = []
        craft_embed = discord.Embed(title="Crafting Recipes", description="Select an item to craft", color=discord.Color.blue())

        for item_name, details in self.recipes.items():
            for recipe in details["recipes"]:
                max_craftable_amount = float('inf')
                for required_item, amount in recipe["cost"].items():
                    item_count = user_data["inventory"].count(required_item)
                    if item_count < amount:
                        max_craftable_amount = 0
                        break
                    else:
                        max_craftable_amount = min(max_craftable_amount, item_count // amount)

                token_cost = recipe.get("token_cost", 0)
                if user_data["tokens"] < token_cost:
                    max_craftable_amount = 0
                else:
                    max_craftable_amount = min(max_craftable_amount, user_data["tokens"] // token_cost)

                if max_craftable_amount > 0:
                    craftable_items.append(item_name)
                    craft_embed.add_field(name=f"{item_name} ✅", value=f"{details['recipes'][0]['description']}\n(Can craft: {max_craftable_amount})", inline=False)
                else:
                    craft_embed.add_field(name=item_name, value=details["recipes"][0]["description"], inline=False)

        if not craftable_items:
            no_craft_embed = discord.Embed(title="Crafting Unavailable", description="You don't have the necessary items to craft anything.", color=discord.Color.red())
            await ctx.send(embed=no_craft_embed)
            return

        view = self.CraftingView(craftable_items, ctx, self.recipes, profile_cog)
        await ctx.send(embed=craft_embed, view=view)



        
def setup(client):
    client.add_cog(CraftingCog(client))
