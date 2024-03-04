from nextcord.ext import commands
import nextcord
import json
import sys
import asyncio


class AdminCog(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.trusted_users = set()
        self.load_trusted_users()
        self.thread_channel = None

    def load_trusted_users(self):
        """Load the trusted users from a JSON file."""
        try:
            with open('trusted_users.json', 'r') as f:
                self.trusted_users = set(json.load(f))
        except FileNotFoundError:
            pass

    def save_trusted_users(self):
        """Save the trusted users to a JSON file."""
        with open('trusted_users.json', 'w') as f:
            json.dump(list(self.trusted_users), f)

    # Function to check if a user is an admin or a trusted user
    def is_admin_or_trusted(self, ctx):
        return ctx.author.guild_permissions.administrator or ctx.author.id in self.trusted_users

    

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def addtrusted(self, ctx, user: nextcord.Member):
        self.trusted_users.add(user.id)
        self.save_trusted_users()
        await ctx.send(f"{user.mention} has been added to the trusted users list.")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def removetrusted(self, ctx, user: nextcord.Member):
        self.trusted_users.discard(user.id)
        self.save_trusted_users()
        await ctx.send(f"{user.mention} has been removed from the trusted users list.")

    @commands.command()
    async def adminonly(self, ctx):
        if ctx.author.guild_permissions.administrator:
            await ctx.send(f"Hello {ctx.author.mention}, you have access to admin-only commands!")
        else:
            await ctx.send("You do not have permission to use this command.")

    @commands.command()
    async def trustedonly(self, ctx):
        if ctx.author.id in self.trusted_users:
            await ctx.send(f"Hello {ctx.author.mention}, you have access to trusted-only commands!")
        else:
            await ctx.send("You are not a trusted user.")

    @commands.command()
    async def addsandwich(self, ctx, user: nextcord.Member, amount: int):
        if ctx.author.guild_permissions.administrator or ctx.author.id in self.trusted_users:
            profile_cog = self.client.get_cog('ProfileCog')
            if profile_cog:
                profile_cog.add_tokens(str(user.id), amount)
                updated_user_data = profile_cog.get_user_data(str(user.id))
                await ctx.send(f"Added {amount} sandwich tokens to {user.mention}. New balance: {updated_user_data['tokens']}")
        else:
            await ctx.send("You do not have permission to use this command.")


    @commands.command()
    async def removesandwich(self, ctx, user: nextcord.Member, amount: int):
        if ctx.author.guild_permissions.administrator or ctx.author.id in self.trusted_users:
            profile_cog = self.client.get_cog('ProfileCog')
            if profile_cog:
                user_id = str(user.id)
                user_data = profile_cog.profiles.get(user_id, {})
                current_tokens = user_data.get('tokens', 0)
                user_data['tokens'] = max(current_tokens - amount, 0)
                profile_cog.save_profiles()
                await ctx.send(f"Removed {amount} sandwich tokens from {user.mention}. New balance: {user_data['tokens']}")
        else:
            await ctx.send("You do not have permission to use this command.")

    @commands.command()
    async def load(self, ctx, extension):
        if ctx.author.id in self.trusted_users or ctx.author.guild_permissions.administrator:
            self.client.load_extension(f'cogs.{extension}')
            await ctx.send(f'Loaded {extension}.')
        else:
            await ctx.send("You do not have permission to use this command.")

    @commands.command()
    async def unload(self, ctx, extension):
        if ctx.author.id in self.trusted_users or ctx.author.guild_permissions.administrator:
            self.client.unload_extension(f'cogs.{extension}')
            await ctx.send(f'Unloaded {extension}.')
        else:
            await ctx.send("You do not have permission to use this command.")

    @commands.command()
    async def reloadcog(self, ctx, extension):
        if ctx.author.id in self.trusted_users or ctx.author.guild_permissions.administrator:
            self.client.unload_extension(f'cogs.{extension}')
            self.client.load_extension(f'cogs.{extension}')
            await ctx.send(f'Reloaded {extension}.')
        else:
            await ctx.send("You do not have permission to use this command.")

    
    @commands.command(name="shutdown")
    @commands.has_permissions(administrator=True)  # optional, to ensure only administrators can use this
    async def shutdown(self, ctx):
        """Shutdown the bot"""
        await ctx.send("Shutting down...")
        await self.client.close()
        sys.exit(0)

    # .speak command
    @commands.command()
    async def speak(self, ctx):
        if not self.is_admin_or_trusted(ctx):
            await ctx.send("You do not have permission to use this command.")
            return
        self.thread_channel = await ctx.channel.create_thread(name='Admin Speak Thread')
        await ctx.send(f'Thread created: {self.thread_channel.mention}')

        
    # .post command to gather and post messages
    @commands.command()
    async def postl(self, ctx):
        if not self.is_admin_or_trusted(ctx):
            await ctx.send("You do not have permission to use this command.")
            return

        if not self.thread_channel:
            await ctx.send('No active thread to gather messages from.')
            return

        # Gather messages from the thread, excluding the .post command
        messages = await self.thread_channel.history(limit=200).flatten()
        messages_content = [msg.content for msg in messages if not msg.content.startswith('.post')]

        # Create an embedded message
        embed = nextcord.Embed(title='Thread Messages', description='\n'.join(messages_content), color=0x00ff00)

        # Asking for the destination channel
        await ctx.send('Please mention the channel to post the messages.')

        # Wait for the user to respond with a channel mention
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and len(m.channel_mentions) > 0

        try:
            response = await self.client.wait_for('message', check=check, timeout=60.0)
            destination_channel = response.channel_mentions[0]
            await destination_channel.send(embed=embed)
            
            # Close the thread channel
            await self.thread_channel.delete()

            # Inform the user that the messages have been posted and the thread is closed
            await ctx.send(f'Messages posted in {destination_channel.mention}. The thread has been closed.')

            await self.thread_channel.edit(archived=True)

            await ctx.send(f'M|essages posted in {destination_channel.mention} the thread has been closed ')



        except asyncio.TimeoutError:
            await ctx.send('You did not mention a channel in time.')




    # ... [other code]


    @load.error
    @unload.error
    @reloadcog.error
    @addtrusted.error
    @removetrusted.error
    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You do not have permission to use this command.")


def setup(client):
    client.add_cog(AdminCog(client))