import sqlite3
import requests
import random
import nextcord
from nextcord.ext import commands

class CryptoMarketCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_file = 'database.db'
        self.token_values = {'USDC': 1.0, 'SANDWICH': 1.0}  # Initial values
        self.volatile_tokens = ['ETH', 'MATIC', 'BTC']

    def initialize_database(self):
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tokens (
                    symbol TEXT PRIMARY KEY,
                    name TEXT,
                    current_value REAL
                )
            """)
            cursor.execute("""
                INSERT INTO tokens (symbol, name, current_value) VALUES
                ('USDC', 'USD Coin', 1.0),
                ('ETH', 'Ethereum', 0.0),
                ('MATIC', 'Polygon', 0.0),
                ('BTC', 'Bitcoin', 0.0)
                ON CONFLICT(symbol) DO NOTHING
            """)
            # Create balances table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS balances (
                    user_id INTEGER,
                    token TEXT,
                    amount REAL,
                    PRIMARY KEY (user_id, token)
                )
            """)
            conn.commit()

    def get_all_user_balances(self, user_id):
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT token, amount FROM balances WHERE user_id = ?", (user_id,))
            return cursor.fetchall()

    def fetch_current_price(self, token_address):
        url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            # Assuming the API returns the price in a field named 'priceUsd'
            return data.get('priceUsd', 0)
        except requests.RequestException as e:
            print(f"API response: {response_text}")
            print(f"Error fetching price for {token_address}: {e}")
            response_text = response.text if response else "No response"
            return 0

    def update_token_values(self):
        token_addresses = {
            'ETH': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
            'MATIC': '0x7D1AfA7B718fb893dB30A3aBc0Cfc608AaCfeBB0',
            'BTC': '0x2297aEbD383787A160DD0d9F71508148769342E3'
        }

        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            for token, address in token_addresses.items():
                price = self.fetch_current_price(address)
                cursor.execute("UPDATE tokens SET current_value = ? WHERE symbol = ?", (price, token))
            conn.commit()

    def adjust_token_value_on_transaction(self, token, amount, is_purchase):
        """
        Adjusts the value of the token based on the transaction.
        Increase the value for purchases, decrease for sales.
        """
        impact_factor = 0.001  # Define how much each token affects the price
        change = amount * impact_factor
        if is_purchase:
            self.token_values[token] += change
        else:
            self.token_values[token] = max(self.token_values[token] - change, 0)  # Prevent negative value


    def get_user_balance(self, user_id, token):
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT amount FROM balances WHERE user_id = ? AND token = ?", (user_id, token))
            result = cursor.fetchone()
            return result[0] if result else 0
        
    def update_balance(self, user_id, token_symbol, new_amount):
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO balances (user_id, token, amount) 
                VALUES (?, ?, ?) 
                ON CONFLICT(user_id, token) 
                DO UPDATE SET amount = ?""",
                (user_id, token_symbol, new_amount, new_amount))
            conn.commit()

    @commands.command(name='check_balance')
    async def check_balance(self, ctx):
        user_balances = self.get_all_user_balances(ctx.author.id)
        if user_balances:
            balance_message = "Your balances are:\n"
            for token, amount in user_balances:
                balance_message += f"{token}: {amount}\n"
        else:
            balance_message = "You do not have any balances."

        await ctx.send(balance_message)


    @commands.command(name='token_value')
    async def token_value(self, ctx):
        token_addresses = {
            'ETH': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
            'MATIC': '0x7D1AfA7B718fb893dB30A3aBc0Cfc608AaCfeBB0',
            'BTC': '0x2297aEbD383787A160DD0d9F71508148769342E3'
            # Add other tokens and their addresses here
        }

        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            for token, address in token_addresses.items():
                price = self.fetch_current_price(address)
                cursor.execute("UPDATE tokens SET current_value = ? WHERE symbol = ?", (price, token))

            cursor.execute("SELECT symbol, current_value FROM tokens")
            all_token_values = cursor.fetchall()

        if all_token_values:
            value_message = "Current token values are:\n"
            for token, value in all_token_values:
                value_message += f"{token}: {value}\n"
        else:
            value_message = "No token values available."

        await ctx.send(value_message)

    @commands.command(name='buy_sandwich')
    async def buy_sandwich(self, ctx, payment_token: str, amount: float):
        payment_token = payment_token.upper()
        user_balance = self.get_user_balance(ctx.author.id, payment_token)

        if payment_token not in self.token_values:
            await ctx.send(f"Token {payment_token} not recognized.")
            return

        cost_in_payment_token = amount * self.token_values['SANDWICH'] / self.token_values[payment_token]

        if user_balance < cost_in_payment_token:
            await ctx.send(f"You do not have enough {payment_token}. Required: {cost_in_payment_token}, Your balance: {user_balance}")
            return

        # Update user's balance for payment token and SANDWICH
        new_balance_payment_token = user_balance - cost_in_payment_token
        self.update_balance(ctx.author.id, payment_token, new_balance_payment_token)

        new_balance_sandwich = self.get_user_balance(ctx.author.id, 'SANDWICH') + amount
        self.update_balance(ctx.author.id, 'SANDWICH', new_balance_sandwich)

        # Adjust SANDWICH token value based on the transaction
        self.adjust_token_value_on_transaction('SANDWICH', amount, is_purchase=True)

        await ctx.send(f"Successfully bought {amount} SANDWICH tokens with {cost_in_payment_token} {payment_token}.")


    @commands.command(name='sell_sandwich')
    async def sell_sandwich(self, ctx, receiving_token: str, amount: float):
        receiving_token = receiving_token.upper()
        sandwich_balance = self.get_user_balance(ctx.author.id, 'SANDWICH')

        if receiving_token not in self.token_values:
            await ctx.send(f"Token {receiving_token} not recognized.")
            return

        if sandwich_balance < amount:
            await ctx.send(f"You do not have enough SANDWICH tokens. Required: {amount}, Your balance: {sandwich_balance}")
            return

        # Calculate how much of the receiving token they get for their Sandwich tokens
        amount_in_receiving_token = amount * self.token_values['SANDWICH'] / self.token_values[receiving_token]

        # Update user's balance for SANDWICH and the receiving token
        new_balance_sandwich = sandwich_balance - amount
        self.update_balance(ctx.author.id, 'SANDWICH', new_balance_sandwich)

        new_balance_receiving = self.get_user_balance(ctx.author.id, receiving_token) + amount_in_receiving_token
        self.update_balance(ctx.author.id, receiving_token, new_balance_receiving)

        # Adjust SANDWICH token value based on the transaction
        self.adjust_token_value_on_transaction('SANDWICH', amount, is_purchase=False)

        # Fetch the updated balances to display to the user
        updated_sandwich_balance = self.get_user_balance(ctx.author.id, 'SANDWICH')
        updated_receiving_balance = self.get_user_balance(ctx.author.id, receiving_token)

        await ctx.send(
            f"Successfully sold {amount} SANDWICH tokens for {amount_in_receiving_token} {receiving_token}.\n"
            f"Your new SANDWICH balance: {updated_sandwich_balance}\n"
            f"Your new {receiving_token} balance: {updated_receiving_balance}"
        )


def setup(bot):
    bot.add_cog(CryptoMarketCog(bot))
