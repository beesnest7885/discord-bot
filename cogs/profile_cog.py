import nextcord
from nextcord.ext.commands import Cog
from nextcord.ext import commands
import sqlite3
import json
import random
from typing import Optional, Dict, Union, List


class ProfileCog(Cog):
    def __init__(self, client):
        self.client = client
        self.conn = sqlite3.connect('database.db')
        self.cursor = self.conn.cursor()
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS profiles 
                            (user_id TEXT PRIMARY KEY, races_won INT, races_lost INT, challenges_won INT,
                            challenges_lost INT, fights_won INT, fights_lost INT, tokens INT,
                            xp INT, rank TEXT, inventory TEXT)''')
         # New tokens table
        self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS tokens (
                    symbol TEXT PRIMARY KEY,
                    name TEXT,
                    current_value REAL
                )
            ''')

            # New balances table
        self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS balances (
                    user_id TEXT,
                    token TEXT,
                    amount REAL,
                    PRIMARY KEY (user_id, token)
                )
            ''')

            # Insert initial values for tokens
        self.cursor.execute('''
                INSERT INTO tokens (symbol, name, current_value) VALUES
                ('USDC', 'USD Coin', 1.0),
                ('ETH', 'Ethereum', 0.0),
                ('MATIC', 'Polygon', 0.0),
                ('BTC', 'Bitcoin', 0.0)
                ON CONFLICT(symbol) DO NOTHING
            ''')

        self.conn.commit()

    # --- Database Utilities ---

    def get_user_data(self, user_id: int) -> Optional[Dict[str, Union[int, str, bool, List[str]]]]:
        try:
            self.cursor.execute("SELECT * FROM profiles WHERE user_id=?", (user_id,))
            data = self.cursor.fetchone()
            if data:
                return {
                    "user_id": data[0],
                    "races_won": data[1],
                    "races_lost": data[2],
                    "challenges_won": data[3],
                    "challenges_lost": data[4],
                    "fights_won": data[5],
                    "fights_lost": data[6],
                    "tokens": data[7],
                    "xp": data[8],
                    "rank": data[9],
                    "inventory": json.loads(data[10]) if data[10] else [],
                    "has_active_charm": bool(data[11])
                }
            else:
                return None
        except sqlite3.Error as e:
            print(f"SQLite error: {e}")
            return None

    def save_user_data(self, user_data: Dict[str, Union[int, str, bool, List[str]]]):
        try:
            self.cursor.execute('''INSERT OR REPLACE INTO profiles 
                              (user_id, races_won, races_lost, challenges_won, challenges_lost, 
                              fights_won, fights_lost, tokens, xp, rank, inventory, has_active_charm)
                              VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                              (user_data["user_id"], user_data["races_won"], user_data["races_lost"],
                               user_data["challenges_won"], user_data["challenges_lost"], user_data["fights_won"],
                               user_data["fights_lost"], user_data["tokens"], user_data["xp"],
                               user_data.get("rank", ""), json.dumps(user_data["inventory"]), user_data.get("has_active_charm", False)))
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"SQLite error: {e}")

    # ... rest of your methods ...

        # ... continuation of the ProfileCog ...

    # --- Profile Management ---

    def check_charm(self, user_id: int) -> bool:
        user_data = self.get_user_data(user_id)
        return user_data and user_data.get('has_active_charm', False)

    def update_profile(self, user_id: int, category: str = None, action: str = None, item: Optional[str] = None, tokens: int = 0):
        user_data = self.get_user_data(user_id) or {
            'user_id': user_id,
            'races_won': 0,
            'races_lost': 0,
            'challenges_won': 0,
            'challenges_lost': 0,
            'fights_won': 0,
            'fights_lost': 0,
            'tokens': 0,
            'xp': 0,
            'inventory': [],
            'has_active_charm': False
        }

        if category and action:
            if action == "win":
                user_data[f'{category}_won'] += 1
            elif action == "lose":
                user_data[f'{category}_lost'] += 1

        if item:
            user_data['inventory'].append(item)

        user_data['tokens'] += tokens

        self.save_user_data(user_data)

    def deactivate_charm(self, user_id: int):
        user_data = self.get_user_data(user_id)
        if user_data and 'has_active_charm' in user_data:
            user_data['has_active_charm'] = False
            self.save_user_data(user_data)

    def add_xp(self, user_id: int, amount: int):
        user_data = self.get_user_data(user_id)
        if user_data:
            user_data['xp'] += amount
            self.update_rank(user_data)
            self.save_user_data(user_data)

    def update_rank(self, user_data: dict):
        xp = user_data['xp']

        if xp < 1000:
            rank = "Beginner"
        elif xp < 2000:
            rank = "Novice"
        elif xp < 4000:
            rank = "Skilled"
        elif xp < 8000:
            rank = "Expert"
        else:
            rank = "Master"

        user_data['rank'] = rank

    def add_tokens(self, user_id: int, amount: int):
        user_data = self.get_user_data(user_id)
        if user_data:
            user_data['tokens'] += amount
            self.save_user_data(user_data)

    def remove_tokens(self, user_id: int, amount: int):
        user_data = self.get_user_data(user_id)
        if user_data:
            user_data['tokens'] -= amount
            self.save_user_data(user_data)

    def has_item(self, user_id: int, item_name: str):
        user_data = self.get_user_data(user_id)
        return item_name in user_data['inventory']
    
    def has_enough_tokens(self, user_id: int, required_amount: int) -> bool:
        user_data = self.get_user_data(user_id)
        if user_data:
            return user_data["tokens"] >= required_amount
        return False

    def has_enough_items(self, user_id: int, item_name: str, required_amount: int) -> bool:
        user_data = self.get_user_data(user_id)
        if user_data:
            item_count = user_data["inventory"].count(item_name)
            return item_count >= required_amount
        return False

    def add_item(self, user_id: int, item_name: str) -> None:
        user_data = self.get_user_data(user_id)
        if user_data:
            user_data["inventory"].append(item_name)
            self.save_user_data(user_data)
        
    def remove_item_from_inventory(self, user_id: int, item_name: str, tokens_to_add: int = 0):
        user_data = self.get_user_data(user_id)
        if item_name in user_data['inventory']:
            user_data['inventory'].remove(item_name)
            user_data['tokens'] += tokens_to_add
            self.save_user_data(user_data)

    def use_charm(self, user_id: int):
        user_data = self.get_user_data(user_id)
        charm_uses = user_data.get('charm_uses', 0)
        
        # Check if the charm is still usable
        if charm_uses > 0:
            user_data['charm_uses'] -= 1
            self.save_user_data(user_data)
            if user_data['charm_uses'] == 0:
                user_data['inventory'].remove('lucky_charm')
                self.save_user_data(user_data)
            return True
        else:
            return False

    def get_item_info(self, item_name):
        """Return information about a specific item from items.json."""
        with open('items.json', 'r') as f:
            items = json.load(f)
            
        return items.get(item_name)



    @commands.command()
    async def user(self, ctx):
        user_data = self.get_user_data(ctx.author.id)

        if not user_data:
            self.update_profile(ctx.author.id)
            user_data = self.get_user_data(ctx.author.id)  # Fetch again after initializing

        # Load special items from shop.json and crafting.json
        with open('shop.json', 'r') as f:
            shop_items = json.load(f)
        with open('crafting.json', 'r') as f:
            crafting_items = json.load(f)

        # Create a list of special items
        special_item_names = set(shop_items.keys()) | set(crafting_items.keys()) | {"mystery_box"}

        # Tally the items
        special_items = {}
        other_items_count = 0
        for item in user_data['inventory']:
            if item in special_item_names:
                special_items[item] = special_items.get(item, 0) + 1
            else:
                other_items_count += 1

        # Convert to the desired display format
        special_items_display = [f"{item} (x{count})" for item, count in special_items.items()]

        # Create the embed
        embed = nextcord.Embed(title=f"{ctx.author.name}'s Profile", color=nextcord.Color.blue())

        # ... [Add other fields like races won, tokens, xp, etc.]

        
        # Win/Loss Records
        embed.add_field(name='Races Won', value=user_data['races_won'], inline=True)
        embed.add_field(name='Races Lost', value=user_data['races_lost'], inline=True)
        embed.add_field(name='Challenges Won', value=user_data['challenges_won'], inline=True)
        embed.add_field(name='Challenges Lost', value=user_data['challenges_lost'], inline=True)
        embed.add_field(name='Fights Won', value=user_data['fights_won'], inline=True)
        embed.add_field(name='Fights Lost', value=user_data['fights_lost'], inline=True)

        # Tokens, XP, and Inventory
        embed.add_field(name='Token Balance', value=user_data['tokens'], inline=True)
        embed.add_field(name='XP', value=user_data['xp'], inline=True)
        embed.add_field(name='Rank', value=user_data.get('rank', 'N/A'), inline=True)
        # Add fields for special and other items
        embed.add_field(name='Special Items', value=', '.join(special_items_display) if special_items_display else 'None', inline=False)
        embed.add_field(name='Other Items', value=f"Total Count: {other_items_count}", inline=False)

        await ctx.send(embed=embed)



    @commands.command()
    async def fight_leaderboard(self, ctx):
        self.cursor.execute("SELECT user_id, fights_won FROM profiles ORDER BY fights_won DESC LIMIT 10")
        results = self.cursor.fetchall()

        embed = nextcord.Embed(title="Fight Wins Leaderboard")
        for idx, (user_id, fights_won) in enumerate(results, 1):
            user = await self.client.fetch_user(int(user_id))
            embed.add_field(name=f"{idx}. {user.name}", value=f"{fights_won} wins")
        await ctx.send(embed=embed)

    @commands.command()
    async def token_leaderboard(self, ctx):
        self.cursor.execute("SELECT user_id, tokens FROM profiles ORDER BY tokens DESC LIMIT 10")
        results = self.cursor.fetchall()

        embed = nextcord.Embed(title="Token Balance Leaderboard")
        for idx, (user_id, tokens) in enumerate(results, 1):
            user = await self.client.fetch_user(int(user_id))
            embed.add_field(name=f"{idx}. {user.name}", value=f"{tokens} tokens")
        await ctx.send(embed=embed)

    

    
    def cog_unload(self):
        """Close the database connection when the cog unloads."""
        if self.conn:
            self.conn.close()

def setup(client):
    client.add_cog(ProfileCog(client))

