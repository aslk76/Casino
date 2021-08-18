#!/usr/bin/env python3
# coding=utf-8
import os
import traceback
import logging
from datetime import datetime, timedelta, timezone
import discord
from discord.ext import commands, tasks
from discord.utils import get 
import aiomysql
import aiohttp
import asyncio
import socket
import collections
import requests
import json
import re
from dotenv import load_dotenv
from random import randint

from functions import *

running=False
lottery_tickets= []


load_dotenv()
token = os.getenv('DISCORD_TOKEN')
GUILD_ID = os.getenv('NOVA_ID')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = int(os.getenv('DB_PORT'))
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
OPS_DB = os.getenv('OPS_DB')
MPLUS_DB =  os.getenv("MPLUS_DB")
CASINO_DB =  os.getenv("CASINO_DB")

intents = discord.Intents().all()
class Casino_Bot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.mplus_pool = None
        self.ops_pool = None
        self.casino_pool = None
        self._resolver = aiohttp.AsyncResolver()
        self.help_pages = []

        # Use AF_INET as its socket family to prevent HTTPS related problems both locally
        # and in production.
        self._connector = aiohttp.TCPConnector(
            resolver=self._resolver,
            family=socket.AF_INET,
        )

        self.http.connector = self._connector
        self.http_session = aiohttp.ClientSession(connector=self._connector)


    async def logout(self):
        """|coro|
        Logs out of Discord and closes all connections.
        """
        try:
            if self.mplus_pool:
                self.mplus_pool.close()
                await self.mplus_pool.wait_closed()
            if self.ops_pool:
                self.ops_pool.close()
                await self.ops_pool.wait_closed()
        finally:
            await super().logout()

bot = Casino_Bot(command_prefix=commands.when_mentioned_or('g!'), case_insensitive=True, intents=intents)

logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename='/NOVA/NOVA_Casino/NOVA_Casino.log', encoding='utf-8', mode='a')
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s'))
logger.addHandler(handler)


async def checkPers(id :int):
    async with bot.mplus_pool.acquire() as conn:
        async with conn.cursor() as cursor:
            query = """
                SELECT name , serv FROM persdict WHERE discord_id = %s
            """
            val = (id,)
            await cursor.execute(query,val)
            result = await cursor.fetchone()
            if result is not None:
                name = result[0]
                realm = result[1]
            else:
                name = None
                realm = None
    return (name, realm)


@bot.event
async def on_error(event, *args, **kwargs):
    logger.error(f"========On {event} error START=======")
    s = traceback.format_exc()
    content = f'Ignoring exception in {event}\n{s}'
    logger.error(content)
    logger.error(f"========On {event} error END=========")
    guild = bot.get_guild(GUILD_ID)
    bot_log_channel = get(guild.text_channels, name='bot-logs')
    embed_bot_log = discord.Embed(
        title=f"{bot.user.name} Error Log.", 
        description=event, 
        color=discord.Color.blue())
    embed_bot_log.set_footer(text=datetime.now(timezone.utc).replace(microsecond=0))
    await bot_log_channel.send(embed=embed_bot_log)


@bot.event
async def on_command_error(ctx, error):
    if (isinstance(error, commands.MissingRole) or 
        isinstance(error, commands.MissingAnyRole)):
        em = discord.Embed(title="❌ Missing permissions",
                           description="You don't have permission to use this command",
                           color=discord.Color.red())
        await ctx.send(embed=em, delete_after=10)
    elif isinstance(error, commands.CommandNotFound):
        em = discord.Embed(title="❌ No Such Command",
                           description="",
                           color=discord.Color.red())
        await ctx.send(embed=em, delete_after=5)
    elif isinstance(error, commands.BadArgument):
        em = discord.Embed(title="❌ Bad arguments",
                           description=error,
                           color=discord.Color.red())
        await ctx.send(embed=em, delete_after=5)
    elif isinstance(error, commands.MissingRequiredArgument):
        em = discord.Embed(title="❌ Missing arguments",
                           description=error,
                           color=discord.Color.red())
        await ctx.send(embed=em, delete_after=10)
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.message.delete()
        em = discord.Embed(title="❌ On Cooldown",
                           description=f"{ctx.command.name} is on cooldown, please try again in {error.retry_after:.2f}s",
                           color=discord.Color.red())
        await ctx.send(embed=em, delete_after=5)
    logger.error(f"========on {ctx.command.name} START=======")
    logger.error(f"traceback: {traceback.format_exc()}")
    logger.error(f"error: {error}")
    logger.error(f"========on {ctx.command.name} END=========")
    bot_log_channel = get(ctx.guild.text_channels, name='bot-logs')
    embed_bot_log = discord.Embed(
        title=f"{ctx.bot.user.name} Error Log.",
        description=f"on {ctx.command.name}",
        color=discord.Color.blue())
    embed_bot_log.set_footer(text=datetime.now(timezone.utc).replace(microsecond=0, tzinfo=None))
    await bot_log_channel.send(embed=embed_bot_log)


@bot.event
async def on_ready():
    global running
    if running==False:
        logger.info(f'{bot.user.name} {discord.__version__} has connected to Discord!')
        guild = await bot.fetch_guild(GUILD_ID)
        bot_log_channel = await bot.fetch_channel(817552283209433098)
        embed_bot_log = discord.Embed(
            title="Info Log.", 
            description=f"{bot.user.name} {discord.__version__} has connected to Discord!",
            color=0x5d4991)
        embed_bot_log.set_footer(text=datetime.now(timezone.utc).replace(microsecond=0))
        await bot_log_channel.send(embed=embed_bot_log)
        running=True


@bot.command()
@commands.has_any_role('Moderator')
async def Logout(ctx):
    await ctx.message.delete()
    await ctx.bot.logout()


@bot.command()
@commands.cooldown(3, 20, commands.BucketType.channel)
async def bet(ctx, target_user : discord.Member, pot):
    """example: g!bet @ASLK76#2188 100K
    """
    try:
        await ctx.message.delete()
        pot = convert_si_to_number(pot)
        if ctx.channel.id != 815104636708323332:
            await ctx.send("You can only gamble in <#815104636708323332>")
        elif ctx.author==target_user:
            em = discord.Embed(title="❌ Can't bet against your self",
                                description="Unless you can duplicate your self IRL!",
                                color=discord.Color.red())
            await ctx.send(embed=em, delete_after=5)
        elif pot<1000 or pot == None:
            em = discord.Embed(title="❌ Bet too low",
                                description="The minimum amount for betting is 1000 !",
                                color=discord.Color.red())
            await ctx.send(embed=em, delete_after=5)
        else:
            gamble_embed=discord.Embed(title="💰Gamble info💰", description="", color=0x4feb1c)
            gamble_embed.set_thumbnail(
                url="https://cdn.discordapp.com/avatars/634917649335320586/ea303e8b580d56ff6837e256b1df6ef6.png")
            gamble_embed.add_field(name="**Initiated By: **", 
                value=ctx.author.mention, inline=True)
            gamble_embed.add_field(name="**Against: **", 
                value=target_user.mention, inline=True)
            gamble_embed.add_field(name="**For the amount of: **", 
                value=f"{pot:,d}", inline=True)
            gamble_embed.set_footer(text=f"Timestamp: {datetime.now(timezone.utc).replace(microsecond=0)}")
            gamble_msg = await ctx.send(embed=gamble_embed)
            gamble_msg_embed = gamble_msg.embeds[0].to_dict()

            name, realm = await checkPers(ctx.author.id)
            if name is not None:
                gambler1 = f"{name}-{realm}"
            else:
                if "-" not in ctx.author.nick:
                    em = discord.Embed(title="❌",
                        description=f"Nickname format not correct for {ctx.author}",
                        color=discord.Color.red())
                    await ctx.send(embed=em, delete_after=5)
                    await gamble_msg.delete()
                    raise ValueError(f"Nickname format not correct for {ctx.author}")
                gambler1 = ctx.author.nick

            name, realm = await checkPers(target_user.id)
            if name is not None:
                gambler2 = f"{name}-{realm}"
            else:
                if "-" not in target_user.nick:
                    em = discord.Embed(title="❌",
                        description=f"Nickname format not correct for {target_user}",
                        color=discord.Color.red())
                    await ctx.send(embed=em, delete_after=5)
                    await gamble_msg.delete()
                    raise ValueError(f"Nickname format not correct for {target_user}")
                gambler2 = target_user.nick
            
            async with ctx.bot.casino_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    query = """
                        SELECT COALESCE((
                            SELECT cur_balance 
                            FROM `nova_mplus`.`ov_creds`
                            WHERE booster = %s
                            ),0) cb
                    """
                    val = (gambler1,)
                    await cursor.execute(query, val)
                    (gambler1_balance,) = await cursor.fetchone()

                    query = """
                        SELECT COALESCE((
                            SELECT cur_balance 
                            FROM `nova_mplus`.`ov_creds` 
                            WHERE booster = %s
                            ),0) cb
                    """
                    val = (gambler2,)
                    await cursor.execute(query, val)
                    (gambler2_balance,) = await cursor.fetchone()
            
                    if gambler1_balance < pot:
                        gamble_msg_embed['color'] = 0xff0000
                        gamble_msg_embed['title'] = f"💰Gamble info💰 TOTAL POT: {pot*2:,d}"
                        not_enough_bal = discord.Embed.from_dict(gamble_msg_embed)
                        not_enough_bal.add_field(
                            name = "❌NOT ENOUGH BALANCE❌", 
                            value = (
                                f"{ctx.author.mention} doesn't have enough balance to cover the bet, "
                                "bet is cancelled!"), 
                            inline = False)
                        await gamble_msg.edit(embed=not_enough_bal)
                        await gamble_msg.add_reaction(u"\u274C")
                    elif gambler2_balance < pot:
                        gamble_msg_embed['color'] = 0xff0000
                        gamble_msg_embed['title'] = f"💰Gamble info💰 TOTAL POT: {pot*2:,d}"
                        not_enough_bal = discord.Embed.from_dict(gamble_msg_embed)
                        not_enough_bal.add_field(
                            name = "❌NOT ENOUGH BALANCE❌", 
                            value = (
                                f"{target_user.mention} doesn't have enough balance to cover the bet, "
                                "bet is cancelled!"), 
                            inline = False)
                        await gamble_msg.edit(embed=not_enough_bal)
                        await gamble_msg.add_reaction(u"\u274C")
                    else:
                        await gamble_msg.add_reaction(u"\U0001F44D")
                        def check(reaction, user):
                            m = gamble_msg
                            return user == target_user and str(reaction.emoji) == '👍' and m.id == reaction.message.id

                        try:
                            reaction, user = await bot.wait_for('reaction_add', timeout=15.0, check=check)
                        except asyncio.TimeoutError:
                            gamble_msg_embed['color'] = 0xff0000
                            gamble_msg_embed['title'] = f"💰Gamble info💰 TOTAL POT: {pot*2:,d}"
                            time_out = discord.Embed.from_dict(gamble_msg_embed)
                            time_out.add_field(
                                name = "❌TIME OUT❌", 
                                value = (
                                    f"{target_user.mention} didn't respond in time, "
                                    "bet is cancelled!"), 
                                inline = False)
                            await gamble_msg.edit(embed=time_out)
                            await gamble_msg.clear_reaction(u"\U0001F44D")
                            await gamble_msg.add_reaction(u"\u274C")
                        else:
                            now = datetime.now(timezone.utc).replace(microsecond=0, tzinfo=None)
                            gambler1_roll = randint(1, 6)
                            gambler2_roll = randint(1, 6)
                            if gambler1_roll > gambler2_roll:
                                gamble_winner = gambler1
                                gamble_loser = gambler2
                                async with ctx.bot.mplus_pool.acquire() as conn:
                                    async with conn.cursor() as cursor:
                                        winner_pot = str(((pot*2) - (pot*2*0.05))).replace('.','').replace(',','')
                                        query = """
                                           INSERT INTO balance_ops
                                                (operation_id, date, name, realm, operation, command, reason, amount, author)
                                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                        """
                                        val = (ctx.message.id, now, gamble_winner.split("-")[0], gamble_winner.split("-")[1], 'Add', 'Casino', 'Casino bet win', winner_pot, 'NOVA_Casino')
                                        await cursor.execute(query, val)
                                        loser_pot = str(pot).replace('.','').replace(',','')
                                        query = """
                                           INSERT INTO balance_ops
                                                (operation_id, date, name, realm, operation, command, reason, amount, author)
                                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                        """
                                        val = (ctx.message.id, now, gamble_loser.split("-")[0], gamble_loser.split("-")[1], 'Deduction', 'Casino', 'Casino bet lose', loser_pot, 'NOVA_Casino')
                                        await cursor.execute(query, val)
                                gamble_msg_embed['color'] = 0x00ff00
                                gamble_msg_embed['title'] = f"💰Gamble info💰 TOTAL POT: {pot*2:,d}"
                                dice_roll_embed = discord.Embed.from_dict(gamble_msg_embed)
                                dice_roll_embed.add_field(
                                    name = "Roll Results:", 
                                    value = (
                                        f"{ctx.author.mention} 🎲{gambler1_roll} \n"
                                        f"{target_user.mention} 🎲{gambler2_roll}"), inline = False)
                                dice_roll_embed.add_field(
                                    name = "Winner is: ", 
                                    value = gamble_winner, inline = True)
                                dice_roll_embed.add_field(
                                    name = "Win Amount: ", 
                                    value = f"{(pot*2) - (pot*2*0.05):,.0f}", inline = True)
                                dice_roll_embed.add_field(name = "--", value = "--" , inline = False)
                                dice_roll_embed.add_field(
                                    name = "Loser is: ", 
                                    value = gamble_loser, inline = True)
                                dice_roll_embed.add_field(name="Loss Amount: ", value = f"{pot:,d}", inline=True)

                                query = """
                                    INSERT INTO gambling_log 
                                        (date, pot, name) 
                                    VALUES (%s, %s, %s)
                                """
                                val = [(now,pot-pot*0.1,gamble_winner),(now,-pot,gamble_loser)]
                                await cursor.executemany(query,val)

                                await gamble_msg.edit(embed=dice_roll_embed)
                                await gamble_msg.add_reaction(u"\U0001F4AF")

                            elif gambler2_roll>gambler1_roll:
                                gamble_winner=gambler2
                                gamble_loser=gambler1
                                async with ctx.bot.mplus_pool.acquire() as conn:
                                    async with conn.cursor() as cursor:
                                        winner_pot = str(((pot*2) - (pot*2*0.05))).replace('.','').replace(',','')
                                        query = """
                                           INSERT INTO balance_ops
                                                (operation_id, date, name, realm, operation, command, reason, amount, author)
                                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                        """
                                        val = (ctx.message.id, now, gamble_winner.split("-")[0], gamble_winner.split("-")[1], 'Add', 'Casino', 'Casino bet win', winner_pot, 'NOVA_Casino')
                                        await cursor.execute(query, val)
                                        loser_pot = str(pot).replace('.','').replace(',','')
                                        query = """
                                           INSERT INTO balance_ops
                                                (operation_id, date, name, realm, operation, command, reason, amount, author)
                                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                        """
                                        val = (ctx.message.id, now, gamble_loser.split("-")[0], gamble_loser.split("-")[1], 'Deduction', 'Casino', 'Casino bet lose', loser_pot, 'NOVA_Casino')
                                        await cursor.execute(query, val)
                                gamble_msg_embed['color'] = 0x00ff00
                                gamble_msg_embed['title'] = f"💰Gamble info💰 TOTAL POT: {pot*2:,d}"
                                dice_roll_embed = discord.Embed.from_dict(gamble_msg_embed)
                                dice_roll_embed.add_field(
                                    name = "Roll Results:", 
                                    value = (
                                        f"{ctx.message.author.mention} 🎲{gambler1_roll} \n"
                                        f"{target_user.mention} 🎲{gambler2_roll}"), inline = False)
                                dice_roll_embed.add_field(
                                    name = "Winner is: ", 
                                    value = gamble_winner, inline = True)
                                dice_roll_embed.add_field(
                                    name = "Win Amount: ", 
                                    value = f"{(pot*2) - (pot*2*0.05):,.0f}", inline = True)
                                dice_roll_embed.add_field(name = "--", value = "--" , inline = False)
                                dice_roll_embed.add_field(
                                    name = "Loser is: ", 
                                    value = gamble_loser, inline = True)
                                dice_roll_embed.add_field(name="Loss Amount: ", value = f"{pot:,d}", inline=True)

                                query = """
                                    INSERT INTO gambling_log 
                                        (date, pot, name) 
                                    VALUES (%s, %s, %s)
                                """
                                val = [(now,pot-pot*0.1,gamble_winner),(now,-pot,gamble_loser)]
                                await cursor.executemany(query,val)

                                await gamble_msg.edit(embed=dice_roll_embed)
                                await gamble_msg.add_reaction(u"\U0001F4AF")

                            else:
                                gamble_msg_embed['color'] = 0x0000ff
                                gamble_msg_embed['title'] = f"💰Gamble info💰 TOTAL POT: {pot*2:,d}"
                                dice_roll_embed = discord.Embed.from_dict(gamble_msg_embed)
                                dice_roll_embed.add_field(
                                    name = "Roll Results:", 
                                    value = (
                                        f"{ctx.author.mention} 🎲{gambler1_roll} \n" 
                                        f"{target_user.mention} 🎲{gambler2_roll}"), inline=True)
                                dice_roll_embed.add_field(name="Winner is: ", 
                                    value= "Tie, no balance changes!", inline=False)
                                await gamble_msg.edit(embed=dice_roll_embed)
                                await gamble_msg.add_reaction(u"\U0001F4AF")
    except Exception:
        logger.error(f"========on bet START=======")
        logger.error(traceback.format_exc())
        logger.error(f"========on bet END=========")


@bot.command()
@commands.cooldown(3, 20, commands.BucketType.channel)
async def betAnyone(ctx, pot):
    """example: g!bet 100K
    """
    try:
        await ctx.message.delete()
        pot = convert_si_to_number(pot)
        if ctx.message.channel.id != 815104636708323332:
            await ctx.message.channel.send("You can only gamble in <#815104636708323332>")
        elif pot<1000 or pot == None:
            em = discord.Embed(title="❌ Bet too low",
                                description="The minimum amount for betting is 1000 !",
                                color=discord.Color.red())
            await ctx.message.channel.send(embed=em, delete_after=5)
        else:
            gamble_embed=discord.Embed(title="💰Gamble info💰", description="", color=0x4feb1c)
            gamble_embed.set_thumbnail(
                url="https://cdn.discordapp.com/avatars/634917649335320586/ea303e8b580d56ff6837e256b1df6ef6.png")
            gamble_embed.add_field(name="**Initiated By: **", 
                value=ctx.author.mention, inline=True)
            gamble_embed.add_field(name="**For the amount of: **", 
                value=f"{pot:,d}", inline=True)
            gamble_embed.set_footer(text=f"Timestamp: {datetime.now(timezone.utc).replace(microsecond=0)}")
            gamble_msg = await ctx.message.channel.send(embed=gamble_embed)
            gamble_msg_embed = gamble_msg.embeds[0].to_dict()
            
            await gamble_msg.add_reaction(u"\U0001F44D")
            def check(reaction, user):
                m = gamble_msg
                return str(reaction.emoji) == '👍' and m.id == reaction.message.id and not user.bot

            try:
                reaction, user = await bot.wait_for('reaction_add', timeout=15.0, check=check)
            except asyncio.TimeoutError:
                gamble_msg_embed['color'] = 0xff0000
                gamble_msg_embed['title'] = f"💰Gamble info💰 TOTAL POT: {pot*2:,d}"
                time_out = discord.Embed.from_dict(gamble_msg_embed)
                time_out.add_field(name = "❌TIME OUT❌", 
                    value = "No one responded in time, bet is cancelled!", inline = False)
                await gamble_msg.edit(embed=time_out)
                await gamble_msg.clear_reaction(u"\U0001F44D")
                await gamble_msg.add_reaction(u"\u274C")
            else:
                name, realm = await checkPers(ctx.author.id)
                if name is not None:
                    gambler1 = f"{name}-{realm}"
                else:
                    if "-" not in ctx.author.nick:
                        em = discord.Embed(title="❌",
                            description=f"Nickname format not correct for {ctx.author}",
                            color=discord.Color.red())
                        await ctx.send(embed=em, delete_after=5)
                        await gamble_msg.delete()
                        raise ValueError(f"Nickname format not correct for {ctx.author}")
                    gambler1 = ctx.author.nick

                name, realm = await checkPers(user.id)
                if name is not None:
                    gambler2 = f"{name}-{realm}"
                else:
                    if "-" not in user.nick:
                        em = discord.Embed(title="❌",
                            description=f"Nickname format not correct for {user}",
                            color=discord.Color.red())
                        await ctx.send(embed=em, delete_after=5)
                        await gamble_msg.delete()
                        raise ValueError(f"Nickname format not correct for {user}")
                    gambler2 = user.nick
                        
                if gambler1==gambler2:
                    em = discord.Embed(title="❌ Can't bet against your self",
                            description="Unless you can duplicate your self IRL!",
                            color=discord.Color.red())
                    await ctx.send(embed=em, delete_after=5)
                    await gamble_msg.delete()
                else:
                    async with ctx.bot.casino_pool.acquire() as conn:
                        async with conn.cursor() as cursor:
                            query = """
                                SELECT COALESCE((
                                    SELECT cur_balance 
                                    FROM `nova_mplus`.`ov_creds` 
                                    WHERE booster = %s
                                    ),0) cb
                            """
                            val = (gambler1,)
                            await cursor.execute(query, val)
                            (gambler1_balance,) = await cursor.fetchone()

                            query = """
                                SELECT COALESCE((
                                    SELECT cur_balance 
                                    FROM `nova_mplus`.`ov_creds` 
                                    WHERE booster = %s
                                    ),0) cb
                            """
                            val = (gambler2,)
                            await cursor.execute(query, val)
                            (gambler2_balance,) = await cursor.fetchone()

                            if gambler1_balance < pot:
                                gamble_msg_embed['color'] = 0xff0000
                                gamble_msg_embed['title'] = f"💰Gamble info💰 TOTAL POT: {pot*2:,d}"
                                not_enough_bal = discord.Embed.from_dict(gamble_msg_embed)
                                not_enough_bal.add_field(
                                    name = "❌NOT ENOUGH BALANCE❌", 
                                    value = (
                                        f"{ctx.author.mention} doesn't have enough balance to cover the bet, "
                                        "bet is cancelled!"), 
                                    inline = False)
                                await gamble_msg.edit(embed=not_enough_bal)
                                await gamble_msg.clear_reaction(u"\U0001F44D")
                                await gamble_msg.add_reaction(u"\u274C")
                            elif gambler2_balance < pot:
                                gamble_msg_embed['color'] = 0xff0000
                                gamble_msg_embed['title'] = f"💰Gamble info💰 TOTAL POT: {pot*2:,d}"
                                not_enough_bal = discord.Embed.from_dict(gamble_msg_embed)
                                not_enough_bal.add_field(
                                    name = "❌NOT ENOUGH BALANCE❌", 
                                    value = (
                                        f"{user.mention} doesn't have enough balance to cover the bet, "
                                        "bet is cancelled!"), 
                                    inline = False)
                                await gamble_msg.edit(embed=not_enough_bal)
                                await gamble_msg.clear_reaction(u"\U0001F44D")
                                await gamble_msg.add_reaction(u"\u274C")
                            else:
                                now = datetime.now(timezone.utc).replace(microsecond=0, tzinfo=None)
                                gambler1_roll = randint(1, 6)
                                gambler2_roll = randint(1, 6)
                                if gambler1_roll>gambler2_roll:
                                    gamble_winner=gambler1
                                    gamble_loser=gambler2

                                    gamble_msg_embed['color'] = 0x00ff00
                                    gamble_msg_embed['title'] = f"💰Gamble info💰 TOTAL POT: {pot*2:,d}"
                                    dice_roll_embed = discord.Embed.from_dict(gamble_msg_embed)
                                    dice_roll_embed.add_field(
                                        name = "Roll Results:", 
                                        value = (
                                            f"{ctx.author.mention} 🎲{gambler1_roll} \n"
                                            f"{user.mention} 🎲{gambler2_roll}"), inline = False)
                                    dice_roll_embed.add_field(
                                        name = "Winner is: ", 
                                        value = gamble_winner, inline = True)
                                    dice_roll_embed.add_field(
                                        name = "Win Amount: ", 
                                        value = f"{(pot*2) - (pot*2*0.05):,.0f}", inline = True)
                                    dice_roll_embed.add_field(name = "--", value = "--" , inline = False)
                                    dice_roll_embed.add_field(
                                        name = "Loser is: ", 
                                        value = gamble_loser, inline = True)
                                    dice_roll_embed.add_field(name="Loss Amount: ", value = f"{pot:,d}", inline=True)
                                    
                                    query = """
                                        INSERT INTO gambling_log 
                                            (date, pot, name) 
                                        VALUES (%s, %s, %s)
                                    """
                                    val = [(now,pot-pot*0.1,gamble_winner),(now,-pot,gamble_loser)]
                                    await cursor.executemany(query,val)

                                    await gamble_msg.edit(embed=dice_roll_embed)
                                    await gamble_msg.add_reaction(u"\U0001F4AF")
                                    
                                elif gambler2_roll>gambler1_roll:
                                    gamble_winner=gambler2
                                    gamble_loser=gambler1
                                    
                                    gamble_msg_embed['color'] = 0x00ff00
                                    gamble_msg_embed['title'] = f"💰Gamble info💰 TOTAL POT: {pot*2:,d}"
                                    dice_roll_embed = discord.Embed.from_dict(gamble_msg_embed)
                                    dice_roll_embed.add_field(
                                        name = "Roll Results:", 
                                        value = (
                                            f"{ctx.author.mention} 🎲{gambler1_roll} \n"
                                            f"{user.mention} 🎲{gambler2_roll}"), inline = False)
                                    dice_roll_embed.add_field(
                                        name = "Winner is: ", 
                                        value = gamble_winner, inline = True)
                                    dice_roll_embed.add_field(
                                        name = "Win Amount: ", 
                                        value = f"{(pot*2) - (pot*2*0.05):,.0f}", inline = True)
                                    dice_roll_embed.add_field(name = "--", value = "--" , inline = False)
                                    dice_roll_embed.add_field(
                                        name = "Loser is: ", 
                                        value = gamble_loser, inline = True)
                                    dice_roll_embed.add_field(name="Loss Amount: ", value = f"{pot:,d}", inline=True)
                                    
                                    query = """
                                        INSERT INTO gambling_log 
                                            (date, pot, name) 
                                        VALUES (%s, %s, %s)
                                    """
                                    val = [(now,pot-pot*0.1,gamble_winner),(now,-pot,gamble_loser)]
                                    await cursor.executemany(query,val)

                                    await gamble_msg.edit(embed=dice_roll_embed)
                                    await gamble_msg.add_reaction(u"\U0001F4AF")
                                else:
                                    gamble_msg_embed['color'] = 0x0000ff
                                    gamble_msg_embed['title'] = f"💰Gamble info💰 TOTAL POT: {pot*2:,d}"
                                    dice_roll_embed = discord.Embed.from_dict(gamble_msg_embed)
                                    dice_roll_embed.add_field(
                                        name = "Roll Results:", 
                                        value = (
                                            f"{ctx.author.mention} 🎲{gambler1_roll} \n" 
                                            f"{user.mention} 🎲{gambler2_roll}"), inline=True)
                                    dice_roll_embed.add_field(name="Winner is: ", 
                                        value= "Tie, no balance changes!", inline=False)
                                    await gamble_msg.edit(embed=dice_roll_embed)
                                    await gamble_msg.add_reaction(u"\U0001F4AF")
    except Exception:
        logger.error(f"========on betAnyone START=======")
        logger.error(traceback.format_exc())
        logger.error(f"========on betAnyone END=========")


@bot.command()
@commands.cooldown(2, 20, commands.BucketType.channel)
async def lottery(ctx):
    """example: g!lottery
    """
    await ctx.message.delete()
    lottery_channel = get(ctx.guild.text_channels, id=815104636708323331)
    if ctx.message.channel.id != 815104636708323331:
        await ctx.message.channel.send("You can only buy a ticket in <#815104636708323331>")
    else:
        name, realm = await checkPers(ctx.author.id)
        if name is not None:
            lottery_user = f"{name}-{realm}"
        else:
            if "-" not in ctx.author.nick:
                em = discord.Embed(title="❌",
                    description=f"Nickname format not correct for {ctx.author}",
                    color=discord.Color.red())
                await ctx.send(embed=em, delete_after=5)
                raise ValueError(f"Nickname format not correct for {ctx.author}")
            lottery_user = ctx.author.nick

        async with ctx.bot.casino_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                query = """
                    SELECT COALESCE((
                        SELECT cur_balance 
                        FROM `nova_mplus`.`ov_creds` 
                        WHERE booster = %s
                        ),0) cb
                """
                val = (lottery_user,)
                await cursor.execute(query, val)
                (lottery_user_balance,) = await cursor.fetchone()
                    
                query = "SELECT name FROM lottery_log WHERE name = %s"
                val = (lottery_user,)
                await cursor.execute(query, val)
                (lottery_result,) = await cursor.fetchone()


                if lottery_result > 0:
                    em = discord.Embed(title="❌",
                        description=
                            f"{ctx.message.author.mention} you already have lottery ticket, "
                            "***1*** ticket per member __only__.",
                        color=discord.Color.red())
                    await ctx.send(embed=em, delete_after=5)
                elif lottery_user_balance < 50000:
                    em = discord.Embed(title="❌",
                        description=
                            f"{ctx.author.mention} you don't have enough balance to buy a ticket.",
                        color=discord.Color.red())
                    await ctx.send(embed=em, delete_after=5)
                else:
                    now = datetime.now(timezone.utc).replace(microsecond=0, tzinfo=None)
                    lottery_user_balance = lottery_user_balance - 50000
                    
                    query = """
                        INSERT INTO lottery_log (date, pot, name) 
                        VALUES (%s, %s, %s)
                    """
                    val = (now,-50000,lottery_user)
                    await cursor.execute(query,val)
                    
                    query = """SELECT COALESCE((
                        SELECT ABS(SUM(pot)) FROM `nova_casino`.`lottery_log` 
                        WHERE `date` BETWEEN 
                            (SELECT cur1 FROM `nova_mplus`.`variables` WHERE id = 1) AND 
                            (SELECT cur2 FROM `nova_mplus`.`variables` WHERE id = 1)),0)
                    """
                    await cursor.execute(query)
                    (lottery_pot,) = await cursor.fetchone()
                    async for message in lottery_channel.history(limit=50, oldest_first=True):
                        if message.id == 847745930563944468:
                            lottery_msg = message
                            lottery_embed_pre = message.embeds[0].to_dict()
                            lottery_embed_pre_fields = lottery_embed_pre['fields']
                            lottery_embed_pre_fields[1]["value"]= f"{lottery_pot:,d}"
                            lottery_update_embed = discord.Embed.from_dict(lottery_embed_pre)
                    await ctx.message.channel.send(
                        f"{ctx.message.author.mention} ticket purchased, good luck", 
                        delete_after=10)
                    await lottery_msg.edit(embed=lottery_update_embed)


@bot.command()
@commands.has_any_role('Moderator')
async def sendEmbed(ctx):
    await ctx.message.delete()
    lottery_embed=discord.Embed(title="💰Lottery info💰", description="", color=0x4feb1c)
    lottery_embed.set_thumbnail(
        url="https://cdn.discordapp.com/avatars/634917649335320586/ea303e8b580d56ff6837e256b1df6ef6.png")
    lottery_embed.add_field(name="**Current Ticket price: **", value="50K", inline=True)
    lottery_embed.add_field(name="**Current Prize Pool: **", value="--", inline=False)
    await ctx.message.channel.send(embed=lottery_embed)


@bot.command()
@commands.has_any_role('Moderator')
async def resetEmbed(ctx, price: str):
    await ctx.message.delete()
    lottery_channel = get(ctx.guild.text_channels, id=815104636708323331)
    async for message in lottery_channel.history(limit=50, oldest_first=True):
        if message.id == 847745930563944468:
            lottery_msg = message
            lottery_embed_pre = message.embeds[0].to_dict()
            lottery_embed_pre_fields = lottery_embed_pre['fields']
            lottery_embed_pre_fields[0]["value"]= price
            lottery_embed_pre_fields[1]["value"]= "--"
            lottery_update_embed = discord.Embed.from_dict(lottery_embed_pre)
    await lottery_msg.edit(embed=lottery_update_embed)


@bot.command()
@commands.has_any_role('Moderator')
async def pickWinners(ctx):
    async with ctx.bot.casino_pool.acquire() as conn:
        async with conn.cursor() as cursor:
            query = """
                SELECT `name` 
                FROM `nova_casino`.`lottery_log` 
                WHERE	`date` BETWEEN 
                    (SELECT cur1 FROM `nova_mplus`.`variables` WHERE id = 1) AND 
                    (SELECT cur2 FROM `nova_mplus`.`variables` WHERE id = 1)
                ORDER BY RAND()
                LIMIT 3;
            """
            await cursor.execute(query)
            winners_list = await cursor.fetchall()
            
            query = """SELECT COALESCE((
                SELECT ABS(SUM(pot)) FROM `nova_casino`.`lottery_log` 
                WHERE `date` BETWEEN 
                    (SELECT cur1 FROM `nova_mplus`.`variables` WHERE id = 1) AND 
                    (SELECT cur2 FROM `nova_mplus`.`variables` WHERE id = 1)),0)
            """
            await cursor.execute(query)
            (lottery_pot,) = await cursor.fetchone()

            lottery_winner_1 = get(ctx.guild.members, nick=' '.join(map(str,winners_list[0])))
            lottery_winner_2 = get(ctx.guild.members, nick=' '.join(map(str,winners_list[1])))
            lottery_winner_3 = get(ctx.guild.members, nick=' '.join(map(str,winners_list[2])))
            lottery_embed=discord.Embed(title="💰Lottery winners💰", description="", color=0x4feb1c)
            lottery_embed.set_thumbnail(
                url="https://cdn.discordapp.com/avatars/634917649335320586/ea303e8b580d56ff6837e256b1df6ef6.png")
            lottery_embed.add_field(name="🥇", 
                value=
                    f"**First place:** {lottery_winner_1.mention} "
                    f"<:goldss:817570131193888828> {int(lottery_pot*65/100):,d}", inline=True)
            lottery_embed.add_field(name="🥈", 
                value=
                    f"**Second place:** {lottery_winner_2.mention} "
                    f"<:goldss:817570131193888828> {int(lottery_pot*15/100):,d}", inline=False)
            lottery_embed.add_field(name="🥉", 
                value=
                    f"**Third place:** {lottery_winner_3.mention} "
                    f"<:goldss:817570131193888828> {int(lottery_pot*5/100):,d}", inline=False)
            lottery_embed.set_footer(text=f"Timestamp  {datetime.now(timezone.utc).replace(microsecond=0)}")
            await ctx.message.channel.send(embed=lottery_embed)


async def start_bot():
    mplus_pool = await aiomysql.create_pool(host=DB_HOST, port=DB_PORT,
                            user=DB_USER, password=DB_PASSWORD,
                            db=MPLUS_DB, autocommit=True)

    ops_pool = await aiomysql.create_pool(host=DB_HOST, port=DB_PORT,
                            user=DB_USER, password=DB_PASSWORD,
                            db=OPS_DB, autocommit=True)

    casino_pool = await aiomysql.create_pool(host=DB_HOST, port=DB_PORT,
                            user=DB_USER, password=DB_PASSWORD,
                            db=CASINO_DB, autocommit=True)

    bot.mplus_pool = mplus_pool
    bot.ops_pool = ops_pool
    bot.casino_pool = casino_pool

    await bot.start(token)

try:
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_bot())
except Exception as e:
    logger.warning("Exception raised from main thread.")
    logger.exception(e)