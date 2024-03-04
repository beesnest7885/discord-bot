import nextcord as discord
from nextcord.ext.commands import Cog, command
from nextcord.ext import commands
import json
from nextcord.ui import Button, View, Select
from nextcord import Interaction, SelectOption
import sqlite3


class ShopCog(Cog):
    def __init__(self, client):
        self.client = client

        # Load the shop items from shop.json
        with open('shop.json', 'r') as f:
            self.shop_items = json.load(f)

    def update_shop_items(self):
        with open('shop.json', 'w') as f:
            json.dump(self.shop_items, f)

    @command()
    async def shop(self, ctx):
        """Displays available items in the shop."""
        embed = discord.Embed(title="Shop", description="Available items for purchase:")
        for item, details in self.shop_items.items():
            embed.add_field(name=item, value=f"Cost: {details['price']} tokens, Quantity: {details['quantity']}", inline=False)
        await ctx.send(embed=embed)

    @command()
    async def buy(self, ctx):
        """Allows a user to buy an item from the shop."""
        profile_cog = self.client.get_cog('ProfileCog')
        user_data = profile_cog.get_user_data(ctx.author.id)

        # Create an embed with user's token balance
        embed = discord.Embed(title="Shop", description=f"Your token balance: {user_data['tokens']}")
        view = View()

        # Dropdown for selecting items
        select = Select(placeholder="Choose an item to buy")
        for item_name, item_data in self.shop_items.items():
            if item_data['quantity'] > 0:
                select.add_option(label=item_name, description=f"{item_data['price']} tokens")

        async def select_callback(interaction: Interaction):
            # Enable the buy button when an item is selected
            buy_button.disabled = False
            await interaction.response.edit_message(view=view)

        select.callback = select_callback
        view.add_item(select)

        # Buy button
        buy_button = Button(label="Buy", style=discord.ButtonStyle.green, disabled=True)

        async def buy_callback(interaction: Interaction):
            response_embed = discord.Embed(color=discord.Color.blue())  # You can change the color as needed

            if not select.values:
                response_embed.title = "Purchase Error"
                response_embed.description = "Please select an item before buying."
                await interaction.response.send_message(embed=response_embed, ephemeral=True)
                return

            selected_item = select.values[0]
            item_data = self.shop_items.get(selected_item)

            if item_data and item_data['quantity'] > 0:
                item_price = item_data['price']
                if user_data['tokens'] >= item_price:
                    # Deduct the price from user's tokens
                    user_data['tokens'] -= item_price

                    # Add the item to the user's inventory
                    user_data['inventory'].append(selected_item)

                    # Decrease the item's quantity in the shop
                    item_data['quantity'] -= 1

                    # Save the user's updated data
                    profile_cog.save_user_data(user_data)

                    # Save the updated shop items
                    with open('shop.json', 'w') as f:
                        json.dump(self.shop_items, f)

                    response_embed.title = "Purchase Successful"
                    response_embed.description = f"You bought a {selected_item} for {item_price} tokens!"
                else:
                    response_embed.title = "Insufficient Tokens"
                    response_embed.description = "You don't have enough tokens."
            else:
                response_embed.title = "Item Not Available"
                response_embed.description = f"{selected_item} is not available in the shop."

            await interaction.response.send_message(embed=response_embed, ephemeral=True)


        buy_button.callback = buy_callback
        view.add_item(buy_button)

        await ctx.send(embed=embed, view=view)
        


    @commands.command()
    async def sell(self, ctx):
        profile_cog = self.client.get_cog('ProfileCog')
        user_data = profile_cog.get_user_data(ctx.author.id)
        item_prices_by_rarity = {
            1: 10,
            2: 20,
            3: 40,
            4: 80,
            5: 160,
            6: 320
        }

        # Load items.json to get rarity ranks
        with open('items.json', 'r') as f:
            items_info = json.load(f)

        rarities = set(details['rarity'] for details in items_info.values())

        embed = discord.Embed(title="Welcome to the Shop", description="Select the rarity of the item you want to sell.")
        view = View()

        # Dropdown for selecting rarity
        rarity_select = Select(placeholder="Choose rarity")

        for rarity in rarities:
            rarity_select.add_option(label=str(rarity))

        async def rarity_callback(interaction: Interaction):
            selected_rarity = rarity_select.values[0]
            user_inventory = user_data['inventory']

            # Find the category with the selected rarity
            category_with_selected_rarity = next((category for category, details in items_info.items() if details['rarity'] == int(selected_rarity)), None)

            if not category_with_selected_rarity:
                no_category_embed = discord.Embed(title="Error", description=f"No category found for rarity '{selected_rarity}'.")
                await interaction.response.send_message(embed=no_category_embed, ephemeral=True)
                return

            # Extract items of the selected rarity
            items_of_selected_rarity = items_info[category_with_selected_rarity]['items']

            # Count how many of these items the user has
            user_items_of_rarity = {item: user_inventory.count(item) for item in items_of_selected_rarity if item in user_inventory}

            if not user_items_of_rarity:
                no_items_embed = discord.Embed(title="No items found", description=f"You don't have any items of rarity '{selected_rarity}'.")
                await interaction.response.send_message(embed=no_items_embed, ephemeral=True)
                return

            # Creating the message/embed to show the items and their counts
            items_embed = discord.Embed(title=f"Your Rarity {selected_rarity} Items", description="Items you can sell:")
            for item, count in user_items_of_rarity.items():
                items_embed.add_field(name=item, value=f"Count: {count}", inline=False)

            item_select = Select(placeholder="Choose an item to sell")
            for item in user_items_of_rarity.keys():
                item_select.add_option(label=item)

            async def item_callback(interaction: Interaction):
                nonlocal count  # Declare count as nonlocal
                selected_item = item_select.values[0]
                item_rarity = int(selected_rarity)
                count = user_items_of_rarity[selected_item]
                sale_price_per_item = item_prices_by_rarity[item_rarity]  # Get price based on rarity


                item_action_embed = discord.Embed(title=f"Sell {selected_item}", description=f"You have {count} {selected_item}(s).")
                item_action_view = View()

                # Sell 1 button
                sell_one_button = Button(label="Sell 1", style=discord.ButtonStyle.green)

                async def sell_one_callback(button_interaction: Interaction):
                    nonlocal count  # Use nonlocal to access the count variable
                    if count > 0:
                        # Deduct one item from user inventory
                        user_data['inventory'].remove(selected_item)
                        # Add token to user balance
                        user_data['tokens'] += sale_price_per_item
                        profile_cog.save_user_data(user_data)
                        response = f"You sold one {selected_item} for {sale_price_per_item} tokens."
                        count -= 1
                    else:
                        response = f"You have no more {selected_item} left to sell."

                    await button_interaction.response.send_message(response, ephemeral=True)

                sell_one_button.callback = sell_one_callback
                item_action_view.add_item(sell_one_button)

                # Sell All button
                sell_all_button = Button(label="Sell All", style=discord.ButtonStyle.red)

                async def sell_all_callback(button_interaction: Interaction):
                    nonlocal count  # If you're using the nonlocal approach for 'count'
                    if count > 0:
                        # Calculate total sale price for all items of this type
                        total_sale_price = sale_price_per_item * count

                        # Remove all items of this type from user inventory
                        user_data['inventory'] = [item for item in user_data['inventory'] if item != selected_item]

                        # Add tokens to user balance for all items sold
                        user_data['tokens'] += total_sale_price

                        # Save the updated user data
                        profile_cog.save_user_data(user_data)

                        response = f"You sold all your {count} {selected_item}(s) for {total_sale_price} tokens."
                        count = 0  # Reset count since all items are sold
                    else:
                        response = f"You have no {selected_item} left to sell."

                    await button_interaction.response.send_message(response, ephemeral=True)

                sell_all_button.callback = sell_all_callback
                item_action_view.add_item(sell_all_button)

                await interaction.response.edit_message(embed=item_action_embed, view=item_action_view)

            item_select.callback = item_callback
            items_embed.clear_fields()
            items_embed.add_field(name="Select an item to sell", value="Choose from the dropdown below.")
            view = View()
            view.add_item(item_select)
            await interaction.response.edit_message(embed=items_embed, view=view)

        rarity_select.callback = rarity_callback
        view.add_item(rarity_select)
        await ctx.send(embed=embed, view=view)






    @buy.error
    async def buy_error(self, ctx, error):
        if isinstance(error, commands.CommandInvokeError):
            await ctx.send(f"Error: {error.original}")

def setup(client):
    client.add_cog(ShopCog(client))
