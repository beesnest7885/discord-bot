import nextcord
from nextcord.ext import commands, tasks
import sqlite3
import random
from datetime import datetime, timedelta
import logging
intents = nextcord.Intents.default()
intents.members = True
image_urls = [
            "https://cdn.discordapp.com/attachments/1093633450671608001/1184568854010134598/Screenshot_2023-12-02_at_11.58.25.png?ex=658c72b7&is=6579fdb7&hm=4ed9b540d1596b3cea550513bd591c9569d43a744903877db9009f877a68ca2c&",
            "https://cdn.discordapp.com/attachments/1093633450671608001/1184568836683469010/yoots.png?ex=658c72b2&is=6579fdb2&hm=f65d80c64a610552671fa4eace1a5f2b756fbaeb65f476ae91904a3d995e0fd5&"
            ]

class RaffleCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conn = sqlite3.connect('database.db')
        self.cursor = self.conn.cursor()
        self.initialize_database()
        self.raffle_reward = 5000
        self.last_reward_reduction = datetime.now()
        self.raffle_loop.start()
        self.active_tickets = False  # Flag to track if there are active tickets
        self.raffle_count = 0  # Counter for number of raffles conducted
        

    @commands.command(name='startraffle')
    @commands.has_permissions(administrator=True)
    async def start_raffle(self, ctx):
        if not self.raffle_loop.is_running():
            self.raffle_loop.start()
            await ctx.send("Raffle system started.")
        else:
            await ctx.send("The raffle system is already running.")

    @commands.command(name='stopraffle')
    @commands.has_permissions(administrator=True)
    async def stop_raffle(self, ctx):
        if self.raffle_loop.is_running():
            self.raffle_loop.cancel()
            await ctx.send("Raffle system stopped.")
        else:
            await ctx.send("The raffle system is not currently running.")

    def get_active_tickets_count(self):
        try:
            with self.conn:
                self.cursor.execute("SELECT COUNT(*) FROM raffle_pool WHERE expiration_date > ?", (datetime.now(),))
                return self.cursor.fetchone()[0]
        except sqlite3.Error as e:
            logging.error(f"SQLite error in get_active_tickets_count: {e}")
            return 0  # Return 0 in case of an error

    def has_active_tickets(self):
        self.cursor.execute("SELECT COUNT(*) FROM raffle_pool WHERE expiration_date > ?", (datetime.now(),))
        count = self.cursor.fetchone()[0]
        return count > 0
    
    def get_raffles_completed(self):
        self.cursor.execute("SELECT COUNT(*) FROM raffle_history")
        return self.cursor.fetchone()[0]
    def get_total_reward_distributed(self):
        self.cursor.execute("SELECT SUM(reward) FROM raffle_history")
        result = self.cursor.fetchone()[0]
        return result if result is not None else 0


    def initialize_database(self):
        try:
            # Separately handle each ALTER TABLE to avoid issues with existing columns
            try:
                self.cursor.execute("ALTER TABLE profiles ADD COLUMN category TEXT")
            except sqlite3.OperationalError:
                pass

            try:
                self.cursor.execute("ALTER TABLE raffle_history ADD COLUMN blocks_won INTEGER DEFAULT 0")
            except sqlite3.OperationalError:
                pass  # Ignore if the column already exists

            # Create 'raffle_history' table if it doesn't exist
            self.cursor.execute('''CREATE TABLE IF NOT EXISTS raffle_history (
                                    raffle_id INTEGER PRIMARY KEY AUTOINCREMENT,
                                    winner_id INTEGER,
                                    reward INTEGER,
                                    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                                )''')
            self.conn.commit()
        except Exception as e:
            print(f"Error during database initialization: {e}")



    def cog_unload(self):
        self.raffle_loop.cancel()

    def get_user_data(self, user_id: int):
        try:
            with self.conn:
                self.cursor.execute("SELECT * FROM profiles WHERE user_id=?", (user_id,))
                # Rest of your code...

            data = self.cursor.fetchone()
            if data:
                return {
                    'user_id': data[0],
                    'races_won': data[1],
                    'races_lost': data[2],
                    'challenges_won': data[3],
                    'challenges_lost': data[4],
                    'fights_won': data[5],
                    'fights_lost': data[6],
                    'tokens': data[7],
                    'xp': data[8],
                    'rank': data[9],
                    'inventory': data[10],
                    'has_active_charm': data[11],
                    'active_miners': data[12],
                    'pending_rewards': data[13],
                    'category': data[14],
                    'blocks_won': data[15]
                }
        except sqlite3.Error as e:
            logging.error(f"SQLite error in get_user_data: {e}")
            return None

    def save_user_data(self, user_data):
        try:
            self.cursor.execute('''UPDATE profiles SET
                                races_won=?, races_lost=?, challenges_won=?, challenges_lost=?,
                                fights_won=?, fights_lost=?, tokens=?, xp=?, rank=?,
                                inventory=?, has_active_charm=?, active_miners=?, pending_rewards=?, category=?, blocks_won=?
                                WHERE user_id=?''',
                                (user_data['races_won'], user_data['races_lost'], 
                                user_data['challenges_won'], user_data['challenges_lost'], 
                                user_data['fights_won'], user_data['fights_lost'], 
                                user_data['tokens'], user_data['xp'], 
                                user_data['rank'], user_data['inventory'], 
                                user_data['has_active_charm'], user_data['active_miners'], 
                                user_data['pending_rewards'], user_data['category'],
                                user_data['blocks_won'], user_data['user_id']))  # Corrected the order
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"SQLite error: {e}")


    def get_ticket_info(self, user_id):
        # Fetch the count of active tickets
        self.cursor.execute("SELECT COUNT(*) FROM raffle_pool WHERE user_id=? AND expiration_date > ?", (user_id, datetime.now()))
        active_tickets_count = self.cursor.fetchone()[0]

        # Fetch the next expiration date
        self.cursor.execute("SELECT MIN(expiration_date) FROM raffle_pool WHERE user_id=? AND expiration_date > ?", (user_id, datetime.now()))
        next_expiration_result = self.cursor.fetchone()[0]
        next_expiration = next_expiration_result if next_expiration_result else "No active tickets"

        # Fetch the number of raffles won
        self.cursor.execute("SELECT blocks_won FROM profiles WHERE user_id=?", (user_id,))
        raffles_won = self.cursor.fetchone()[0]

        return active_tickets_count, next_expiration, raffles_won
    
     # Define get_active_users_count method
    def get_active_users_count(self):
        self.cursor.execute("SELECT COUNT(DISTINCT user_id) FROM raffle_pool WHERE expiration_date > ?", (datetime.now(),))
        return self.cursor.fetchone()[0]


    def add_ticket_to_pool(self, user_id, ticket_number, expiration_date):
        try:
            self.cursor.execute("INSERT INTO raffle_pool (ticket_number, user_id, expiration_date) VALUES (?, ?, ?)",
                                (ticket_number, user_id, expiration_date))
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"SQLite error: {e}")
            

    @commands.command(name='buytickets')
    async def buy_tickets(self, ctx):
        user_id = str(ctx.author.id)
        active_tickets_count, next_expiration, raffles_won = self.get_ticket_info(user_id)

        embed = nextcord.Embed(title="Raffle Ticket Purchase", description="Select the tier of miners you want to buy.", color=0x00ff00)
        embed.add_field(name="Tier 1", value="1000 tokens for 1 ticket", inline=False)
        embed.add_field(name="Tier 2", value="2000 tokens for 3 tickets", inline=False)
        embed.add_field(name="Tier 3", value="3000 tokens for 6 tickets", inline=False)

        # Add additional information
        embed.add_field(name="Your Active Tickets", value=f"{active_tickets_count}/20", inline=False)
        embed.add_field(name="Next Ticket Expiry", value=next_expiration or "N/A", inline=False)
        embed.add_field(name="Raffles Won", value=raffles_won or "0", inline=False)

        view = TicketPurchaseView(self, str(ctx.author.id))
        await ctx.send(embed=embed, view=view)


    @tasks.loop(minutes=1)
    async def raffle_loop(self):
        logging.info("Raffle loop triggered")
        try:
            if not self.has_active_tickets():
                logging.info("No active tickets, skipping raffle")
                return

            active_users = self.get_active_users()
            if not active_users:
                logging.info("No active users, skipping raffle")
                return

            winner_id = random.choice(active_users)
            winner = await self.bot.fetch_user(winner_id)
            if winner is None:
                logging.warning(f"Winner not found for user ID: {winner_id}")
                return

            winner_data = self.get_user_data(winner_id)
            if winner_data:
                winner_data['tokens'] += self.raffle_reward
                winner_data['blocks_won'] += 1
                self.save_user_data(winner_data)
                
                self.record_raffle_result(winner_id, self.raffle_reward, winner_data['blocks_won'])

                channel = self.bot.get_channel(1094393721040146534)
                if channel:
                    selected_url = random.choice(image_urls)
                    embed = nextcord.Embed(
                        title="Raffle Winner!",
                        description=f"Block solved! Congratulations {winner.name}#{winner.discriminator}, you won {self.raffle_reward} Sandwich Tokens!",
                        color=0x00ff00)
                    embed.set_image(url=selected_url)
                    await channel.send(embed=embed)
                    logging.info(f"Winner announced: {winner.name}#{winner.discriminator}")
            else:
                logging.warning(f"No user data found for ID: {winner_id}")

            # Raffle reward reduction logic here...
            

            # Increment the raffle count and reduce reward if needed
            self.raffle_count += 1
            if self.raffle_count >= 5000:  # Check if 5 raffles have been conducted
                self.raffle_reward *= 0.8  # Reduce the reward
                self.raffle_count = 0  # Reset the raffle counter

        except Exception as e:
            logging.exception("Error in raffle loop: ", e)

    

    def record_raffle_result(self, winner_id, reward, blocks_won):
        try:
            with self.conn:
                self.cursor.execute("INSERT INTO raffle_history (winner_id, reward, blocks_won) VALUES (?, ?, ?)", 
                                    (winner_id, reward, blocks_won))
        except sqlite3.Error as e:
            logging.error(f"SQLite error when recording raffle result: {e}")

    def get_active_users(self):
        self.cursor.execute("SELECT DISTINCT user_id FROM raffle_pool WHERE expiration_date > ?", (datetime.now(),))
        return [row[0] for row in self.cursor.fetchall()]

    @raffle_loop.before_loop
    async def before_raffle_loop(self):
        await self.bot.wait_until_ready()

    @commands.command(name='dashboard')
    async def global_dashboard(self, ctx):
        # Fetch data from the database
        active_users_count = self.get_active_users_count()
        active_tickets_count = self.get_active_tickets_count()
        raffles_completed = self.get_raffles_completed()
        total_reward_distributed = self.get_total_reward_distributed()

        # Calculate active tickets per user
        tickets_per_user = active_tickets_count / active_users_count if active_users_count else 0

        # Create the embedded message
        embed = nextcord.Embed(title="Global Dashboard", color=0x00ff00)
        embed.add_field(name="Active Users", value=str(active_users_count), inline=False)
        embed.add_field(name="Active Ticket", value=str(active_tickets_count), inline=False)
        embed.add_field(name="Average Tickets Per User", value=f"{tickets_per_user:.2f}", inline=False)
        embed.add_field(name="Blocks Completed", value=str(raffles_completed), inline=False)
        embed.add_field(name="Total Reward Distributed", value=str(total_reward_distributed), inline=False)

        await ctx.send(embed=embed)

    

class TicketPurchaseView(nextcord.ui.View):
    def __init__(self, cog, user_id):
        super().__init__()
        self.cog = cog
        self.user_id = user_id

    async def interaction_check(self, interaction: nextcord.Interaction) -> bool:
        return str(interaction.user.id) == self.user_id

    async def process_ticket_purchase(self, tier, interaction):
        user_id = self.user_id
        user_data = self.cog.get_user_data(user_id)

        if not user_data:
            await interaction.response.send_message("You don't have a profile yet. Please create one first.", ephemeral=True)
            return

        ticket_prices = {1: 1000, 2: 5000, 3: 10000}
        tickets_per_tier = {1: 1, 2: 3, 3: 6}
        cost = ticket_prices[tier]

        if user_data['tokens'] < cost:
            await interaction.response.send_message("You don't have enough tokens.", ephemeral=True)
            return
        
         # Update the flag/counter
        self.cog.active_tickets = True

        # Deduct tokens and add tickets
        user_data['tokens'] -= cost
        self.cog.save_user_data(user_data)

        expiration_date = datetime.now() + timedelta(weeks=1)  # Tickets are valid for 1 week

        for _ in range(tickets_per_tier[tier]):
            ticket_number = random.randint(1000, 9999)
            self.cog.add_ticket_to_pool(self.user_id, ticket_number, expiration_date)

        # First response
        await interaction.response.send_message(f"You have purchased {tickets_per_tier[tier]} tickets at tier {tier}.", ephemeral=True)

        # Fetch updated information after purchase
        updated_active_tickets_count, updated_next_expiration, updated_raffles_won = self.cog.get_ticket_info(self.user_id)

        # Update user data and fetch updated raffle wins
        self.cog.save_user_data(user_data)
        updated_user_data = self.cog.get_user_data(user_id)

        updated_raffles_won = updated_user_data['blocks_won']
        updated_active_tickets_count, updated_next_expiration, _ = self.cog.get_ticket_info(user_id)

        # Follow-up with updated information
        updated_additional_info = (f"Active Tickets: {updated_active_tickets_count}/20\n"
                                   f"Next Ticket Expires: {updated_next_expiration}\n"
                                   f"Raffles Won: {updated_raffles_won}")
        await interaction.followup.send(updated_additional_info, ephemeral=True)


    def add_ticket_to_pool(self, user_id, ticket_number, expiration_date):
        try:
            self.cursor.execute("INSERT INTO raffle_pool (ticket_number, user_id, expiration_date) VALUES (?, ?, ?)",
                                (ticket_number, user_id, expiration_date))
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"SQLite error: {e}")
        # ... [rest of process_ticket_purchase method logic]

    @nextcord.ui.button(label="Tier 1", style=nextcord.ButtonStyle.primary, custom_id="purchase_tier_1")
    async def handle_tier_1_purchase(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await self.process_ticket_purchase(1, interaction)

    @nextcord.ui.button(label="Tier 2", style=nextcord.ButtonStyle.primary, custom_id="purchase_tier_2")
    async def handle_tier_2_purchase(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await self.process_ticket_purchase(2, interaction)

    @nextcord.ui.button(label="Tier 3", style=nextcord.ButtonStyle.primary, custom_id="purchase_tier_3")
    async def handle_tier_3_purchase(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await self.process_ticket_purchase(3, interaction)

    

def setup(client):
    client.add_cog(RaffleCog(client))
