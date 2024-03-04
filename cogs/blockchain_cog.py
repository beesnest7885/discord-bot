import nextcord
from nextcord.ext import commands
import requests

class DexScreenerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def fetch_data(self, url):
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error fetching data: {e}")
            return None

    @commands.command(name='get_pairs')
    async def get_pairs(self, ctx, chain_id: str, pair_addresses: str):
        url = f"https://api.dexscreener.com/latest/dex/pairs/{chain_id}/{pair_addresses}"
        data = await self.fetch_data(url)
        if data:
            embed = nextcord.Embed(title="Pair Information", color=0x00ff00)
            for pair in data['pairs']:
                embed.add_field(name="Pair Address", value=pair['pairAddress'], inline=False)
                embed.add_field(name="Base Token", value=f"{pair['baseToken']['name']} ({pair['baseToken']['symbol']})", inline=True)
                embed.add_field(name="Quote Token", value=pair['quoteToken']['symbol'], inline=True)
                embed.add_field(name="Price (USD)", value=pair.get('priceUsd', 'N/A'), inline=True)
                embed.add_field(name="Liquidity (USD)", value=pair['liquidity'].get('usd', 'N/A') if pair.get('liquidity') else 'N/A', inline=True)
                embed.add_field(name="Volume (24h)", value=pair['volume']['h24'], inline=True)
                embed.add_field(name="Price Change (24h)", value=f"{pair['priceChange']['h24']}%", inline=True)
                # Add more fields as needed

            await ctx.send(embed=embed)

    @commands.command(name='get_token')
    async def get_token(self, ctx, token_address: str):
        url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
        data = await self.fetch_data(url)
        if data and 'pairs' in data and len(data['pairs']) > 0:
            token_info = data['pairs'][0]  # Assuming you want to display the first token in the list
            embed = nextcord.Embed(title=f"Token Information: {token_info['baseToken']['name']} ({token_info['baseToken']['symbol']})", color=0x00ff00)
            embed.add_field(name="Chain ID", value=token_info['chainId'], inline=True)
            embed.add_field(name="Pair Address", value=token_info['pairAddress'], inline=True)
            embed.add_field(name="Price (Native)", value=token_info['priceNative'], inline=True)
            embed.add_field(name="Price (USD)", value=token_info.get('priceUsd', 'N/A'), inline=True)
            embed.add_field(name="Volume (24h)", value=token_info['volume']['h24'], inline=True)
            embed.add_field(name="Liquidity (USD)", value=token_info['liquidity'].get('usd', 'N/A'), inline=True)
            embed.add_field(name="Fully Diluted Valuation", value=token_info.get('fdv', 'N/A'), inline=True)
            embed.add_field(name="Pair URL", value=token_info['url'], inline=False)

            await ctx.send(embed=embed)
        else:
            await ctx.send("Token data not found.")


    @commands.command(name='search_pairs')
    async def search_pairs(self, ctx, query: str):
        url = f"https://api.dexscreener.com/latest/dex/search/?q={query}"
        data = await self.fetch_data(url)
        if data and 'pairs' in data and len(data['pairs']) > 0:
            for pair in data['pairs'][:4]:  # Limit to the first 5 pairs
                embed = nextcord.Embed(title=f"Pair: {pair['baseToken']['name']} ({pair['baseToken']['symbol']}) / {pair['quoteToken']['name']} ({pair['quoteToken']['symbol']})", color=0x00ff00)
                embed.add_field(name="Chain ID", value=pair['chainId'], inline=True)
                embed.add_field(name="DEX ID", value=pair['dexId'], inline=True)
                embed.add_field(name="Pair Address", value=pair['pairAddress'], inline=True)
                embed.add_field(name="Price (Native)", value=pair['priceNative'], inline=True)
                embed.add_field(name="Price (USD)", value=pair.get('priceUsd', 'N/A'), inline=True)
                embed.add_field(name="Volume (24h)", value=pair['volume']['h24'], inline=True)
                embed.add_field(name="Liquidity (USD)", value=pair['liquidity'].get('usd', 'N/A'), inline=True)
                embed.add_field(name="Price Change (24h)", value=f"{pair['priceChange']['h24']}%", inline=True)
                embed.add_field(name="Pair URL", value=pair['url'], inline=False)

                await ctx.send(embed=embed)
                # Add a delay if necessary to avoid rate limiting
        else:
            await ctx.send("No pair data found.")



def setup(bot):
    bot.add_cog(DexScreenerCog(bot))
