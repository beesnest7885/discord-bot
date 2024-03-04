import nextcord
from nextcord.ext import commands
from datetime import datetime, timedelta
import random
import asyncio


# Create a dictionary to hold player scores, this should ideally be loaded from a database or file
player_scores = {}
bad_events = ["Caught by the trainyard security", "Tripped over loose rail ties", "Lost your map and took a wrong turn", "Backpack strap broke, spilling essentials", "Hitchhiked on a train going the wrong direction", "Caught in a makeshift trap set by rivals", "Bitten by a stray dog guarding a shortcut", "Caught a 'bad ticket' (caught a disease)", "Ran afoul of a hostile vagrant", "Sleeping bag taken by gang members"]
good_events = ["Found a stash of food and water", "Caught a fast train going in the right direction", "Received useful gear from a sympathetic rail worker", "Discovered a shortcut through an abandoned tunnel", "Met a friendly stray dog that helped guide the way", "Found a hidden cache of first-aid supplies", "Stumbled upon an old, working bicycle", "Encountered a kind stranger who gave accurate directions", "Found a functioning GPS device among discarded items", "Got a tip about a police checkpoint and successfully avoided it"]
neutral_events = ["Cross paths with a group of graffiti artists", "Witness a beautiful sunset over a derelict factory", "Encounter a disused train car covered in murals","Find an old harmonica next to the tracks", "Stumble upon a makeshift shrine or memorial", "Run into a fellow hobo who shares a story but no useful information", "Discover an old, rusted-out locomotive off to the side of the tracks", "Hear the distant sound of a live band playing in a nearby town", "Find a pile of discarded books and magazines", "Come across a campfire site that has already been extinguished"]
hobo_names = ["Boxcar Benny", "Tumbleweed Tina", "Switchyard Sam", "Junkyard Jill", "Railroader Randy", "Hobo Harry", "Rucksack Rosie", "Nomad Nancy", "Freight-train Fred", "Drifter Dave"]

class ChallengeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.user_cooldowns = {}
        self.difficulty_level = 1
 
    @commands.command()
    async def challenge(self, ctx):
        user_id = ctx.author.id
        allowed_channel_id = 1006296186828902421

        if ctx.channel.id != allowed_channel_id:
            await ctx.send("This command can only be used in the racing channel!")
            return
        
        

        if user_id in self.user_cooldowns:
            time_passed = datetime.now() - self.user_cooldowns[user_id]
            if time_passed < timedelta(hours=1):
                remaining_time = timedelta(hours=1) - time_passed
                embed = nextcord.Embed(title="Cooldown Active", 
                                       description=f"You must wait {remaining_time} before issuing this command again.", 
                                       color=0xff0000)  # Red for cooldown
                await ctx.send(embed=embed)
                return

        embed = nextcord.Embed(title="Challenge Started!", 
                               description="The hobos line up at the end of the road!", 
                               color=0x00ff00)  # Green for starting
        await ctx.send(embed=embed)
        self.user_cooldowns[user_id] = datetime.now()
        
        self.difficulty_level
    
        # Ensure minimum difficulty level is 1
        self.difficulty_level = max(1, self.difficulty_level)
        
        user = ctx.author
        user_id = user.id  # Get the user's ID for easy reference
        computer_hobos_count = 3 + self.difficulty_level  # Start with fewer hobos

        players = [{"user": user, "name": random.choice(hobo_names)}]
        for i in range(computer_hobos_count):
            players.append({"user": f"ComputerHobo{i}", "name": random.choice(hobo_names)})

        participants_list = "\n".join([f"{player['user']} as {player['name']}" for player in players])

        # Embedding the racer list
        reward = random.randint(100, 200)
        multiplier = len(players) // 5  # Multiplier for every 5 participants
        reward *= (1 + multiplier)

        # Embedding the racer list
        participants_list += f"\n\nTotal Sandwich Tokens for the winner: {reward}"
        embed_title = f"Racers List - Difficulty Level {self.difficulty_level}"
        embed = nextcord.Embed(title=embed_title, description=participants_list, color=0x87ceeb)
        await ctx.send(embed=embed)

        while len(players) > 1 and any(p['user'] == user for p in players):
            events_for_round = []
            for player in players[:]:  # Start of for loop
                event_chance = random.randint(1, 10 + self.difficulty_level)  # Adjust event chance based on difficulty level

                # User gets slightly better odds than computer hobos
                if player['user'] == user:
                    if event_chance <= 2:  # Bad event
                        bad_event = random.choice(bad_events)
                        events_for_round.append(f"{player['name']} ({player['user'].mention}): {bad_event}")
                        players.remove(player)
                    elif 1 < event_chance <= 6:  # Good event
                        good_event = random.choice(good_events)
                        events_for_round.append(f"{player['name']} ({player['user'].mention}): {good_event}")

                        if players.index(player) != 0:
                            idx = players.index(player)
                            players[idx], players[idx - 1] = players[idx - 1], players[idx]
                    else:  # Neutral event
                        neutral_event = random.choice(neutral_events)
                        events_for_round.append(f"{player['name']} ({player['user'].mention}): {neutral_event}")
                else:  # Logic for computer hobos
                    if event_chance <= 3:  # Bad event
                        bad_event = random.choice(bad_events)
                        events_for_round.append(f"{player['name']} ({player['user']}): {bad_event}")
                        players.remove(player)
                    elif 2 < event_chance <= 5:  # Good event
                        good_event = random.choice(good_events)
                        events_for_round.append(f"{player['name']} ({player['user']}): {good_event}")

                        if players.index(player) != 0:
                            idx = players.index(player)
                            players[idx], players[idx - 1] = players[idx - 1], players[idx]
                    else:  # Neutral event
                        neutral_event = random.choice(neutral_events)
                        events_for_round.append(f"{player['name']} ({player['user']}): {neutral_event}")
            # End of for loop

            embed = nextcord.Embed(title="Race Update", description="\n".join(events_for_round), color=0x87ceeb)
            await ctx.send(embed=embed)
            await asyncio.sleep(5)

        win = len(players) == 1 or any(p['user'] == ctx.author for p in players)

        # Fetch cogs
        profile_cog = self.bot.get_cog('ProfileCog')
        achievements_cog = self.bot.get_cog('AchievementsCog')  # Fetch AchievementsCog
        xp_cog = self.bot.get_cog('XPCog')

        # Update difficulty level and user profile
        if win:
            self.difficulty_level += 1 # Increment difficulty level for a win
            if profile_cog:
                profile_cog.add_tokens(user_id, reward)
                profile_cog.update_profile(user_id, category='challenges', action='win')
            if xp_cog:
                xp_cog.add_xp(user_id, 50) # adds 50 xp
            color = 0x00ff00  # Green for win
            title = "You Won!"
            description = f"Your cooldown has been reset! Difficulty level is now {self.difficulty_level}."
            if user_id in self.user_cooldowns:
                del self.user_cooldowns[user_id]
        else:
            self.difficulty_level = max(1, self.difficulty_level - 1)  # Decrement, but don't go below 1
            if profile_cog:
                profile_cog.update_profile(user_id, category='challenges', action='lose')
            color = 0xff0000  # Red for loss
            title = "You Lost!"
            description = f"You raced hard, take some time out! See you in 1 hour! Difficulty level is now {self.difficulty_level}."
            self.user_cooldowns[user_id] = datetime.now()

        try:
            embed = nextcord.Embed(title=title, description=description, color=color)
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"Error: {e}")

def setup(client):
    client.add_cog(ChallengeCog(client))
