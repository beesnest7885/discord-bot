import nextcord
from nextcord.ext import commands
import asyncio
import random

    
class battleroyalCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot    
    
    @commands.command(name='battle')
    async def battle(self, ctx):
        players = []

        # Inform players about the brawl and how to join
        embed = nextcord.Embed(title="Battle!", description="A brawl is starting! React with 💪 to join within the next 20 seconds!", color=0xFF4500)
        msg = await ctx.send(embed=embed)
        await msg.add_reaction('💪')

        await asyncio.sleep(20)
        msg = await ctx.channel.fetch_message(msg.id)

        for reaction in msg.reactions:
            if reaction.emoji == '💪':
                async for user in reaction.users():
                    if user != self.bot.user:
                        players.append(user)

        if len(players) < 2:
            embed = nextcord.Embed(title="Brawl Result", description="Not enough players joined the brawl!", color=0xFF4500)
            await ctx.send(embed=embed)
            return

        player_healths = {player: 100 for player in players} 

        while len([player for player, health in player_healths.items() if health > 0]) > 1:  # Check there's more than one player alive
            player1, player2 = random.choices(list(player_healths.keys()), k=2)  # This allows the possibility to select an eliminated player
            
            # If one of the chosen players is eliminated, skip the round
            if player_healths[player1] <= 0 or player_healths[player2] <= 0:
                continue

            player1_damage = random.randint(5, 20)
            player2_damage = random.randint(5, 20)

            player_healths[player2] -= player1_damage
            player_healths[player1] -= player2_damage

            attack_descriptions = [
                f"{player1.display_name} attacks {player2.display_name}, dealing {player1_damage} damage!",
                f"{player2.display_name} retaliates, inflicting {player2_damage} damage on {player1.display_name}!"
            ]

            embed = nextcord.Embed(title="Brawl Update", description="\n".join(attack_descriptions), color=0xFFFF00)
            await ctx.send(embed=embed)
            await asyncio.sleep(2)

        # Finding the winner - the player with health above 0
        winner = [player for player, health in player_healths.items() if health > 0][0]
        embed = nextcord.Embed(title="Brawl Result", description=f"{winner.mention} is the last one standing!", color=0x00FF00)
        await ctx.send(embed=embed)

def setup(client):
    client.add_cog(battleroyalCog(client))

