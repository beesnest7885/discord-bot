import json
import nextcord
from nextcord.ext import commands
from nextcord import Interaction, SlashOption

class WalletWhitelistCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.wallet_file = "wallet_addresses.json"
        self.role_id = None  # Role ID to be assigned

    def save_wallet_data(self, user_id, user_name, wallet_address):
        try:
            with open(self.wallet_file, "r") as file:
                data = json.load(file)
        except FileNotFoundError:
            data = {}

        data[user_id] = {"username": user_name, "wallet_address": wallet_address}

        with open(self.wallet_file, "w") as file:
            json.dump(data, file, indent=4)

    @nextcord.slash_command(name="setrole", description="Set the role to assign to whitelisted users")
    @commands.has_permissions(administrator=True)
    async def set_role(self, interaction: Interaction, role: nextcord.Role):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
            return

        self.role_id = role.id
        await interaction.response.send_message(f"Role set to: {role.name}", ephemeral=True)


    @nextcord.slash_command(name="whitelist", description="Submit your wallet address for whitelisting")
    async def whitelist(self, interaction: Interaction, wallet_address: str = SlashOption(description="Your wallet address")):
        user_id = str(interaction.user.id)
        user_name = interaction.user.name

        self.save_wallet_data(user_id, user_name, wallet_address)

        if self.role_id:
            role = interaction.guild.get_role(self.role_id)
            if role:
                await interaction.user.add_roles(role)
                await interaction.response.send_message(f"Thanks, your wallet address has been recorded. You've been given the {role.name} role.", ephemeral=True)
            else:
                await interaction.response.send_message("Role not found. Please have an admin set the role again.", ephemeral=True)
        else:
            await interaction.response.send_message("Thanks, your wallet address has been recorded, but no role is set for assignment.", ephemeral=True)

def setup(bot):
    bot.add_cog(WalletWhitelistCog(bot))
