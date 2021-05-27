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
import random

from constants import *
from functions import *

running=False
lottery_tickets= []


load_dotenv()
token = os.getenv('DISCORD_TOKEN')
GUILD_ID = os.getenv('NOVA_ID')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
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

bot = commands.Casino_Bot(command_prefix=commands.when_mentioned_or('g!'), case_insensitive=True, intents=intents)

logging.basicConfig(filename='/NOVA/Gamble_Bot/Casino.log', level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')





@bot.event
async def on_ready():
    #global alliance_counter_lottery, alliance_counter_init_lottery
    global running
    try:
        if running==False:
            await asyncio.sleep (3)
            guild = get(bot.guilds, name="Nova Boosting Community")
            bot_log_channel = get(guild.text_channels, name='bot-logs')
            embed_bot_log = discord.Embed(title="Info Log.", description=f"{bot.user.name} {discord.__version__} has connected to Discord!",
                                          color=0x5d4991)
            embed_bot_log.set_footer(text=datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S"))
            await bot_log_channel.send(embed=embed_bot_log)
            #alliance_counter_init_lottery = alliance_find_empty_cell_lottery(alliance_lottery_sheet)
            #if int(alliance_counter_init_lottery) > int(alliance_counter_lottery):
            #    alliance_counter_lottery = alliance_counter_init_lottery
            #ImportBalance_loop.start()
            bot.loop.create_task(balanceSync(agcm))
            running=True
    except Exception:
        logging.error(traceback.format_exc())
        bot_log_channel = get(guild.text_channels, name='bot-logs')
        embed_bot_log = discord.Embed(title="Casino Error Log.", description=traceback.format_exc(), color=discord.Color.orange())
        embed_bot_log.add_field(name="Source", value="on ready", inline=True)
        embed_bot_log.set_footer(text=datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S"))
        await bot_log_channel.send(embed=embed_bot_log)
    
@bot.command(pass_context=True)
@commands.has_any_role('Moderator')
async def Logout(ctx):
    await ctx.message.delete()
    await ctx.bot.logout()
    
@bot.command(pass_context=True)
@commands.has_any_role('Moderator')
async def ImportToDB(ctx):
    all_members = ctx.guild.members
    i=0
    val=[]  
    for member in all_members:
        if not member.bot and get(ctx.guild.roles, name="Client") not in member.roles and \
            get(ctx.guild.roles, name="Client NA") not in member.roles and get(ctx.guild.roles, name="PickYourRegion") not in member.roles:
            for key in persdict:
                if key == member.id:
                    member_toDB = persdict[member.id]['name'] + '-' + persdict[member.id]['serv']
                    break
            else:
                member_toDB = member.nick
            val.append([member_toDB,"0"])
            i+=1
    cnx = mysql.connector.connect(
        host="128.199.48.106",
        port="3306",
        user="nova",
        passwd="DiscordNovaP@ssw0rd@qais",
        database="nova_casino"
    )
    cursor = cnx.cursor()
    query = "INSERT INTO gambling_prod (name, balance) VALUES (%s, %s) ON DUPLICATE KEY UPDATE name=name,balance=balance"
    cursor.executemany(query,val)
    #val = (member_toDB,"0")
    #cursor.execute(query,val)
    cnx.commit()
    cursor.close()
    cnx.close()
    bot_log_channel = get(ctx.guild.text_channels, name='bot-logs')
    await bot_log_channel.send(f"All {i} Users Imported to the DB")

@bot.command(pass_context=True)
@commands.has_any_role('Moderator')
async def ImportBalance(ctx):
    try:
        
        alliance_rich_names = [item for item in alliance_coreData_sheet.col_values(172) if item] #FP Col Names
        alliance_rich_realms = [item for item in alliance_coreData_sheet.col_values(173) if item] #FQ Col Realms
        alliance_rich_balances = [item for item in alliance_coreData_sheet.col_values(174) if item] #FR Col Balances
        
        horde_rich_names = [item for item in horde_coreData_sheet.col_values(172) if item] #FP Col Names
        horde_rich_realms = [item for item in horde_coreData_sheet.col_values(173) if item] #FQ Col Realms
        horde_rich_balances = [item for item in horde_coreData_sheet.col_values(174) if item] #FR Col Balances
        
        i=0
        val=[]
        for item in alliance_rich_realms:
            if i < len(alliance_rich_realms)-1:
                val.append([int(alliance_rich_balances[i].replace(',','')),(alliance_rich_names[i+1]+"-"+alliance_rich_realms[i])])
                i+=1
        i=0
        for item in horde_rich_realms:
            if i < len(horde_rich_realms)-1:
                test_res=f"{horde_rich_names[i+1]}-{horde_rich_realms[i]}"
                #print(test_res)
                if (horde_rich_names[i+1]+"-"+horde_rich_realms[i]) in [elem for sublist in val for elem in sublist]:
                    out = [(ind,ind2) for ind,i in enumerate(val) for ind2,y in enumerate(i) if y == test_res]
                    val[out[0][0]][0]=val[out[0][0]][0]+int(horde_rich_balances[i].replace(',',''))
                else:
                    val.append([int(horde_rich_balances[i].replace(',','')),(horde_rich_names[i+1]+"-"+horde_rich_realms[i])])
                i+=1
        cnx = mysql.connector.connect(
            host="128.199.48.106",
            port="3306",
            user="nova",
            passwd="DiscordNovaP@ssw0rd@qais",
            database="nova_casino"
        )
        cursor = cnx.cursor()
        query = "UPDATE gambling_prod SET balance=%s WHERE name=%s"
        cursor.executemany(query,val)
        cnx.commit()
        bot_log_channel = get(ctx.guild.text_channels, name='bot-logs')
        await bot_log_channel.send(f"{len(val)} record(s) affected")
        cursor.close()
        cnx.close()
    except Exception:
        logging.error(traceback.format_exc())
        bot_log_channel = get(ctx.guild.text_channels, name='bot-logs')
        embed_bot_log = discord.Embed(title="Casino Error Log.", description=traceback.format_exc(), color=discord.Color.orange())
        embed_bot_log.add_field(name="Source", value="on ImportBalance", inline=True)
        # embed_bot_log.add_field(name="Content", value=message.content, inline=False)
        embed_bot_log.set_footer(text=datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S"))
        await bot_log_channel.send(embed=embed_bot_log)



@bot.command(pass_context=True)
@commands.cooldown(3, 20, commands.BucketType.channel)
async def bet(ctx, target_user : discord.Member, pot: str):
    await ctx.message.delete()
    await asyncio.sleep(1)
    pot = convert_si_to_number(pot)
    try:
        if ctx.message.channel.id != 695699820144361554:
            await ctx.message.channel.send("You can only gamble in #nova-casino")
        elif ctx.message.author==target_user:
            await ctx.message.channel.send("Unless you can duplicate your self IRL, you cannot bet against your self!")
        elif pot<1000 or pot == None:
            em = discord.Embed(title="❌ Bet too low",
                                description="The minimum amount for betting is 1000 !",
                                color=discord.Color.red())
            await ctx.message.channel.send(embed=em)
        else:
            gv = open('/NOVA/global_vars.json',"r")
            global_vars = json.load(gv)
            gv.close()
            gamble_embed=discord.Embed(title="💰Gamble info💰", description="", color=0x4feb1c)
            gamble_embed.set_thumbnail(url="https://cdn.discordapp.com/avatars/634917649335320586/ea303e8b580d56ff6837e256b1df6ef6.png")
            gamble_embed.add_field(name="**Initiated By: **", value=ctx.author.mention, inline=True)
            gamble_embed.add_field(name="**Against: **", value=target_user.mention, inline=True)
            gamble_embed.add_field(name="**For the amount of: **", value=f"{pot:,d}", inline=True)
            gamble_embed.set_footer(text="Timestamp (UTC±00:00): " + datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S"))
            gamble_msg = await ctx.message.channel.send(embed=gamble_embed)
            await gamble_msg.add_reaction(u"\U0001F44D")
            cnx = mysql.connector.connect(
                host="128.199.48.106",
                port="3306",
                user="nova",
                passwd="DiscordNovaP@ssw0rd@qais",
                database="nova_casino"
            )
            cursor = cnx.cursor()
            for key in persdict:
                if key == ctx.message.author.id:
                    gambler1 = persdict[ctx.message.author.id]['name'] + '-' + persdict[ctx.message.author.id]['serv']
                    break
                else:
                    gambler1 = ctx.message.author.nick
            for key in persdict:
                if key == target_user.id:
                    gambler2 = persdict[target_user.id]['name'] + '-' + persdict[target_user.id]['serv']
                    break
                else:
                    gambler2 = target_user.nick
            #gambler1 = ctx.message.author.nick
            #gambler2 = target_user.nick
            
            #if gambler1.endswith("[A]") or gambler1.endswith("[H]"):
                #gambler1=gambler1.("-")[0]
            query = "SELECT balance FROM gambling_prod WHERE name=\"" + gambler1 + "\""
            cursor.execute(query)
            gambler1_balance = cursor.fetchone()[0]
            if gambler1_balance == None:
                gambler1_balance=0
            else:
                gambler1_balance=gambler1_balance
            #else:
            #    for key in persdict:
            #        if key == ctx.message.author.id:
            #            gambler1 = persdict[ctx.message.author.id]['name'] + '-' + persdict[ctx.message.author.id]['serv']
            #            break
                # if gambler1 == "Windzorn":
                    # gambler1 = "Windzorn-Silvermoon [A]"
                # elif gambler1 == "Aízagora":
                    # gambler1 = "Aízagora-Silvermoon [A]"
                # elif gambler1 == "Saadi":
                    # gambler1 = "Saadi-Silvermoon [A]"
                # elif gambler1 == "Killêr":
                    # gambler1 = "Killêr-Silvermoon [A]"
                # elif gambler1 == "Menex":
                    # gambler1 = "Menex-Draenor [H]"
                # elif gambler1 == "Sanfura 🤖":
                    # gambler1 = "Sanfura-Ravencrest [A]"
                # elif gambler1 == "Adam":
                    # gambler1 = "Miladtaker-Ravencrest [A]"
                # elif gambler1 == "Laxus":
                    # gambler1 = "Huntardson-TwistingNether [H]"
                # elif gambler1 == "Einargelius":
                    # gambler1 = "Einargelius-Silvermoon [A]"
                # elif gambler1 == "Nashiira":
                    # gambler1 = "Nashiira-Sanguino [H]"
                # elif gambler1 == "Gnomesrock":
                    # gambler1 = "Gnomesrock-Silvermoon [A]"
                # elif gambler1 == "Aiune":
                    # gambler1 = "Aiune-Tyrande [A]"
                #query = "SELECT balance FROM gambling_prod WHERE name=\"" + gambler1 +"\""
                #cursor.execute(query)
                #gambler1_balance = cursor.fetchone()[0]
                #if gambler1_balance == None:
                #    gambler1_balance=0
                #else:
                #    gambler1_balance=gambler1_balance
                
            #if gambler2.endswith("[A]") or gambler2.endswith("[H]"):
                # gambler2=gambler2.partition("-")[0]
            query = "SELECT balance FROM gambling_prod WHERE name=\"" + gambler2 + "\""
            cursor.execute(query)
            gambler2_balance = cursor.fetchone()[0]
            if gambler2_balance == None:
                gambler2_balance=0
            else:
                gambler2_balance=gambler2_balance
            #else:
            #    for key in persdict:
            #        if key == target_user.id:
            #            gambler2 = persdict[member.id]['name'] + '-' + persdict[member.id]['serv']
            #            break
                # if gambler2 == "Windzorn":
                    # gambler2 = "Windzorn-Silvermoon [A]"
                # elif gambler2 == "Aízagora":
                    # gambler2 = "Aízagora-Silvermoon [A]"
                # elif gambler2 == "Saadi":
                    # gambler2 = "Saadi-Silvermoon [A]"
                # elif gambler2 == "Killêr":
                    # gambler2 = "Killêr-Silvermoon [A]"
                # elif gambler2 == "Menex":
                    # gambler2 = "Menex-Draenor [H]"
                # elif gambler2 == "Sanfura 🤖":
                    # gambler2 = "Sanfura-Ravencrest [A]"
                # elif gambler2 == "Adam":
                    # gambler2 = "Miladtaker-Ravencrest [A]"
                # elif gambler2 == "Laxus":
                    # gambler2 = "Huntardson-TwistingNether [H]"
                # elif gambler2 == "Einargelius":
                    # gambler2 = "Einargelius-Silvermoon [A]"
                # elif gambler2 == "Nashiira":
                    # gambler2 = "Nashiira-Sanguino [H]"
                # elif gambler2 == "Gnomesrock":
                    # gambler2 = "Gnomesrock-Silvermoon [A]"
                # elif gambler2 == "Aiune":
                    # gambler2 = "Aiune-Tyrande [A]"
                #query = "SELECT balance FROM gambling_prod WHERE name=\"" + gambler2 +"\""
                #cursor.execute(query)
                #gambler2_balance = cursor.fetchone()[0]
                #if gambler2_balance == None:
                #    gambler2_balance=0
                #else:
                #    gambler2_balance=gambler2_balance
            if int(gambler1_balance) < pot:
                await ctx.message.channel.send(f"{ctx.message.author.mention} doesnt have enough balance to cover **{pot:,d}** , bet is cancelled!")
                await gamble_msg.add_reaction(u"\u274C")
            elif int(gambler2_balance) < pot:
                await ctx.message.channel.send(f"{target_user.mention} doesnt have enough balance to cover **{pot:,d}** , bet is cancelled!")
                await gamble_msg.add_reaction(u"\u274C")
            else:
                def check(reaction, user):
                    m = gamble_msg
                    return user == target_user and str(reaction.emoji) == '👍' and m.id == reaction.message.id

                try:
                    reaction, user = await bot.wait_for('reaction_add', timeout=15.0, check=check)
                except asyncio.TimeoutError:
                    await gamble_msg.add_reaction(u"\u274C")
                    await ctx.message.channel.send(target_user.mention + " didnt respond in time, bet is cancelled!",delete_after=5)
                else:
                    now = datetime.utcnow()
                    d1 = now.strftime("%d/%m/%Y %H:%M:%S")
                    embed_pre = gamble_msg.embeds[0].to_dict()
                    gambler1_roll=random.randint(1, 6)
                    gambler2_roll=random.randint(1, 6)
                    if gambler1_roll>gambler2_roll:
                        gamble_winner=gambler1
                        gamble_loser=gambler2
                        winner_balance = gambler1_balance + (pot-pot*0.1)
                        loser_balance = gambler2_balance - pot
                        
                        embed_pre['color'] = 0xff0000
                        embed_pre['title'] = f"💰Gamble info💰 TOTAL POT: {pot*2:,d}"
                        dice_roll_embed = discord.Embed.from_dict(embed_pre)
                        dice_roll_embed.add_field(name="Roll Results:", value=ctx.message.author.mention + "🎲" + str(gambler1_roll) +"\n" + target_user.mention + "🎲" + str(gambler2_roll) , inline=False)
                        dice_roll_embed.add_field(name="Winner is: ", value= gamble_winner, inline=True)
                        dice_roll_embed.add_field(name="Win Amount: ", value= f"{(pot*2)-(pot*2*0.05):,.0f}" , inline=True)
                        dice_roll_embed.add_field(name="--", value="--" , inline=False)
                        dice_roll_embed.add_field(name="Loser is: ", value= gamble_loser, inline=True)
                        dice_roll_embed.add_field(name="Loss Amount: ", value=f"{pot:,d}" , inline=True)
                        #await gamble_msg.edit(embed=dice_roll_embed)
                        ############################if winner is alliance and loser is alliance##########################
                        if gamble_winner.endswith("[A]") and gamble_loser.endswith("[A]"):
                            gc.login()
                            #alliance_counter_gambling = alliance_find_empty_cell_gambling(alliance_gambling_sheet)
                            A_val = alliance_gambling_sheet.cell(global_vars['alliance_counter_gambling'], 2).value
                            if A_val == None or A_val == "":
                                alliance_gambling_cells = [Cell(row=global_vars['alliance_counter_gambling'], col=2, value=d1),
                                                              Cell(row=global_vars['alliance_counter_gambling'], col=4, value=pot-pot*0.1),
                                                              Cell(row=global_vars['alliance_counter_gambling'], col=5, value="Gamble"),
                                                              Cell(row=global_vars['alliance_counter_gambling'], col=6, value=gamble_winner.partition("-")[0]),
                                                              Cell(row=global_vars['alliance_counter_gambling'], col=7, value=gamble_winner.partition("-")[2])]
                                alliance_gambling_sheet.update_cells(alliance_gambling_cells)
                                gv = open('/NOVA/global_vars.json',"w")
                                global_vars['alliance_counter_gambling']+=1
                                json.dump(global_vars,gv)
                                gv.close()
                                #alliance_counter_gambling = alliance_counter_gambling + 1
                                
                                alliance_gambling_cells = [Cell(row=global_vars['alliance_counter_gambling'], col=2, value=d1),
                                                              Cell(row=global_vars['alliance_counter_gambling'], col=4, value=-pot),
                                                              Cell(row=global_vars['alliance_counter_gambling'], col=5, value="Gamble"),
                                                              Cell(row=global_vars['alliance_counter_gambling'], col=6, value=gamble_loser.partition("-")[0]),
                                                              Cell(row=global_vars['alliance_counter_gambling'], col=7, value=gamble_loser.partition("-")[2])]
                                alliance_gambling_sheet.update_cells(alliance_gambling_cells)
                                gv = open('/NOVA/global_vars.json',"w")
                                global_vars['alliance_counter_gambling']+=1
                                json.dump(global_vars,gv)
                                gv.close()
                                query = "UPDATE gambling_prod SET balance=%s WHERE name=%s"
                                val = [(winner_balance,gambler1),(loser_balance,gambler2)]
                                cursor.executemany(query,val)
                                cnx.commit()
                                query = "INSERT INTO gambling_log (date, pot, name) VALUES (%s, %s, %s)"
                                val = [(d1,pot-pot*0.1,gamble_winner),(d1,-pot,gamble_loser)]
                                cursor.executemany(query,val)
                                cnx.commit()
                                await gamble_msg.edit(embed=dice_roll_embed)
                                await gamble_msg.add_reaction(u"\U0001F4AF")
                            elif A_val != None or A_val != "":
                                    await gamble_msg.add_reaction(u"\u274C")
                            #alliance_counter_gambling = alliance_counter_gambling + 1
                        ############################if winner is alliance and loser is horde##############################
                        elif gamble_winner.endswith("[A]") and gamble_loser.endswith("[H]"):
                            gc.login()
                            #alliance_counter_gambling = alliance_find_empty_cell_gambling(alliance_gambling_sheet)
                            A_val = alliance_gambling_sheet.cell(global_vars['alliance_counter_gambling'], 2).value
                            H_val = horde_gambling_sheet.cell(global_vars['horde_counter_gambling'], 2).value
                            if (A_val == None or A_val == "") and (H_val == None or H_val == ""):
                                alliance_gambling_cells = [Cell(row=global_vars['alliance_counter_gambling'], col=2, value=d1),
                                                              Cell(row=global_vars['alliance_counter_gambling'], col=4, value=pot-pot*0.1),
                                                              Cell(row=global_vars['alliance_counter_gambling'], col=5, value="Gamble"),
                                                              Cell(row=global_vars['alliance_counter_gambling'], col=6, value=gamble_winner.partition("-")[0]),
                                                              Cell(row=global_vars['alliance_counter_gambling'], col=7, value=gamble_winner.partition("-")[2])]
                                alliance_gambling_sheet.update_cells(alliance_gambling_cells)
                                gv = open('/NOVA/global_vars.json',"w")
                                global_vars['alliance_counter_gambling']+=1
                                json.dump(global_vars,gv)
                                gv.close()
                                ##alliance_counter_gambling = alliance_counter_gambling + 1
                                gc.login()
                                #horde_counter_gambling = horde_find_empty_cell_gambling(horde_gambling_sheet)
                                horde_gambling_cells = [Cell(row=global_vars['horde_counter_gambling'], col=2, value=d1),
                                                              Cell(row=global_vars['horde_counter_gambling'], col=4, value=-pot),
                                                              Cell(row=global_vars['horde_counter_gambling'], col=5, value="Gamble"),
                                                              Cell(row=global_vars['horde_counter_gambling'], col=6, value=gamble_loser.partition("-")[0]),
                                                              Cell(row=global_vars['horde_counter_gambling'], col=7, value=gamble_loser.partition("-")[2])]
                                horde_gambling_sheet.update_cells(horde_gambling_cells)
                                gv = open('/NOVA/global_vars.json',"w")
                                global_vars['horde_counter_gambling']+=1
                                json.dump(global_vars,gv)
                                gv.close()
                                query = "UPDATE gambling_prod SET balance=%s WHERE name=%s"
                                val = [(winner_balance,gambler1),(loser_balance,gambler2)]
                                cursor.executemany(query,val)
                                cnx.commit()
                                query = "INSERT INTO gambling_log (date, pot, name) VALUES (%s, %s, %s)"
                                val = [(d1,pot-pot*0.1,gamble_winner),(d1,-pot,gamble_loser)]
                                cursor.executemany(query,val)
                                cnx.commit()
                                await gamble_msg.edit(embed=dice_roll_embed)
                                await gamble_msg.add_reaction(u"\U0001F4AF")
                            elif (A_val != None or A_val != "") and (H_val != None or H_val != ""):
                                await gamble_msg.add_reaction(u"\u274C")
                            ##horde_counter_gambling = horde_counter_gambling + 1
                        ############################if winner is horde and loser is horde##############################
                        elif gamble_winner.endswith("[H]") and gamble_loser.endswith("[H]"):
                            gc.login()
                            #horde_counter_gambling = horde_find_empty_cell_gambling(horde_gambling_sheet)
                            H_val = horde_gambling_sheet.cell(global_vars['horde_counter_gambling'], 2).value
                            if H_val == None or H_val == "":
                                horde_gambling_cells = [Cell(row=global_vars['horde_counter_gambling'], col=2, value=d1),
                                                              Cell(row=global_vars['horde_counter_gambling'], col=4, value=pot-pot*0.1),
                                                              Cell(row=global_vars['horde_counter_gambling'], col=5, value="Gamble"),
                                                              Cell(row=global_vars['horde_counter_gambling'], col=6, value=gamble_winner.partition("-")[0]),
                                                              Cell(row=global_vars['horde_counter_gambling'], col=7, value=gamble_winner.partition("-")[2])]
                                horde_gambling_sheet.update_cells(horde_gambling_cells)
                                gv = open('/NOVA/global_vars.json',"w")
                                global_vars['horde_counter_gambling']+=1
                                json.dump(global_vars,gv)
                                gv.close()
                            #horde_counter_gambling = horde_counter_gambling + 1
                            
                                horde_gambling_cells = [Cell(row=global_vars['horde_counter_gambling'], col=2, value=d1),
                                                              Cell(row=global_vars['horde_counter_gambling'], col=4, value=-pot),
                                                              Cell(row=global_vars['horde_counter_gambling'], col=5, value="Gamble"),
                                                              Cell(row=global_vars['horde_counter_gambling'], col=6, value=gamble_loser.partition("-")[0]),
                                                              Cell(row=global_vars['horde_counter_gambling'], col=7, value=gamble_loser.partition("-")[2])]
                                horde_gambling_sheet.update_cells(horde_gambling_cells)
                                gv = open('/NOVA/global_vars.json',"w")
                                global_vars['horde_counter_gambling']+=1
                                json.dump(global_vars,gv)
                                gv.close()
                                query = "UPDATE gambling_prod SET balance=%s WHERE name=%s"
                                val = [(winner_balance,gambler1),(loser_balance,gambler2)]
                                cursor.executemany(query,val)
                                cnx.commit()
                                query = "INSERT INTO gambling_log (date, pot, name) VALUES (%s, %s, %s)"
                                val = [(d1,pot-pot*0.1,gamble_winner),(d1,-pot,gamble_loser)]
                                cursor.executemany(query,val)
                                cnx.commit()
                                await gamble_msg.edit(embed=dice_roll_embed)
                                await gamble_msg.add_reaction(u"\U0001F4AF")
                            elif H_val != None or H_val != "":
                                await gamble_msg.add_reaction(u"\u274C")
                            ##horde_counter_gambling = horde_counter_gambling + 1
                        ############################if winner is horde and loser is alliance##############################
                        elif gamble_winner.endswith("[H]") and gamble_loser.endswith("[A]"):
                            gc.login()
                            #horde_counter_gambling = horde_find_empty_cell_gambling(horde_gambling_sheet)
                            A_val = alliance_gambling_sheet.cell(global_vars['alliance_counter_gambling'], 2).value
                            H_val = horde_gambling_sheet.cell(global_vars['horde_counter_gambling'], 2).value
                            if (A_val == None or A_val == "") and (H_val == None or H_val == ""):
                                horde_gambling_cells = [Cell(row=global_vars['horde_counter_gambling'], col=2, value=d1),
                                                              Cell(row=global_vars['horde_counter_gambling'], col=4, value=pot-pot*0.1),
                                                              Cell(row=global_vars['horde_counter_gambling'], col=5, value="Gamble"),
                                                              Cell(row=global_vars['horde_counter_gambling'], col=6, value=gamble_winner.partition("-")[0]),
                                                              Cell(row=global_vars['horde_counter_gambling'], col=7, value=gamble_winner.partition("-")[2])]
                                horde_gambling_sheet.update_cells(horde_gambling_cells)
                                gv = open('/NOVA/global_vars.json',"w")
                                global_vars['horde_counter_gambling']+=1
                                json.dump(global_vars,gv)
                                gv.close()
                                ##horde_counter_gambling = horde_counter_gambling + 1
                                gc.login()
                                #alliance_counter_gambling = alliance_find_empty_cell_gambling(alliance_gambling_sheet)
                                alliance_gambling_cells = [Cell(row=global_vars['alliance_counter_gambling'], col=2, value=d1),
                                                              Cell(row=global_vars['alliance_counter_gambling'], col=4, value=-pot),
                                                              Cell(row=global_vars['alliance_counter_gambling'], col=5, value="Gamble"),
                                                              Cell(row=global_vars['alliance_counter_gambling'], col=6, value=gamble_loser.partition("-")[0]),
                                                              Cell(row=global_vars['alliance_counter_gambling'], col=7, value=gamble_loser.partition("-")[2])]
                                alliance_gambling_sheet.update_cells(alliance_gambling_cells)
                                gv = open('/NOVA/global_vars.json',"w")
                                global_vars['alliance_counter_gambling']+=1
                                json.dump(global_vars,gv)
                                gv.close()
                                query = "UPDATE gambling_prod SET balance=%s WHERE name=%s"
                                val = [(winner_balance,gambler1),(loser_balance,gambler2)]
                                cursor.executemany(query,val)
                                cnx.commit()
                                query = "INSERT INTO gambling_log (date, pot, name) VALUES (%s, %s, %s)"
                                val = [(d1,pot-pot*0.1,gamble_winner),(d1,-pot,gamble_loser)]
                                cursor.executemany(query,val)
                                cnx.commit()
                                await gamble_msg.edit(embed=dice_roll_embed)
                                await gamble_msg.add_reaction(u"\U0001F4AF")
                            elif (A_val != None or A_val != "") and (H_val != None or H_val != ""):
                                await gamble_msg.add_reaction(u"\u274C")
                            ##alliance_counter_gambling = alliance_counter_gambling + 1
                    elif gambler2_roll>gambler1_roll:
                        gamble_winner=gambler2
                        gamble_loser=gambler1
                        winner_balance = gambler2_balance + (pot-pot*0.1)
                        loser_balance = gambler1_balance - pot
                        embed_pre['color'] = 0xff0000
                        embed_pre['title'] = f"💰Gamble info💰 TOTAL POT: {pot*2:,d}"
                        dice_roll_embed = discord.Embed.from_dict(embed_pre)
                        dice_roll_embed.add_field(name="Roll Results:", value=ctx.message.author.mention + "🎲" + str(gambler1_roll) +"\n" + target_user.mention + "🎲" + str(gambler2_roll) , inline=False)
                        dice_roll_embed.add_field(name="Winner is: ", value= gamble_winner, inline=True)
                        dice_roll_embed.add_field(name="Win Amount: ", value= f"{(pot*2)-(pot*2*0.05):,.0f}" , inline=True)
                        dice_roll_embed.add_field(name="--", value="--" , inline=False)
                        dice_roll_embed.add_field(name="Loser is: ", value= gamble_loser, inline=True)
                        dice_roll_embed.add_field(name="Loss Amount: ", value=f"{pot:,d}" , inline=True)
                        #await gamble_msg.edit(embed=dice_roll_embed)
                        ############################if winner is alliance and loser is alliance##########################
                        if gamble_winner.endswith("[A]") and gamble_loser.endswith("[A]"):
                            gc.login()
                            #alliance_counter_gambling = alliance_find_empty_cell_gambling(alliance_gambling_sheet)
                            A_val = alliance_gambling_sheet.cell(global_vars['alliance_counter_gambling'], 2).value
                            if A_val == None or A_val == "":
                                alliance_gambling_cells = [Cell(row=global_vars['alliance_counter_gambling'], col=2, value=d1),
                                                              Cell(row=global_vars['alliance_counter_gambling'], col=4, value=pot-pot*0.1),
                                                              Cell(row=global_vars['alliance_counter_gambling'], col=5, value="Gamble"),
                                                              Cell(row=global_vars['alliance_counter_gambling'], col=6, value=gamble_winner.partition("-")[0]),
                                                              Cell(row=global_vars['alliance_counter_gambling'], col=7, value=gamble_winner.partition("-")[2])]
                                alliance_gambling_sheet.update_cells(alliance_gambling_cells)
                                gv = open('/NOVA/global_vars.json',"w")
                                global_vars['alliance_counter_gambling']+=1
                                json.dump(global_vars,gv)
                                gv.close()
                                #alliance_counter_gambling = alliance_counter_gambling + 1
                                
                                alliance_gambling_cells = [Cell(row=global_vars['alliance_counter_gambling'], col=2, value=d1),
                                                              Cell(row=global_vars['alliance_counter_gambling'], col=4, value=-pot),
                                                              Cell(row=global_vars['alliance_counter_gambling'], col=5, value="Gamble"),
                                                              Cell(row=global_vars['alliance_counter_gambling'], col=6, value=gamble_loser.partition("-")[0]),
                                                              Cell(row=global_vars['alliance_counter_gambling'], col=7, value=gamble_loser.partition("-")[2])]
                                alliance_gambling_sheet.update_cells(alliance_gambling_cells)
                                gv = open('/NOVA/global_vars.json',"w")
                                global_vars['alliance_counter_gambling']+=1
                                json.dump(global_vars,gv)
                                gv.close()
                                query = "UPDATE gambling_prod SET balance= %s WHERE name= %s"
                                val = [(winner_balance,gambler2),(loser_balance,gambler1)]
                                cursor.executemany(query,val)
                                cnx.commit()
                                query = "INSERT INTO gambling_log (date, pot, name) VALUES (%s, %s, %s)"
                                val = [(d1,pot-pot*0.1,gamble_winner),(d1,-pot,gamble_loser)]
                                cursor.executemany(query,val)
                                cnx.commit()
                                await gamble_msg.edit(embed=dice_roll_embed)
                                await gamble_msg.add_reaction(u"\U0001F4AF")
                            elif A_val != None or A_val != "":
                                await gamble_msg.add_reaction(u"\u274C")
                            ##alliance_counter_gambling = alliance_counter_gambling + 1
                        ############################if winner is alliance and loser is horde##############################
                        elif gamble_winner.endswith("[A]") and gamble_loser.endswith("[H]"):
                            gc.login()
                            #alliance_counter_gambling = alliance_find_empty_cell_gambling(alliance_gambling_sheet)
                            A_val = alliance_gambling_sheet.cell(global_vars['alliance_counter_gambling'], 2).value
                            H_val = horde_gambling_sheet.cell(global_vars['horde_counter_gambling'], 2).value
                            if (A_val == None or A_val == "") and (H_val == None or H_val == ""):
                                alliance_gambling_cells = [Cell(row=global_vars['alliance_counter_gambling'], col=2, value=d1),
                                                              Cell(row=global_vars['alliance_counter_gambling'], col=4, value=pot-pot*0.1),
                                                              Cell(row=global_vars['alliance_counter_gambling'], col=5, value="Gamble"),
                                                              Cell(row=global_vars['alliance_counter_gambling'], col=6, value=gamble_winner.partition("-")[0]),
                                                              Cell(row=global_vars['alliance_counter_gambling'], col=7, value=gamble_winner.partition("-")[2])]
                                alliance_gambling_sheet.update_cells(alliance_gambling_cells)
                                gv = open('/NOVA/global_vars.json',"w")
                                global_vars['alliance_counter_gambling']+=1
                                json.dump(global_vars,gv)
                                gv.close()
                                ##alliance_counter_gambling = alliance_counter_gambling + 1
                                gc.login()
                                #horde_counter_gambling = horde_find_empty_cell_gambling(horde_gambling_sheet)
                                horde_gambling_cells = [Cell(row=global_vars['horde_counter_gambling'], col=2, value=d1),
                                                              Cell(row=global_vars['horde_counter_gambling'], col=4, value=-pot),
                                                              Cell(row=global_vars['horde_counter_gambling'], col=5, value="Gamble"),
                                                              Cell(row=global_vars['horde_counter_gambling'], col=6, value=gamble_loser.partition("-")[0]),
                                                              Cell(row=global_vars['horde_counter_gambling'], col=7, value=gamble_loser.partition("-")[2])]
                                horde_gambling_sheet.update_cells(horde_gambling_cells)
                                gv = open('/NOVA/global_vars.json',"w")
                                global_vars['horde_counter_gambling']+=1
                                json.dump(global_vars,gv)
                                gv.close()
                                query = "UPDATE gambling_prod SET balance= %s WHERE name= %s"
                                val = [(winner_balance,gambler2),(loser_balance,gambler1)]
                                cursor.executemany(query,val)
                                cnx.commit()
                                query = "INSERT INTO gambling_log (date, pot, name) VALUES (%s, %s, %s)"
                                val = [(d1,pot-pot*0.1,gamble_winner),(d1,-pot,gamble_loser)]
                                cursor.executemany(query,val)
                                cnx.commit()
                                await gamble_msg.edit(embed=dice_roll_embed)
                                await gamble_msg.add_reaction(u"\U0001F4AF")
                            elif (A_val != None or A_val != "") and (H_val != None or H_val != ""):
                                await gamble_msg.add_reaction(u"\u274C")
                            ##horde_counter_gambling = horde_counter_gambling + 1
                        ############################if winner is horde and loser is horde##############################
                        elif gamble_winner.endswith("[H]") and gamble_loser.endswith("[H]"):
                            gc.login()
                            #horde_counter_gambling = horde_find_empty_cell_gambling(horde_gambling_sheet)
                            H_val = horde_gambling_sheet.cell(global_vars['horde_counter_gambling'], 2).value
                            if H_val == None or H_val == "":
                                horde_gambling_cells = [Cell(row=global_vars['horde_counter_gambling'], col=2, value=d1),
                                                              Cell(row=global_vars['horde_counter_gambling'], col=4, value=pot-pot*0.1),
                                                              Cell(row=global_vars['horde_counter_gambling'], col=5, value="Gamble"),
                                                              Cell(row=global_vars['horde_counter_gambling'], col=6, value=gamble_winner.partition("-")[0]),
                                                              Cell(row=global_vars['horde_counter_gambling'], col=7, value=gamble_winner.partition("-")[2])]
                                horde_gambling_sheet.update_cells(horde_gambling_cells)
                                gv = open('/NOVA/global_vars.json',"w")
                                global_vars['horde_counter_gambling']+=1
                                json.dump(global_vars,gv)
                                gv.close()
                                #horde_counter_gambling = horde_counter_gambling + 1
                                
                                horde_gambling_cells = [Cell(row=global_vars['horde_counter_gambling'], col=2, value=d1),
                                                              Cell(row=global_vars['horde_counter_gambling'], col=4, value=-pot),
                                                              Cell(row=global_vars['horde_counter_gambling'], col=5, value="Gamble"),
                                                              Cell(row=global_vars['horde_counter_gambling'], col=6, value=gamble_loser.partition("-")[0]),
                                                              Cell(row=global_vars['horde_counter_gambling'], col=7, value=gamble_loser.partition("-")[2])]
                                horde_gambling_sheet.update_cells(horde_gambling_cells)
                                gv = open('/NOVA/global_vars.json',"w")
                                global_vars['horde_counter_gambling']+=1
                                json.dump(global_vars,gv)
                                gv.close()
                                query = "UPDATE gambling_prod SET balance= %s WHERE name= %s"
                                val = [(winner_balance,gambler2),(loser_balance,gambler1)]
                                cursor.executemany(query,val)
                                cnx.commit()
                                query = "INSERT INTO gambling_log (date, pot, name) VALUES (%s, %s, %s)"
                                val = [(d1,pot-pot*0.1,gamble_winner),(d1,-pot,gamble_loser)]
                                cursor.executemany(query,val)
                                cnx.commit()
                                await gamble_msg.edit(embed=dice_roll_embed)
                                await gamble_msg.add_reaction(u"\U0001F4AF")
                            elif H_val != None or H_val != "":
                                await gamble_msg.add_reaction(u"\u274C")
                            ##horde_counter_gambling = horde_counter_gambling + 1
                        ############################if winner is horde and loser is alliance##############################
                        elif gamble_winner.endswith("[H]") and gamble_loser.endswith("[A]"):
                            gc.login()
                            #horde_counter_gambling = horde_find_empty_cell_gambling(horde_gambling_sheet)
                            A_val = alliance_gambling_sheet.cell(global_vars['alliance_counter_gambling'], 2).value
                            H_val = horde_gambling_sheet.cell(global_vars['horde_counter_gambling'], 2).value
                            if (A_val == None or A_val == "") and (H_val == None or H_val == ""):
                                horde_gambling_cells = [Cell(row=global_vars['horde_counter_gambling'], col=2, value=d1),
                                                              Cell(row=global_vars['horde_counter_gambling'], col=4, value=pot-pot*0.1),
                                                              Cell(row=global_vars['horde_counter_gambling'], col=5, value="Gamble"),
                                                              Cell(row=global_vars['horde_counter_gambling'], col=6, value=gamble_winner.partition("-")[0]),
                                                              Cell(row=global_vars['horde_counter_gambling'], col=7, value=gamble_winner.partition("-")[2])]
                                horde_gambling_sheet.update_cells(horde_gambling_cells)
                                gv = open('/NOVA/global_vars.json',"w")
                                global_vars['horde_counter_gambling']+=1
                                json.dump(global_vars,gv)
                                gv.close()
                                ##horde_counter_gambling = horde_counter_gambling + 1
                                gc.login()
                                #alliance_counter_gambling = alliance_find_empty_cell_gambling(alliance_gambling_sheet)
                                alliance_gambling_cells = [Cell(row=global_vars['alliance_counter_gambling'], col=2, value=d1),
                                                              Cell(row=global_vars['alliance_counter_gambling'], col=4, value=-pot),
                                                              Cell(row=global_vars['alliance_counter_gambling'], col=5, value="Gamble"),
                                                              Cell(row=global_vars['alliance_counter_gambling'], col=6, value=gamble_loser.partition("-")[0]),
                                                              Cell(row=global_vars['alliance_counter_gambling'], col=7, value=gamble_loser.partition("-")[2])]
                                alliance_gambling_sheet.update_cells(alliance_gambling_cells)
                                gv = open('/NOVA/global_vars.json',"w")
                                global_vars['alliance_counter_gambling']+=1
                                json.dump(global_vars,gv)
                                gv.close()
                                query = "UPDATE gambling_prod SET balance= %s WHERE name= %s"
                                val = [(winner_balance,gambler2),(loser_balance,gambler1)]
                                cursor.executemany(query,val)
                                cnx.commit()
                                query = "INSERT INTO gambling_log (date, pot, name) VALUES (%s, %s, %s)"
                                val = [(d1,pot-pot*0.1,gamble_winner),(d1,-pot,gamble_loser)]
                                cursor.executemany(query,val)
                                cnx.commit()
                                await gamble_msg.edit(embed=dice_roll_embed)
                                await gamble_msg.add_reaction(u"\U0001F4AF")
                            elif (A_val != None or A_val != "") and (H_val != None or H_val != ""):
                                await gamble_msg.add_reaction(u"\u274C")
                            ##alliance_counter_gambling = alliance_counter_gambling + 1
                    else:
                        embed_pre['color'] = 0xff0000
                        embed_pre['title'] = f"💰Gamble info💰 TOTAL POT: {pot*2:,d}"
                        dice_roll_embed = discord.Embed.from_dict(embed_pre)
                        dice_roll_embed.add_field(name="Roll Results:", value=ctx.message.author.mention + "🎲" + str(gambler1_roll) +"\n" + target_user.mention + "🎲" + str(gambler2_roll) , inline=True)
                        dice_roll_embed.add_field(name="Winner is: ", value= "Tie, no balance changes!", inline=False)
                        await gamble_msg.edit(embed=dice_roll_embed)
                        await gamble_msg.add_reaction(u"\U0001F4AF")
            cursor.close()
            cnx.close()
    except Exception:
        logging.error(traceback.format_exc())
        await gamble_msg.add_reaction(u"\u274C")
        bot_log_channel = get(ctx.guild.text_channels, name='bot-logs')
        embed_bot_log = discord.Embed(title="CASINO Error Log.", description=traceback.format_exc(), color=discord.Color.orange())
        embed_bot_log.add_field(name="Source", value="on bet", inline=True)
        embed_bot_log.add_field(name="Author", value=ctx.message.author.nick, inline=True)
        embed_bot_log.add_field(name="Channel", value=ctx.channel.name, inline=False)
        embed_bot_log.add_field(name="Link", value=ctx.message.jump_url, inline=True)
        embed_bot_log.add_field(name="Content", value=ctx.message.content, inline=False)
        embed_bot_log.set_footer(text="Timestamp: " + d1)
        await bot_log_channel.send(embed=embed_bot_log)

@bet.error
async def bet_error(ctx, error):
    if isinstance(error, commands.MissingRole):
        em = discord.Embed(title="❌ Missing permissions",
                            description="",
                            color=discord.Color.red())
        await ctx.send(embed=em,delete_after=5)
    elif isinstance(error, commands.CommandNotFound):
        em = discord.Embed(title="❌ No Such Command",
                            description="",
                            color=discord.Color.red())
        await ctx.send(embed=em,delete_after=5)
    elif isinstance(error, commands.BadArgument):
        em = discord.Embed(title="❌ Bad arguments",
                            description="",
                            color=discord.Color.red())
        await ctx.send(embed=em,delete_after=5)
    elif isinstance(error, commands.MissingRequiredArgument):
        em = discord.Embed(title="❌ Missing arguments",
                            description="",
                            color=discord.Color.red())
        await ctx.send(embed=em,delete_after=5)
    elif isinstance(error, commands.CommandOnCooldown):
        em = discord.Embed(title="❌ On Cooldown",
                            description="Betting frequency is limited, please try again in {:.2f}s".format(error.retry_after),
                            color=discord.Color.red())
        await ctx.send(embed=em,delete_after=error.retry_after)
    
@bot.command(pass_context=True)
@commands.cooldown(3, 20, commands.BucketType.channel)
#@commands.has_any_role('Moderator')
async def betAnyone(ctx, pot: str):
    await ctx.message.delete()
    pot = convert_si_to_number(pot)
    try:
        if ctx.message.channel.id != 695699820144361554:
            await ctx.message.channel.send("You can only gamble in #nova-casino")
        elif pot<1000 or pot == None:
            em = discord.Embed(title="❌ Bet too low",
                                description="The minimum amount for betting is 1000 !",
                                color=discord.Color.red())
            await ctx.message.channel.send(embed=em)
        else:
            gv = open('/NOVA/global_vars.json',"r")
            global_vars = json.load(gv)
            gv.close()
            await asyncio.sleep(2)
            gamble_embed=discord.Embed(title="💰Gamble info💰", description="", color=0x4feb1c)
            gamble_embed.set_thumbnail(url="https://cdn.discordapp.com/avatars/634917649335320586/ea303e8b580d56ff6837e256b1df6ef6.png")
            gamble_embed.add_field(name="**Initiated By: **", value=ctx.author.mention, inline=True)
            #gamble_embed.add_field(name="**Against: **", value=target_user.mention, inline=True)
            gamble_embed.add_field(name="**For the amount of: **", value=f"{pot:,d}", inline=True)
            gamble_embed.set_footer(text="Timestamp (UTC±00:00): " + datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S"))
            gamble_msg = await ctx.message.channel.send(embed=gamble_embed)
            await gamble_msg.add_reaction(u"\U0001F44D")
            def check(reaction, user):
                    m = gamble_msg
                    return str(reaction.emoji) == '👍' and m.id == reaction.message.id and not user.bot

            try:
                reaction, user = await bot.wait_for('reaction_add', timeout=15.0, check=check)
            except asyncio.TimeoutError:
                await gamble_msg.add_reaction(u"\u274C")
                await ctx.message.channel.send("No one took the bet, cancelled!",delete_after=5)
            else:
                for key in persdict:
                    if key == ctx.message.author.id:
                        gambler1 = persdict[ctx.message.author.id]['name'] + '-' + persdict[ctx.message.author.id]['serv']
                        break
                    else:
                        gambler1 = ctx.message.author.nick
                for key in persdict:
                    if key == user.id:
                        gambler2 = persdict[user.id]['name'] + '-' + persdict[user.id]['serv']
                        break
                    else:
                        gambler2 = user.nick
                        
                if gambler1==gambler2:
                   await ctx.message.channel.send("Unless you can duplicate your self IRL, you cannot bet against your self!")
                else:
                    cnx = mysql.connector.connect(
                        host="128.199.48.106",
                        port="3306",
                        user="nova",
                        passwd="DiscordNovaP@ssw0rd@qais",
                        database="nova_casino"
                    )
                    cursor = cnx.cursor()
                    
                    #if gambler1.endswith("[A]") or gambler1.endswith("[H]"):
                        #gambler1=gambler1.("-")[0]
                    query = "SELECT balance FROM gambling_prod WHERE name=\"" + gambler1 + "\""
                    cursor.execute(query)
                    gambler1_balance = cursor.fetchone()[0]
                    if gambler1_balance == None:
                        gambler1_balance=0
                    else:
                        gambler1_balance=gambler1_balance
                    #else:
                    #    for key in persdict:
                    #        if key == ctx.message.author.id:
                    #            gambler1 = persdict[member.id]['name'] + '-' + persdict[member.id]['serv']
                    #            break
                        # if gambler1 == "Windzorn":
                            # gambler1 = "Windzorn-Silvermoon [A]"
                        # elif gambler1 == "Aízagora":
                            # gambler1 = "Aízagora-Silvermoon [A]"
                        # elif gambler1 == "Saadi":
                            # gambler1 = "Saadi-Silvermoon [A]"
                        # elif gambler1 == "Killêr":
                            # gambler1 = "Killêr-Silvermoon [A]"
                        # elif gambler1 == "Menex":
                            # gambler1 = "Menex-Draenor [H]"
                        # elif gambler1 == "Sanfura 🤖":
                            # gambler1 = "Sanfura-Ravencrest [A]"
                        # elif gambler1 == "Adam":
                            # gambler1 = "Miladtaker-Ravencrest [A]"
                        # elif gambler1 == "Laxus":
                            # gambler1 = "Huntardson-TwistingNether [H]"
                        # elif gambler1 == "Einargelius":
                            # gambler1 = "Einargelius-Silvermoon [A]"
                        # elif gambler1 == "Gnomesrock":
                            # gambler1 = "Gnomesrock-Silvermoon [A]"
                        # elif gambler1 == "Aiune":
                            # gambler1 = "Aiune-Tyrande [A]"
                        #query = "SELECT balance FROM gambling_prod WHERE name=\"" + gambler1 +"\""
                        #cursor.execute(query)
                        #gambler1_balance = cursor.fetchone()[0]
                        #if gambler1_balance == None:
                        #    gambler1_balance=0
                        #else:
                        #    gambler1_balance=gambler1_balance
                        
                    #if gambler2.endswith("[A]") or gambler2.endswith("[H]"):
                        # gambler2=gambler2.partition("-")[0]
                    query = "SELECT balance FROM gambling_prod WHERE name=\"" + gambler2 + "\""
                    cursor.execute(query)
                    gambler2_balance = cursor.fetchone()[0]
                    if gambler2_balance == None:
                        gambler2_balance=0
                    else:
                        gambler2_balance=gambler2_balance
                    #else:
                    #    for key in persdict:
                    #        if key == user.id:
                    #            gambler2 = persdict[member.id]['name'] + '-' + persdict[member.id]['serv']
                    #            break
                        # if gambler2 == "Windzorn":
                            # gambler2 = "Windzorn-Silvermoon [A]"
                        # elif gambler2 == "Aízagora":
                            # gambler2 = "Aízagora-Silvermoon [A]"
                        # elif gambler2 == "Saadi":
                            # gambler2 = "Saadi-Silvermoon [A]"
                        # elif gambler2 == "Killêr":
                            # gambler2 = "Killêr-Silvermoon [A]"
                        # elif gambler2 == "Menex":
                            # gambler2 = "Menex-Draenor [H]"
                        # elif gambler2 == "Sanfura 🤖":
                            # gambler2 = "Sanfura-Ravencrest [A]"
                        # elif gambler2 == "Adam":
                            # gambler2 = "Miladtaker-Ravencrest [A]"
                        # elif gambler2 == "Laxus":
                            # gambler2 = "Huntardson-TwistingNether [H]"
                        # elif gambler2 == "Einargelius":
                            # gambler2 = "Einargelius-Silvermoon [A]"
                        # elif gambler2 == "Nashiira":
                            # gambler2 = "Nashiira-Sanguino [H]"
                        # elif gambler2 == "Gnomesrock":
                            # gambler2 = "Gnomesrock-Silvermoon [A]"
                        # elif gambler2 == "Aiune":
                            # gambler2 = "Aiune-Tyrande [A]"
                        #query = "SELECT balance FROM gambling_prod WHERE name=\"" + gambler2 +"\""
                        #cursor.execute(query)
                        #gambler2_balance = cursor.fetchone()[0]
                        #if gambler2_balance == None:
                        #    gambler2_balance=0
                        #else:
                        #    gambler2_balance=gambler2_balance
                    if int(gambler1_balance) < pot:
                        await ctx.message.channel.send(f"{ctx.message.author.mention} doesnt have enough balance to cover **{pot:,d}** , bet is cancelled!")
                        await gamble_msg.add_reaction(u"\u274C")
                    elif int(gambler2_balance) < pot:
                        await ctx.message.channel.send(f"{user.mention} doesnt have enough balance to cover **{pot:,d}** , bet is cancelled!")
                        await gamble_msg.add_reaction(u"\u274C")
                    else:
                        now = datetime.utcnow()
                        d1 = now.strftime("%d/%m/%Y %H:%M:%S")
                        gc.login()
                        embed_pre = gamble_msg.embeds[0].to_dict()
                        gambler1_roll=random.randint(1, 6)
                        gambler2_roll=random.randint(1, 6)
                        if gambler1_roll>gambler2_roll:
                            gamble_winner=gambler1
                            gamble_loser=gambler2
                            winner_balance = gambler1_balance + (pot-pot*0.1)
                            loser_balance = gambler2_balance - pot
                            embed_pre['color'] = 0xff0000
                            embed_pre['title'] = f"💰Gamble info💰 TOTAL POT: {pot*2:,d}"
                            dice_roll_embed = discord.Embed.from_dict(embed_pre)
                            dice_roll_embed.add_field(name="Roll Results:", value=ctx.message.author.mention + "🎲" + str(gambler1_roll) +"\n" + user.mention + "🎲" + str(gambler2_roll) , inline=False)
                            dice_roll_embed.add_field(name="Winner is: ", value= gamble_winner, inline=True)
                            dice_roll_embed.add_field(name="Win Amount: ", value= f"{(pot*2)-(pot*2*0.05):,.0f}" , inline=True)
                            dice_roll_embed.add_field(name="--", value="--" , inline=False)
                            dice_roll_embed.add_field(name="Loser is: ", value= gamble_loser, inline=True)
                            dice_roll_embed.add_field(name="Loss Amount: ", value=f"{pot:,d}" , inline=True)
                            #await gamble_msg.edit(embed=dice_roll_embed)
                            ############################if winner is alliance and loser is alliance##########################
                            if gamble_winner.endswith("[A]") and gamble_loser.endswith("[A]"):
                                #print("A and A")
                                gc.login()
                                #alliance_counter_gambling = alliance_find_empty_cell_gambling(alliance_gambling_sheet)
                                A_val = alliance_gambling_sheet.cell(global_vars['alliance_counter_gambling'], 2).value
                                if A_val == None or A_val == "":
                                    alliance_gambling_cells = [Cell(row=global_vars['alliance_counter_gambling'], col=2, value=d1),
                                                                  Cell(row=global_vars['alliance_counter_gambling'], col=4, value=pot-pot*0.1),
                                                                  Cell(row=global_vars['alliance_counter_gambling'], col=5, value="Gamble"),
                                                                  Cell(row=global_vars['alliance_counter_gambling'], col=6, value=gamble_winner.partition("-")[0]),
                                                                  Cell(row=global_vars['alliance_counter_gambling'], col=7, value=gamble_winner.partition("-")[2])]
                                    alliance_gambling_sheet.update_cells(alliance_gambling_cells)
                                    gv = open('/NOVA/global_vars.json',"w")
                                    global_vars['alliance_counter_gambling']+=1
                                    json.dump(global_vars,gv)
                                    gv.close()
                                    #alliance_counter_gambling = alliance_counter_gambling + 1
                                    
                                    alliance_gambling_cells = [Cell(row=global_vars['alliance_counter_gambling'], col=2, value=d1),
                                                                  Cell(row=global_vars['alliance_counter_gambling'], col=4, value=-pot),
                                                                  Cell(row=global_vars['alliance_counter_gambling'], col=5, value="Gamble"),
                                                                  Cell(row=global_vars['alliance_counter_gambling'], col=6, value=gamble_loser.partition("-")[0]),
                                                                  Cell(row=global_vars['alliance_counter_gambling'], col=7, value=gamble_loser.partition("-")[2])]
                                    alliance_gambling_sheet.update_cells(alliance_gambling_cells)
                                    gv = open('/NOVA/global_vars.json',"w")
                                    global_vars['alliance_counter_gambling']+=1
                                    json.dump(global_vars,gv)
                                    gv.close()
                                    query = "UPDATE gambling_prod SET balance=%s WHERE name=%s"
                                    val = [(winner_balance,gambler1),(loser_balance,gambler2)]
                                    cursor.executemany(query,val)
                                    cnx.commit()
                                    query = "INSERT INTO gambling_log (date, pot, name) VALUES (%s, %s, %s)"
                                    val = [(d1,pot-pot*0.1,gamble_winner),(d1,-pot,gamble_loser)]
                                    cursor.executemany(query,val)
                                    cnx.commit()
                                    await gamble_msg.edit(embed=dice_roll_embed)
                                    await gamble_msg.add_reaction(u"\U0001F4AF")
                                elif A_val != None or A_val != "":
                                    await gamble_msg.add_reaction(u"\u274C")
                                ##alliance_counter_gambling = alliance_counter_gambling + 1
                            ############################if winner is alliance and loser is horde##############################
                            elif gamble_winner.endswith("[A]") and gamble_loser.endswith("[H]"):
                                #print("A and H")
                                gc.login()
                                A_val = alliance_gambling_sheet.cell(global_vars['alliance_counter_gambling'], 2).value
                                H_val = horde_gambling_sheet.cell(global_vars['horde_counter_gambling'], 2).value
                                #alliance_counter_gambling = alliance_find_empty_cell_gambling(alliance_gambling_sheet)
                                if (A_val == None or A_val == "") and (H_val == None or H_val == ""):
                                    alliance_gambling_cells = [Cell(row=global_vars['alliance_counter_gambling'], col=2, value=d1),
                                                                  Cell(row=global_vars['alliance_counter_gambling'], col=4, value=pot-pot*0.1),
                                                                  Cell(row=global_vars['alliance_counter_gambling'], col=5, value="Gamble"),
                                                                  Cell(row=global_vars['alliance_counter_gambling'], col=6, value=gamble_winner.partition("-")[0]),
                                                                  Cell(row=global_vars['alliance_counter_gambling'], col=7, value=gamble_winner.partition("-")[2])]
                                    alliance_gambling_sheet.update_cells(alliance_gambling_cells)
                                    gv = open('/NOVA/global_vars.json',"w")
                                    global_vars['alliance_counter_gambling']+=1
                                    json.dump(global_vars,gv)
                                    gv.close()
                                    ##alliance_counter_gambling = alliance_counter_gambling + 1
                                    gc.login()
                                    #horde_counter_gambling = horde_find_empty_cell_gambling(horde_gambling_sheet)
                                    horde_gambling_cells = [Cell(row=global_vars['horde_counter_gambling'], col=2, value=d1),
                                                                  Cell(row=global_vars['horde_counter_gambling'], col=4, value=-pot),
                                                                  Cell(row=global_vars['horde_counter_gambling'], col=5, value="Gamble"),
                                                                  Cell(row=global_vars['horde_counter_gambling'], col=6, value=gamble_loser.partition("-")[0]),
                                                                  Cell(row=global_vars['horde_counter_gambling'], col=7, value=gamble_loser.partition("-")[2])]
                                    horde_gambling_sheet.update_cells(horde_gambling_cells)
                                    gv = open('/NOVA/global_vars.json',"w")
                                    global_vars['horde_counter_gambling']+=1
                                    json.dump(global_vars,gv)
                                    gv.close()
                                    query = "UPDATE gambling_prod SET balance=%s WHERE name=%s"
                                    val = [(winner_balance,gambler1),(loser_balance,gambler2)]
                                    cursor.executemany(query,val)
                                    cnx.commit()
                                    query = "INSERT INTO gambling_log (date, pot, name) VALUES (%s, %s, %s)"
                                    val = [(d1,pot-pot*0.1,gamble_winner),(d1,-pot,gamble_loser)]
                                    cursor.executemany(query,val)
                                    cnx.commit()
                                    await gamble_msg.edit(embed=dice_roll_embed)
                                    await gamble_msg.add_reaction(u"\U0001F4AF")
                                elif (A_val != None or A_val != "") and (H_val != None or H_val != ""):
                                    await gamble_msg.add_reaction(u"\u274C")
                                ##horde_counter_gambling = horde_counter_gambling + 1
                            ############################if winner is horde and loser is horde##############################
                            elif gamble_winner.endswith("[H]") and gamble_loser.endswith("[H]"):
                                #print("H and H")
                                gc.login()
                                #horde_counter_gambling = horde_find_empty_cell_gambling(horde_gambling_sheet)
                                H_val = horde_gambling_sheet.cell(global_vars['horde_counter_gambling'], 2).value
                                if H_val == None or H_val == "":
                                    horde_gambling_cells = [Cell(row=global_vars['horde_counter_gambling'], col=2, value=d1),
                                                                  Cell(row=global_vars['horde_counter_gambling'], col=4, value=pot-pot*0.1),
                                                                  Cell(row=global_vars['horde_counter_gambling'], col=5, value="Gamble"),
                                                                  Cell(row=global_vars['horde_counter_gambling'], col=6, value=gamble_winner.partition("-")[0]),
                                                                  Cell(row=global_vars['horde_counter_gambling'], col=7, value=gamble_winner.partition("-")[2])]
                                    horde_gambling_sheet.update_cells(horde_gambling_cells)
                                    gv = open('/NOVA/global_vars.json',"w")
                                    global_vars['horde_counter_gambling']+=1
                                    json.dump(global_vars,gv)
                                    gv.close()
                                    #horde_counter_gambling = horde_counter_gambling + 1
                                    
                                    horde_gambling_cells = [Cell(row=global_vars['horde_counter_gambling'], col=2, value=d1),
                                                                  Cell(row=global_vars['horde_counter_gambling'], col=4, value=-pot),
                                                                  Cell(row=global_vars['horde_counter_gambling'], col=5, value="Gamble"),
                                                                  Cell(row=global_vars['horde_counter_gambling'], col=6, value=gamble_loser.partition("-")[0]),
                                                                  Cell(row=global_vars['horde_counter_gambling'], col=7, value=gamble_loser.partition("-")[2])]
                                    horde_gambling_sheet.update_cells(horde_gambling_cells)
                                    gv = open('/NOVA/global_vars.json',"w")
                                    global_vars['horde_counter_gambling']+=1
                                    json.dump(global_vars,gv)
                                    gv.close()
                                    query = "UPDATE gambling_prod SET balance=%s WHERE name=%s"
                                    val = [(winner_balance,gambler1),(loser_balance,gambler2)]
                                    cursor.executemany(query,val)
                                    cnx.commit()
                                    query = "INSERT INTO gambling_log (date, pot, name) VALUES (%s, %s, %s)"
                                    val = [(d1,pot-pot*0.1,gamble_winner),(d1,-pot,gamble_loser)]
                                    cursor.executemany(query,val)
                                    cnx.commit()
                                    await gamble_msg.edit(embed=dice_roll_embed)
                                    await gamble_msg.add_reaction(u"\U0001F4AF")
                                elif H_val != None or H_val != "":
                                    await gamble_msg.add_reaction(u"\u274C")
                                ##horde_counter_gambling = horde_counter_gambling + 1
                            ############################if winner is horde and loser is alliance##############################
                            elif gamble_winner.endswith("[H]") and gamble_loser.endswith("[A]"):
                                #print("H and A")
                                gc.login()
                                #horde_counter_gambling = horde_find_empty_cell_gambling(horde_gambling_sheet)
                                A_val = alliance_gambling_sheet.cell(global_vars['alliance_counter_gambling'], 2).value
                                H_val = horde_gambling_sheet.cell(global_vars['horde_counter_gambling'], 2).value
                                if (A_val == None or A_val == "") and (H_val == None or H_val == ""):
                                    horde_gambling_cells = [Cell(row=global_vars['horde_counter_gambling'], col=2, value=d1),
                                                                  Cell(row=global_vars['horde_counter_gambling'], col=4, value=pot-pot*0.1),
                                                                  Cell(row=global_vars['horde_counter_gambling'], col=5, value="Gamble"),
                                                                  Cell(row=global_vars['horde_counter_gambling'], col=6, value=gamble_winner.partition("-")[0]),
                                                                  Cell(row=global_vars['horde_counter_gambling'], col=7, value=gamble_winner.partition("-")[2])]
                                    horde_gambling_sheet.update_cells(horde_gambling_cells)
                                    gv = open('/NOVA/global_vars.json',"w")
                                    global_vars['horde_counter_gambling']+=1
                                    json.dump(global_vars,gv)
                                    gv.close()
                                    ##horde_counter_gambling = horde_counter_gambling + 1
                                    gc.login()
                                    #alliance_counter_gambling = alliance_find_empty_cell_gambling(alliance_gambling_sheet)
                                    alliance_gambling_cells = [Cell(row=global_vars['alliance_counter_gambling'], col=2, value=d1),
                                                                  Cell(row=global_vars['alliance_counter_gambling'], col=4, value=-pot),
                                                                  Cell(row=global_vars['alliance_counter_gambling'], col=5, value="Gamble"),
                                                                  Cell(row=global_vars['alliance_counter_gambling'], col=6, value=gamble_loser.partition("-")[0]),
                                                                  Cell(row=global_vars['alliance_counter_gambling'], col=7, value=gamble_loser.partition("-")[2])]
                                    alliance_gambling_sheet.update_cells(alliance_gambling_cells)
                                    gv = open('/NOVA/global_vars.json',"w")
                                    global_vars['alliance_counter_gambling']+=1
                                    json.dump(global_vars,gv)
                                    gv.close()
                                    query = "UPDATE gambling_prod SET balance=%s WHERE name=%s"
                                    val = [(winner_balance,gambler1),(loser_balance,gambler2)]
                                    cursor.executemany(query,val)
                                    cnx.commit()
                                    query = "INSERT INTO gambling_log (date, pot, name) VALUES (%s, %s, %s)"
                                    val = [(d1,pot-pot*0.1,gamble_winner),(d1,-pot,gamble_loser)]
                                    cursor.executemany(query,val)
                                    cnx.commit()
                                    await gamble_msg.edit(embed=dice_roll_embed)
                                    await gamble_msg.add_reaction(u"\U0001F4AF")
                                elif (A_val != None or A_val != "") and (H_val != None or H_val != ""):
                                    await gamble_msg.add_reaction(u"\u274C")
                                ##alliance_counter_gambling = alliance_counter_gambling + 1
                            
                        elif gambler2_roll>gambler1_roll:
                            gamble_winner=gambler2
                            gamble_loser=gambler1
                            winner_balance = gambler2_balance + (pot-pot*0.1)
                            loser_balance = gambler1_balance - pot
                            embed_pre['color'] = 0xff0000
                            embed_pre['title'] = f"💰Gamble info💰 TOTAL POT: {pot*2:,d}"
                            dice_roll_embed = discord.Embed.from_dict(embed_pre)
                            dice_roll_embed.add_field(name="Roll Results:", value=ctx.message.author.mention + "🎲" + str(gambler1_roll) +"\n" + user.mention + "🎲" + str(gambler2_roll) , inline=False)
                            dice_roll_embed.add_field(name="Winner is: ", value= gamble_winner, inline=True)
                            dice_roll_embed.add_field(name="Win Amount: ", value= f"{(pot*2)-(pot*2*0.05):,.0f}" , inline=True)
                            dice_roll_embed.add_field(name="--", value="--" , inline=False)
                            dice_roll_embed.add_field(name="Loser is: ", value= gamble_loser, inline=True)
                            dice_roll_embed.add_field(name="Loss Amount: ", value=f"{pot:,d}" , inline=True)
                            #await gamble_msg.edit(embed=dice_roll_embed)
                            ############################if winner is alliance and loser is alliance##########################
                            if gamble_winner.endswith("[A]") and gamble_loser.endswith("[A]"):
                                #print("A and A")
                                gc.login()
                                #alliance_counter_gambling = alliance_find_empty_cell_gambling(alliance_gambling_sheet)
                                A_val = alliance_gambling_sheet.cell(global_vars['alliance_counter_gambling'], 2).value
                                if A_val == None or A_val == "":
                                    alliance_gambling_cells = [Cell(row=global_vars['alliance_counter_gambling'], col=2, value=d1),
                                                                  Cell(row=global_vars['alliance_counter_gambling'], col=4, value=pot-pot*0.1),
                                                                  Cell(row=global_vars['alliance_counter_gambling'], col=5, value="Gamble"),
                                                                  Cell(row=global_vars['alliance_counter_gambling'], col=6, value=gamble_winner.partition("-")[0]),
                                                                  Cell(row=global_vars['alliance_counter_gambling'], col=7, value=gamble_winner.partition("-")[2])]
                                    alliance_gambling_sheet.update_cells(alliance_gambling_cells)
                                    gv = open('/NOVA/global_vars.json',"w")
                                    global_vars['alliance_counter_gambling']+=1
                                    json.dump(global_vars,gv)
                                    gv.close()
                                    #alliance_counter_gambling = alliance_counter_gambling + 1
                                    
                                    alliance_gambling_cells = [Cell(row=global_vars['alliance_counter_gambling'], col=2, value=d1),
                                                                  Cell(row=global_vars['alliance_counter_gambling'], col=4, value=-pot),
                                                                  Cell(row=global_vars['alliance_counter_gambling'], col=5, value="Gamble"),
                                                                  Cell(row=global_vars['alliance_counter_gambling'], col=6, value=gamble_loser.partition("-")[0]),
                                                                  Cell(row=global_vars['alliance_counter_gambling'], col=7, value=gamble_loser.partition("-")[2])]
                                    alliance_gambling_sheet.update_cells(alliance_gambling_cells)
                                    gv = open('/NOVA/global_vars.json',"w")
                                    global_vars['alliance_counter_gambling']+=1
                                    json.dump(global_vars,gv)
                                    gv.close()
                                    query = "UPDATE gambling_prod SET balance= %s WHERE name= %s"
                                    val = [(winner_balance,gambler2),(loser_balance,gambler1)]
                                    cursor.executemany(query,val)
                                    cnx.commit()
                                    query = "INSERT INTO gambling_log (date, pot, name) VALUES (%s, %s, %s)"
                                    val = [(d1,pot-pot*0.1,gamble_winner),(d1,-pot,gamble_loser)]
                                    cursor.executemany(query,val)
                                    cnx.commit()
                                    await gamble_msg.edit(embed=dice_roll_embed)
                                    await gamble_msg.add_reaction(u"\U0001F4AF")
                                elif A_val != None or A_val != "":
                                    await gamble_msg.add_reaction(u"\u274C")
                                ##alliance_counter_gambling = alliance_counter_gambling + 1
                            ############################if winner is alliance and loser is horde##############################
                            elif gamble_winner.endswith("[A]") and gamble_loser.endswith("[H]"):
                                #print("A and H")
                                gc.login()
                                #alliance_counter_gambling = alliance_find_empty_cell_gambling(alliance_gambling_sheet)
                                A_val = alliance_gambling_sheet.cell(global_vars['alliance_counter_gambling'], 2).value
                                H_val = horde_gambling_sheet.cell(global_vars['horde_counter_gambling'], 2).value
                                if (A_val == None or A_val == "") and (H_val == None or H_val == ""):
                                    alliance_gambling_cells = [Cell(row=global_vars['alliance_counter_gambling'], col=2, value=d1),
                                                                  Cell(row=global_vars['alliance_counter_gambling'], col=4, value=pot-pot*0.1),
                                                                  Cell(row=global_vars['alliance_counter_gambling'], col=5, value="Gamble"),
                                                                  Cell(row=global_vars['alliance_counter_gambling'], col=6, value=gamble_winner.partition("-")[0]),
                                                                  Cell(row=global_vars['alliance_counter_gambling'], col=7, value=gamble_winner.partition("-")[2])]
                                    alliance_gambling_sheet.update_cells(alliance_gambling_cells)
                                    gv = open('/NOVA/global_vars.json',"w")
                                    global_vars['alliance_counter_gambling']+=1
                                    json.dump(global_vars,gv)
                                    gv.close()
                                    ##alliance_counter_gambling = alliance_counter_gambling + 1
                                    gc.login()
                                    #horde_counter_gambling = horde_find_empty_cell_gambling(horde_gambling_sheet)
                                    horde_gambling_cells = [Cell(row=global_vars['horde_counter_gambling'], col=2, value=d1),
                                                                  Cell(row=global_vars['horde_counter_gambling'], col=4, value=-pot),
                                                                  Cell(row=global_vars['horde_counter_gambling'], col=5, value="Gamble"),
                                                                  Cell(row=global_vars['horde_counter_gambling'], col=6, value=gamble_loser.partition("-")[0]),
                                                                  Cell(row=global_vars['horde_counter_gambling'], col=7, value=gamble_loser.partition("-")[2])]
                                    horde_gambling_sheet.update_cells(horde_gambling_cells)
                                    gv = open('/NOVA/global_vars.json',"w")
                                    global_vars['horde_counter_gambling']+=1
                                    json.dump(global_vars,gv)
                                    gv.close()
                                    query = "UPDATE gambling_prod SET balance= %s WHERE name= %s"
                                    val = [(winner_balance,gambler2),(loser_balance,gambler1)]
                                    cursor.executemany(query,val)
                                    cnx.commit()
                                    query = "INSERT INTO gambling_log (date, pot, name) VALUES (%s, %s, %s)"
                                    val = [(d1,pot-pot*0.1,gamble_winner),(d1,-pot,gamble_loser)]
                                    cursor.executemany(query,val)
                                    cnx.commit()
                                    await gamble_msg.edit(embed=dice_roll_embed)
                                    await gamble_msg.add_reaction(u"\U0001F4AF")
                                elif (A_val != None or A_val != "") and (H_val != None or H_val != ""):
                                    await gamble_msg.add_reaction(u"\u274C")
                                ##horde_counter_gambling = horde_counter_gambling + 1
                            ############################if winner is horde and loser is horde##############################
                            elif gamble_winner.endswith("[H]") and gamble_loser.endswith("[H]"):
                                #print("H and H")
                                gc.login()
                                #horde_counter_gambling = horde_find_empty_cell_gambling(horde_gambling_sheet)
                                H_val = horde_gambling_sheet.cell(global_vars['horde_counter_gambling'], 2).value
                                if H_val == None or H_val == "":
                                    horde_gambling_cells = [Cell(row=global_vars['horde_counter_gambling'], col=2, value=d1),
                                                                  Cell(row=global_vars['horde_counter_gambling'], col=4, value=pot-pot*0.1),
                                                                  Cell(row=global_vars['horde_counter_gambling'], col=5, value="Gamble"),
                                                                  Cell(row=global_vars['horde_counter_gambling'], col=6, value=gamble_winner.partition("-")[0]),
                                                                  Cell(row=global_vars['horde_counter_gambling'], col=7, value=gamble_winner.partition("-")[2])]
                                    horde_gambling_sheet.update_cells(horde_gambling_cells)
                                    gv = open('/NOVA/global_vars.json',"w")
                                    global_vars['horde_counter_gambling']+=1
                                    json.dump(global_vars,gv)
                                    gv.close()
                                    #horde_counter_gambling = horde_counter_gambling + 1
                                    
                                    horde_gambling_cells = [Cell(row=global_vars['horde_counter_gambling'], col=2, value=d1),
                                                                  Cell(row=global_vars['horde_counter_gambling'], col=4, value=-pot),
                                                                  Cell(row=global_vars['horde_counter_gambling'], col=5, value="Gamble"),
                                                                  Cell(row=global_vars['horde_counter_gambling'], col=6, value=gamble_loser.partition("-")[0]),
                                                                  Cell(row=global_vars['horde_counter_gambling'], col=7, value=gamble_loser.partition("-")[2])]
                                    horde_gambling_sheet.update_cells(horde_gambling_cells)
                                    gv = open('/NOVA/global_vars.json',"w")
                                    global_vars['horde_counter_gambling']+=1
                                    json.dump(global_vars,gv)
                                    gv.close()
                                    query = "UPDATE gambling_prod SET balance= %s WHERE name= %s"
                                    val = [(winner_balance,gambler2),(loser_balance,gambler1)]
                                    cursor.executemany(query,val)
                                    cnx.commit()
                                    query = "INSERT INTO gambling_log (date, pot, name) VALUES (%s, %s, %s)"
                                    val = [(d1,pot-pot*0.1,gamble_winner),(d1,-pot,gamble_loser)]
                                    cursor.executemany(query,val)
                                    cnx.commit()
                                    await gamble_msg.edit(embed=dice_roll_embed)
                                    await gamble_msg.add_reaction(u"\U0001F4AF")
                                elif H_val != None or H_val != "":
                                    await gamble_msg.add_reaction(u"\u274C")
                                ##horde_counter_gambling = horde_counter_gambling + 1
                            ############################if winner is horde and loser is alliance##############################
                            elif gamble_winner.endswith("[H]") and gamble_loser.endswith("[A]"):
                                #print("H and A")
                                gc.login()
                                #horde_counter_gambling = horde_find_empty_cell_gambling(horde_gambling_sheet)
                                A_val = alliance_gambling_sheet.cell(global_vars['alliance_counter_gambling'], 2).value
                                H_val = horde_gambling_sheet.cell(global_vars['horde_counter_gambling'], 2).value
                                if (A_val == None or A_val == "") and (H_val == None or H_val == ""):
                                    horde_gambling_cells = [Cell(row=global_vars['horde_counter_gambling'], col=2, value=d1),
                                                                  Cell(row=global_vars['horde_counter_gambling'], col=4, value=pot-pot*0.1),
                                                                  Cell(row=global_vars['horde_counter_gambling'], col=5, value="Gamble"),
                                                                  Cell(row=global_vars['horde_counter_gambling'], col=6, value=gamble_winner.partition("-")[0]),
                                                                  Cell(row=global_vars['horde_counter_gambling'], col=7, value=gamble_winner.partition("-")[2])]
                                    horde_gambling_sheet.update_cells(horde_gambling_cells)
                                    gv = open('/NOVA/global_vars.json',"w")
                                    global_vars['horde_counter_gambling']+=1
                                    json.dump(global_vars,gv)
                                    gv.close()
                                    ##horde_counter_gambling = horde_counter_gambling + 1
                                    gc.login()
                                    #alliance_counter_gambling = alliance_find_empty_cell_gambling(alliance_gambling_sheet)
                                    alliance_gambling_cells = [Cell(row=global_vars['alliance_counter_gambling'], col=2, value=d1),
                                                                  Cell(row=global_vars['alliance_counter_gambling'], col=4, value=-pot),
                                                                  Cell(row=global_vars['alliance_counter_gambling'], col=5, value="Gamble"),
                                                                  Cell(row=global_vars['alliance_counter_gambling'], col=6, value=gamble_loser.partition("-")[0]),
                                                                  Cell(row=global_vars['alliance_counter_gambling'], col=7, value=gamble_loser.partition("-")[2])]
                                    alliance_gambling_sheet.update_cells(alliance_gambling_cells)
                                    gv = open('/NOVA/global_vars.json',"w")
                                    global_vars['alliance_counter_gambling']+=1
                                    json.dump(global_vars,gv)
                                    gv.close()
                                    query = "UPDATE gambling_prod SET balance= %s WHERE name= %s"
                                    val = [(winner_balance,gambler2),(loser_balance,gambler1)]
                                    cursor.executemany(query,val)
                                    cnx.commit()
                                    query = "INSERT INTO gambling_log (date, pot, name) VALUES (%s, %s, %s)"
                                    val = [(d1,pot-pot*0.1,gamble_winner),(d1,-pot,gamble_loser)]
                                    cursor.executemany(query,val)
                                    cnx.commit()
                                    await gamble_msg.edit(embed=dice_roll_embed)
                                    await gamble_msg.add_reaction(u"\U0001F4AF")
                                elif (A_val != None or A_val != "") and (H_val != None or H_val != ""):
                                    await gamble_msg.add_reaction(u"\u274C")
                                ##alliance_counter_gambling = alliance_counter_gambling + 1
                        else:
                            embed_pre['color'] = 0xff0000
                            embed_pre['title'] = f"💰Gamble info💰 TOTAL POT: {pot*2:,d}"
                            dice_roll_embed = discord.Embed.from_dict(embed_pre)
                            dice_roll_embed.add_field(name="Roll Results:", value=ctx.message.author.mention + "🎲" + str(gambler1_roll) +"\n" + user.mention + "🎲" + str(gambler2_roll) , inline=True)
                            dice_roll_embed.add_field(name="Winner is: ", value= "Tie, no balance changes!", inline=False)
                            await gamble_msg.edit(embed=dice_roll_embed)
                            await gamble_msg.add_reaction(u"\U0001F4AF")
                    cursor.close()
                    cnx.close()
    except Exception:
        cursor.close()
        cnx.close()
        logging.error(traceback.format_exc())
        await gamble_msg.add_reaction(u"\u274C")
        bot_log_channel = get(ctx.guild.text_channels, name='bot-logs')
        embed_bot_log = discord.Embed(title="CASINO Error Log.", description=traceback.format_exc(), color=discord.Color.orange())
        embed_bot_log.add_field(name="Source", value="on betAnyone", inline=True)
        embed_bot_log.add_field(name="Author", value=ctx.message.author.nick, inline=True)
        embed_bot_log.add_field(name="Channel", value=ctx.channel.name, inline=False)
        embed_bot_log.add_field(name="Link", value=ctx.message.jump_url, inline=True)
        embed_bot_log.add_field(name="Content", value=ctx.message.content, inline=False)
        embed_bot_log.set_footer(text="Timestamp: " + d1)
        await bot_log_channel.send(embed=embed_bot_log)

@betAnyone.error
async def betAnyone_error(ctx, error):
    if isinstance(error, commands.MissingRole):
        em = discord.Embed(title="❌ Missing permissions",
                            description="",
                            color=discord.Color.red())
        await ctx.send(embed=em,delete_after=5)
    elif isinstance(error, commands.CommandNotFound):
        em = discord.Embed(title="❌ No Such Command",
                            description="",
                            color=discord.Color.red())
        await ctx.send(embed=em,delete_after=5)
    elif isinstance(error, commands.BadArgument):
        em = discord.Embed(title="❌ Bad arguments",
                            description="",
                            color=discord.Color.red())
        await ctx.send(embed=em,delete_after=5)
    elif isinstance(error, commands.MissingRequiredArgument):
        em = discord.Embed(title="❌ Missing arguments",
                            description="",
                            color=discord.Color.red())
        await ctx.send(embed=em,delete_after=5)
    elif isinstance(error, commands.CommandOnCooldown):
        em = discord.Embed(title="❌ On Cooldown",
                            description="Betting frequency is limited, please try again in {:.2f}s".format(error.retry_after),
                            color=discord.Color.red())
        await ctx.send(embed=em,delete_after=error.retry_after)

#######################################################
class MyConverter(mysql.connector.conversion.MySQLConverter):

    def row_to_python(self, row, fields):
        row = super(MyConverter, self).row_to_python(row, fields)

        def to_unicode(col):
            if isinstance(col, bytearray):
                return col.decode('utf-8')
            return col

        return[to_unicode(col) for col in row]
        
@bot.command(pass_context=True)
@commands.cooldown(2, 20, commands.BucketType.channel)
#@commands.has_any_role('Moderator')
async def lottery(ctx):
    try:
        await ctx.message.delete()
        global lottery_tickets
        lottery_channel = get(ctx.guild.text_channels, id=716396365126565919)
        if ctx.message.channel.id != 716396365126565919:
            await ctx.message.channel.send("You can only buy a ticket in #nova-lottery")
        else:
            await asyncio.sleep(1)
            gv = open('/NOVA/global_vars.json',"r")
            global_vars = json.load(gv)
            gv.close()
            cnx = mysql.connector.connect(
                converter_class=MyConverter,
                host="128.199.48.106",
                port="3306",
                user="nova",
                passwd="DiscordNovaP@ssw0rd@qais",
                database="nova_casino"
            )
            cursor = cnx.cursor()
            for key in persdict:
                if key == ctx.message.author.id:
                    lottery_user = persdict[ctx.message.author.id]['name'] + '-' + persdict[ctx.message.author.id]['serv']
                    break
                else:
                    lottery_user = ctx.message.author.nick
            query = "SELECT balance FROM gambling_prod WHERE name=\"" + lottery_user +"\""
            cursor.execute(query)
            lottery_user_balance = cursor.fetchone()[0]
            if lottery_user_balance == None:
                lottery_user_balance=0
            else:
                lottery_user_balance=lottery_user_balance
                
            query = "SELECT name FROM lottery_log"
            cursor.execute(query)
            lottery_tickets = cursor.fetchall()
            if lottery_user in str(lottery_tickets):
                await ctx.message.channel.send(f"{ctx.message.author.mention} you already have lottery ticket, ***1*** ticket per member __only__.", delete_after=10)
            elif int(lottery_user_balance) < 50000:
                await ctx.message.channel.send(f"{ctx.message.author.mention} doesnt have enough balance to buy a lottery ticket.", delete_after=10)
            else:
                now = datetime.utcnow()
                d1 = now.strftime("%d/%m/%Y %H:%M:%S")
                lottery_user_balance = lottery_user_balance - 50000
                gc.login()
                if lottery_user.endswith("[A]"):
                    gc.login()
                    A_val = alliance_gambling_sheet.cell(global_vars['alliance_counter_gambling'], 2).value
                    if A_val == None or A_val == "":
                        alliance_gambling_cells = [Cell(row=global_vars['alliance_counter_gambling'], col=2, value=d1),
                                                      Cell(row=global_vars['alliance_counter_gambling'], col=4, value=-50000),
                                                      Cell(row=global_vars['alliance_counter_gambling'], col=5, value="Lottery"),
                                                      Cell(row=global_vars['alliance_counter_gambling'], col=6, value=lottery_user.partition("-")[0]),
                                                      Cell(row=global_vars['alliance_counter_gambling'], col=7, value=lottery_user.partition("-")[2])]
                        alliance_gambling_sheet.update_cells(alliance_gambling_cells)
                        gv = open('/NOVA/global_vars.json',"w")
                        global_vars['alliance_counter_gambling']+=1
                        json.dump(global_vars,gv)
                        gv.close()
                        query = "UPDATE gambling_prod SET balance= %s WHERE name= %s"
                        val = (lottery_user_balance,lottery_user)
                        cursor.execute(query,val)
                        cnx.commit()
                        query = "INSERT INTO lottery_log (date, pot, name) VALUES (%s, %s, %s)"
                        val = (d1,50000,lottery_user)
                        cursor.execute(query,val)
                        cnx.commit()
                        query = "SELECT SUM(pot) FROM lottery_log"
                        cursor.execute(query)
                        lottery_pot = cursor.fetchone()[0]
                        cursor.close()
                        cnx.close()
                        async for message in lottery_channel.history(limit=50, oldest_first=True):
                            if message.id == 716560494160248893:
                                lottery_msg = message
                                lottery_embed_pre = message.embeds[0].to_dict()
                                lottery_embed_pre_fields = lottery_embed_pre['fields']
                                lottery_embed_pre_fields[1]["value"]= f"{int(lottery_pot):,d}"
                                lottery_update_embed = discord.Embed.from_dict(lottery_embed_pre)
                        await ctx.message.channel.send(f"{ctx.message.author.mention} ticket purchased, good luck", delete_after=10)
                        await lottery_msg.edit(embed=lottery_update_embed)
                    elif A_val != None or A_val != "":
                        await ctx.message.channel.send(f"{ctx.message.author.mention} error occured while purchasing the ticket, please try again or contact management", delete_after=10)
                elif lottery_user.endswith("[H]"):
                    gc.login()
                    H_val = horde_gambling_sheet.cell(global_vars['horde_counter_gambling'], 2).value
                    if H_val == None or H_val == "":
                        horde_gambling_cells = [Cell(row=global_vars['horde_counter_gambling'], col=2, value=d1),
                                                      Cell(row=global_vars['horde_counter_gambling'], col=4, value=-50000),
                                                      Cell(row=global_vars['horde_counter_gambling'], col=5, value="Lottery"),
                                                      Cell(row=global_vars['horde_counter_gambling'], col=6, value=lottery_user.partition("-")[0]),
                                                      Cell(row=global_vars['horde_counter_gambling'], col=7, value=lottery_user.partition("-")[2])]
                        horde_gambling_sheet.update_cells(horde_gambling_cells)
                        gv = open('/NOVA/global_vars.json',"w")
                        global_vars['horde_counter_gambling']+=1
                        json.dump(global_vars,gv)
                        gv.close()
                        query = "UPDATE gambling_prod SET balance= %s WHERE name= %s"
                        val = (lottery_user_balance,lottery_user)
                        cursor.execute(query,val)
                        cnx.commit()
                        query = "INSERT INTO lottery_log (date, pot, name) VALUES (%s, %s, %s)"
                        val = (d1,50000,lottery_user)
                        cursor.execute(query,val)
                        cnx.commit()
                        query = "SELECT SUM(pot) FROM lottery_log"
                        cursor.execute(query)
                        lottery_pot = cursor.fetchone()[0]
                        cursor.close()
                        cnx.close()
                        async for message in lottery_channel.history(limit=50, oldest_first=True):
                            if message.id == 716560494160248893:
                                lottery_msg = message
                                lottery_embed_pre = message.embeds[0].to_dict()
                                lottery_embed_pre_fields = lottery_embed_pre['fields']
                                lottery_embed_pre_fields[1]["value"]= f"{int(lottery_pot):,d}"
                                lottery_update_embed = discord.Embed.from_dict(lottery_embed_pre)
                        await ctx.message.channel.send(f"{ctx.message.author.mention} ticket purchased, good luck", delete_after=10)
                        await lottery_msg.edit(embed=lottery_update_embed)
                    elif H_val != None or H_val != "":
                        await ctx.message.channel.send(f"{ctx.message.author.mention} error occured while purchasing the ticket, please try again or contact management", delete_after=10)
                
    except Exception:
        logging.error(traceback.format_exc())
        await ctx.message.channel.send(f"{ctx.message.author.mention} error occured while purchasing the ticket, please try again or contact management", delete_after=10)
        bot_log_channel = get(ctx.guild.text_channels, name='bot-logs')
        embed_bot_log = discord.Embed(title="CASINO Error Log.", description=traceback.format_exc(), color=discord.Color.orange())
        embed_bot_log.add_field(name="Source", value="on lottery", inline=True)
        embed_bot_log.add_field(name="Author", value=ctx.message.author.nick, inline=True)
        embed_bot_log.add_field(name="Channel", value=ctx.channel.name, inline=False)
        embed_bot_log.add_field(name="Link", value=ctx.message.jump_url, inline=True)
        embed_bot_log.add_field(name="Content", value=ctx.message.content, inline=False)
        embed_bot_log.set_footer(text="Timestamp: " + d1)
        await bot_log_channel.send(embed=embed_bot_log)

@lottery.error
async def lottery_error(ctx, error):
    if isinstance(error, commands.MissingRole):
        em = discord.Embed(title="❌ Missing permissions",
                            description="",
                            color=discord.Color.red())
        await ctx.send(embed=em,delete_after=5)
    elif isinstance(error, commands.CommandNotFound):
        em = discord.Embed(title="❌ No Such Command",
                            description="",
                            color=discord.Color.red())
        await ctx.send(embed=em,delete_after=5)
    elif isinstance(error, commands.BadArgument):
        em = discord.Embed(title="❌ Bad arguments",
                            description="",
                            color=discord.Color.red())
        await ctx.send(embed=em,delete_after=5)
    elif isinstance(error, commands.MissingRequiredArgument):
        em = discord.Embed(title="❌ Missing arguments",
                            description="",
                            color=discord.Color.red())
        await ctx.send(embed=em,delete_after=5)
    elif isinstance(error, commands.CommandOnCooldown):
        em = discord.Embed(title="❌ On Cooldown",
                            description="You can buy a ticket once every 30 seconds, please try again in {:.2f}s".format(error.retry_after),
                            color=discord.Color.red())
        await ctx.send(embed=em,delete_after=error.retry_after)

#######################################
def check_if_it_saadi_stan_me(ctx):
    return ctx.message.author.id == 278172998496944128 or ctx.message.author.id == 226069789754392576 or ctx.message.author.id == 163324686086832129

@bot.command(pass_context=True)
@commands.has_any_role('Moderator','NOVA')
async def placeholder(ctx, faction: str):
    await ctx.message.delete()
    d1 = datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S")
    if faction.lower()== "alliance":
        #gc.login()
        #alliance_counter_gambling = alliance_find_empty_cell_gambling(alliance_gambling_sheet)
        gv = open('/NOVA/global_vars.json',"r")
        global_vars = json.load(gv)
        gv.close()
        await asyncio.sleep(1)
        alliance_gambling_cells = [Cell(row=global_vars['alliance_counter_gambling'], col=2, value=d1),
                                      Cell(row=global_vars['alliance_counter_gambling'], col=5, value="Placeholder")]
        alliance_gambling_sheet.update_cells(alliance_gambling_cells)
        gv = open('/NOVA/global_vars.json',"w")
        global_vars['alliance_counter_gambling']+=1
        json.dump(global_vars,gv)
        gv.close()
        ##alliance_counter_gambling = alliance_counter_gambling + 1
    elif faction.lower()== "horde":
        #gc.login()
        #horde_counter_gambling = horde_find_empty_cell_gambling(horde_gambling_sheet)
        gv = open('/NOVA/global_vars.json',"r")
        global_vars = json.load(gv)
        gv.close()
        await asyncio.sleep(1)
        horde_gambling_cells = [Cell(row=global_vars['horde_counter_gambling'], col=2, value=d1),
                                      Cell(row=global_vars['horde_counter_gambling'], col=5, value="Placeholder")]
        horde_gambling_sheet.update_cells(horde_gambling_cells)
        gv = open('/NOVA/global_vars.json',"w")
        global_vars['horde_counter_gambling']+=1
        json.dump(global_vars,gv)
        gv.close()
        ##horde_counter_gambling = horde_counter_gambling + 1


@bot.command(pass_context=True)
@commands.has_any_role('Moderator')
async def sendEmbed(ctx):
    await ctx.message.delete()
    lottery_embed=discord.Embed(title="💰Lottery info💰", description="", color=0x4feb1c)
    lottery_embed.set_thumbnail(url="https://cdn.discordapp.com/avatars/634917649335320586/ea303e8b580d56ff6837e256b1df6ef6.png")
    lottery_embed.add_field(name="**Current Ticket price: **", value="50K", inline=True)
    lottery_embed.add_field(name="**Current Prize Pool: **", value="--", inline=False)
    await ctx.message.channel.send(embed=lottery_embed)

@bot.command(pass_context=True)
@commands.has_any_role('Moderator')
async def resetEmbed(ctx, price: str):
    await ctx.message.delete()
    lottery_channel = get(ctx.guild.text_channels, id=716396365126565919)
    async for message in lottery_channel.history(limit=50, oldest_first=True):
        if message.id == 716560494160248893:
            lottery_msg = message
            lottery_embed_pre = message.embeds[0].to_dict()
            lottery_embed_pre_fields = lottery_embed_pre['fields']
            lottery_embed_pre_fields[0]["value"]= price
            lottery_embed_pre_fields[1]["value"]= "--"
            lottery_update_embed = discord.Embed.from_dict(lottery_embed_pre)
    await lottery_msg.edit(embed=lottery_update_embed)


@bot.command(pass_context=True)
@commands.has_any_role('Moderator')
async def pickWinners(ctx):
    try:
        cnx = mysql.connector.connect(
            converter_class=MyConverter,
            host="128.199.48.106",
            port="3306",
            user="nova",
            passwd="DiscordNovaP@ssw0rd@qais",
            database="nova_casino"
        )
        cursor = cnx.cursor()
        query = "SELECT name FROM lottery_log"
        cursor.execute(query)
        lottery_tickets = cursor.fetchall()
        winners_list = random.sample(lottery_tickets, 3)
        query = "SELECT SUM(pot) FROM lottery_log"
        cursor.execute(query)
        lottery_pot = cursor.fetchone()[0]
        cursor.close()
        cnx.close()
        lot_win_1_nick = str(winners_list[0]).replace("['","").replace("]'","")
        lot_win_2_nick = str(winners_list[1]).replace("['","").replace("]'","")
        lot_win_3_nick = str(winners_list[2]).replace("['","").replace("]'","")
        if lot_win_1_nick == "Windzorn-Silvermoon [A]":
            lot_win_1_nick = "Windzorn"
        elif lot_win_1_nick == "Aizagora-TwistingNether [H]":
            lot_win_1_nick = "Aízagora"
        elif lot_win_1_nick == "Saadi-Silvermoon [A]":
            lot_win_1_nick = "Saadi"
        elif lot_win_1_nick == "Killèr-TwistingNether [H]":
            lot_win_1_nick = "Killêr"
        elif lot_win_1_nick == "Ménex-Kazzak [H]":
            lot_win_1_nick = "Menex"
        elif lot_win_1_nick == "Sanfura-Ravencrest [A]":
            lot_win_1_nick = "Sanfura 🤖"
        elif lot_win_1_nick == "Stepstan-TwistingNether [H]":
            lot_win_1_nick = "Stan"
        elif lot_win_1_nick == "Miladtaker-Ravencrest [A]":
            lot_win_1_nick = "Adam"
        elif lot_win_1_nick == "Huntardson-TwistingNether [H]":
            lot_win_1_nick = "Laxus"
        elif lot_win_1_nick == "Nashiira-Sanguino [H]":
            lot_win_1_nick = "Nashiira"
        elif lot_win_1_nick == "Gnomesrock-Silvermoon [A]":
            lot_win_1_nick = "Gnomesrock"
        elif lot_win_1_nick == "Chiieff-TarrenMill [H]":
            lot_win_1_nick = "Chief"
        elif lot_win_1_nick == "Aiune-Tyrande [A]":
            lot_win_1_nick = "Aiune"
        elif lot_win_1_nick == "Durdy-TarrenMill [H]":
            lot_win_1_nick = "Durdy"
        elif lot_win_1_nick == "Revisdh-TarrenMill [H]":
            lot_win_1_nick = "Revis"
        elif lot_win_1_nick == "Lîza-TarrenMill [H]":
            lot_win_1_nick = "Liza"
        elif lot_win_1_nick == "Kurtcôwbain-Illidan [H]":
            lot_win_1_nick = "Kurt"

        if lot_win_2_nick == "Windzorn-Silvermoon [A]":
            lot_win_2_nick = "Windzorn"
        elif lot_win_2_nick == "Aizagora-TwistingNether [H]":
            lot_win_2_nick = "Aízagora"
        elif lot_win_2_nick == "Saadi-Silvermoon [A]":
            lot_win_2_nick = "Saadi"
        elif lot_win_2_nick == "Killèr-TwistingNether [H]":
            lot_win_2_nick = "Killêr"
        elif lot_win_2_nick == "Ménex-Kazzak [H]":
            lot_win_2_nick = "Menex"
        elif lot_win_2_nick == "Sanfura-Ravencrest [A]":
            lot_win_2_nick = "Sanfura 🤖"
        elif lot_win_2_nick == "Stepstan-TwistingNether [H]":
            lot_win_2_nick = "Stan"
        elif lot_win_2_nick == "Miladtaker-Ravencrest [A]":
            lot_win_2_nick = "Adam"
        elif lot_win_2_nick == "Huntardson-TwistingNether [H]":
            lot_win_2_nick = "Laxus"
        elif lot_win_2_nick == "Nashiira-Sanguino [H]":
            lot_win_2_nick = "Nashiira"
        elif lot_win_2_nick == "Gnomesrock-Silvermoon [A]":
            lot_win_2_nick = "Gnomesrock"
        elif lot_win_2_nick == "Chiieff-TarrenMill [H]":
            lot_win_2_nick = "Chief"
        elif lot_win_2_nick == "Aiune-Tyrande [A]":
            lot_win_2_nick = "Aiune"
        elif lot_win_2_nick == "Durdy-TarrenMill [H]":
            lot_win_2_nick = "Durdy"
        elif lot_win_2_nick == "Revisdh-TarrenMill [H]":
            lot_win_2_nick = "Revis"
        elif lot_win_2_nick == "Lîza-TarrenMill [H]":
            lot_win_2_nick = "Liza"
        elif lot_win_2_nick == "Kurtcôwbain-Illidan [H]":
            lot_win_2_nick = "Kurt"
            
        if lot_win_3_nick == "Windzorn-Silvermoon [A]":
            lot_win_3_nick = "Windzorn"
        elif lot_win_3_nick == "Aizagora-TwistingNether [H]":
            lot_win_3_nick = "Aízagora"
        elif lot_win_3_nick == "Saadi-Silvermoon [A]":
            lot_win_3_nick = "Saadi"
        elif lot_win_3_nick == "Killèr-TwistingNether [H]":
            lot_win_3_nick = "Killêr"
        elif lot_win_3_nick == "Ménex-Kazzak [H]":
            lot_win_3_nick = "Menex"
        elif lot_win_3_nick == "Sanfura-Ravencrest [A]":
            lot_win_3_nick = "Sanfura 🤖"
        elif lot_win_3_nick == "Stepstan-TwistingNether [H]":
            lot_win_3_nick = "Stan"
        elif lot_win_3_nick == "Miladtaker-Ravencrest [A]":
            lot_win_3_nick = "Adam"
        elif lot_win_3_nick == "Huntardson-TwistingNether [H]":
            lot_win_3_nick = "Laxus"
        elif lot_win_3_nick == "Nashiira-Sanguino [H]":
            lot_win_3_nick = "Nashiira"
        elif lot_win_3_nick == "Gnomesrock-Silvermoon [A]":
            lot_win_3_nick = "Gnomesrock"
        elif lot_win_3_nick == "Chiieff-TarrenMill [H]":
            lot_win_3_nick = "Chief"
        elif lot_win_3_nick == "Aiune-Tyrande [A]":
            lot_win_3_nick = "Aiune"
        elif lot_win_3_nick == "Durdy-TarrenMill [H]":
            lot_win_3_nick = "Durdy"
        elif lot_win_3_nick == "Revisdh-TarrenMill [H]":
            lot_win_3_nick = "Revis"
        elif lot_win_3_nick == "Lîza-TarrenMill [H]":
            lot_win_3_nick = "Liza"
        elif lot_win_3_nick == "Kurtcôwbain-Illidan [H]":
            lot_win_3_nick = "Kurt"
            
        print(f"{lot_win_1_nick}\n{lot_win_2_nick}\n{lot_win_3_nick}")
            
        lottery_winner_1 = get(ctx.guild.members, nick=lot_win_1_nick)
        lottery_winner_2 = get(ctx.guild.members, nick=lot_win_2_nick)
        lottery_winner_3 = get(ctx.guild.members, nick=lot_win_3_nick)
        lottery_embed=discord.Embed(title="💰Lottery winners💰", description="", color=0x4feb1c)
        lottery_embed.set_thumbnail(url="https://cdn.discordapp.com/avatars/634917649335320586/ea303e8b580d56ff6837e256b1df6ef6.png")
        lottery_embed.add_field(name="🥇", value=f"**First place:** {lottery_winner_1.mention} <:goldss:606863829980282940> {int(lottery_pot*65/100):,d}", inline=True)
        lottery_embed.add_field(name="🥈", value=f"**Second place:** {lottery_winner_2.mention} <:goldss:606863829980282940> {int(lottery_pot*15/100):,d}", inline=False)
        lottery_embed.add_field(name="🥉", value=f"**Third place:** {lottery_winner_3.mention} <:goldss:606863829980282940> {int(lottery_pot*5/100):,d}", inline=False)
        lottery_embed.set_footer(text="Timestamp (UTC±00:00): " + datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S"))
        await ctx.message.channel.send(embed=lottery_embed)
    except Exception:
        logging.error(traceback.format_exc())
        bot_log_channel = get(ctx.guild.text_channels, name='bot-logs')
        embed_bot_log = discord.Embed(title="CASINO Error Log.", description=traceback.format_exc(), color=discord.Color.orange())
        embed_bot_log.add_field(name="Source", value="on pickWinners", inline=True)
        embed_bot_log.add_field(name="Author", value=ctx.message.author.nick, inline=True)
        embed_bot_log.add_field(name="Channel", value=ctx.channel.name, inline=False)
        embed_bot_log.add_field(name="Link", value=ctx.message.jump_url, inline=True)
        embed_bot_log.add_field(name="Content", value=ctx.message.content, inline=False)
        embed_bot_log.set_footer(text="Timestamp: " + datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S"))
        await bot_log_channel.send(embed=embed_bot_log)


async def balanceSync(agcm):
    
    try:
        while True:
            logging.info("ImportBalance_loop started")
            guild = bot.get_guild(606853414780928021)
            casino_channel = get(guild.text_channels, id=695699820144361554)
            lottery_channel = get(guild.text_channels, id=716396365126565919)
            alliance_role = get(guild.roles, name="Alliance")
            horde_role = get(guild.roles, name="Horde")
            await casino_channel.set_permissions(alliance_role, send_messages=False, read_messages=True, read_message_history=True)
            await lottery_channel.set_permissions(alliance_role, send_messages=False, read_messages=True, read_message_history=True)
            
            await casino_channel.set_permissions(horde_role, send_messages=False, read_messages=True, read_message_history=True)
            await lottery_channel.set_permissions(horde_role, send_messages=False, read_messages=True, read_message_history=True)
            
            em = discord.Embed(title="Synchronization",
                                    description=random.choice(sync_msg),
                                    color=discord.Color.red())
            casino_sync_start_msg = await casino_channel.send(embed=em)
            lottery_sync_start_msg = await lottery_channel.send(embed=em)
        
        #####################################################################################
            
            agc = await agcm.authorize()
            
            alliance_sheet = await agc.open("Alliance Board - Active")
            horde_sheet = await agc.open("Horde Board - Active")
            alliance_gambling_sheet = await alliance_sheet.worksheet("Gambling")
            alliance_coreData_sheet = await alliance_sheet.worksheet("CoreData")
            horde_gambling_sheet = await horde_sheet.worksheet("Gambling")
            horde_coreData_sheet = await horde_sheet.worksheet("CoreData")
            alliance_rich_names = await alliance_coreData_sheet.batch_get(["FP3:FP"]) #FP Col Names
            alliance_rich_realms = await alliance_coreData_sheet.batch_get(["FQ3:FQ"]) #FQ Col Realms
            alliance_rich_balances = await alliance_coreData_sheet.batch_get(["FR3:FR"]) #FR Col Balances
            
            horde_rich_names = await horde_coreData_sheet.batch_get(["FP3:FP"]) #FP Col Names
            horde_rich_realms = await horde_coreData_sheet.batch_get(["FQ3:FQ"]) #FQ Col Realms
            horde_rich_balances = await horde_coreData_sheet.batch_get(["FR3:FR"]) #FR Col Balances
            
            i=0
            val=[]
            for item in alliance_rich_realms[0]:
                if i <= len(alliance_rich_realms[0]):
                    val.append([int(alliance_rich_balances[0][i][0].replace(',','')),(alliance_rich_names[0][i][0]+"-"+alliance_rich_realms[0][i][0])])
                    i+=1
                
            i=0
            for item in horde_rich_realms[0]:
                if i <= len(horde_rich_realms[0]):
                   test_res=f"{horde_rich_names[0][i][0]}-{horde_rich_realms[0][i][0]}"
                   if (horde_rich_names[0][i][0]+"-"+horde_rich_realms[0][i][0]) in [elem for sublist in val for elem in sublist]:
                       out = [(ind,ind2) for ind,i in enumerate(val) for ind2,y in enumerate(i) if y == test_res]
                       val[out[0][0]][0]=val[out[0][0]][0]+int(horde_rich_balances[0][i][0].replace(',',''))
                   else:
                       val.append([int(horde_rich_balances[0][i][0].replace(',','')),(horde_rich_names[0][i][0]+"-"+horde_rich_realms[0][i][0])])
                   i+=1
        #########################################################################################         
            cnx = mysql.connector.connect(
                    host="128.199.48.106",
                    port="3306",
                    user="nova",
                    passwd="DiscordNovaP@ssw0rd@qais",
                    database="nova_casino"
                )
            bal_loop_cursor = cnx.cursor()
            query = "UPDATE gambling_prod SET balance=0"
            bal_loop_cursor.execute(query)
            cnx.commit()
            query = "UPDATE gambling_prod SET balance=%s WHERE name=%s"
            bal_loop_cursor.executemany(query,val)
            cnx.commit()
            bot_log_channel = get(guild.text_channels, name='bot-logs')
            await bot_log_channel.send(f"{len(val)} record(s) affected")
            bal_loop_cursor.close()
            cnx.close()
            ########################################################################################################
            logging.info("ImportBalance_loop ended")
            await casino_sync_start_msg.delete()
            await lottery_sync_start_msg.delete()
            em = discord.Embed(title="Synchronization",
                                    description="Balance synchronization completed!",
                                    color=discord.Color.green())
            await casino_channel.send(embed=em,delete_after=5)
            await lottery_channel.send(embed=em,delete_after=5)
            await casino_channel.set_permissions(alliance_role, send_messages=True, read_messages=True, read_message_history=True)
            await lottery_channel.set_permissions(alliance_role, send_messages=True, read_messages=True, read_message_history=True)
            await casino_channel.set_permissions(horde_role, send_messages=True, read_messages=True, read_message_history=True)
            await lottery_channel.set_permissions(horde_role, send_messages=True, read_messages=True, read_message_history=True)
            await asyncio.sleep(3600)
    except Exception:
        logging.error(traceback.format_exc())
        bot_log_channel = get(guild.text_channels, name='bot-logs')
        embed_bot_log = discord.Embed(title="Casino Error Log.", description=traceback.format_exc(), color=discord.Color.orange())
        embed_bot_log.add_field(name="Source", value="on importBalance Loop", inline=True)
        embed_bot_log.set_footer(text=datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S"))
        await bot_log_channel.send(embed=embed_bot_log)


@tasks.loop(minutes=60)
async def ImportBalance_loop():
    #global val
    try:
        logging.info("ImportBalance_loop started")
        guild = bot.get_guild(606853414780928021)
        casino_channel = get(guild.text_channels, id=695699820144361554)
        lottery_channel = get(guild.text_channels, id=716396365126565919)
        alliance_role = get(guild.roles, name="Alliance")
        horde_role = get(guild.roles, name="Horde")
        await casino_channel.set_permissions(alliance_role, send_messages=False, read_messages=True, read_message_history=True)
        await lottery_channel.set_permissions(alliance_role, send_messages=False, read_messages=True, read_message_history=True)
        
        await casino_channel.set_permissions(horde_role, send_messages=False, read_messages=True, read_message_history=True)
        await lottery_channel.set_permissions(horde_role, send_messages=False, read_messages=True, read_message_history=True)
        
        em = discord.Embed(title="Synchronization",
                                description=random.choice(sync_msg),
                                color=discord.Color.red())
        casino_sync_start_msg = await casino_channel.send(embed=em)
        lottery_sync_start_msg = await lottery_channel.send(embed=em)
        
        #asyncio.run(balanceSync(agcm))
        
        cnx = mysql.connector.connect(
                host="128.199.48.106",
                port="3306",
                user="nova",
                passwd="DiscordNovaP@ssw0rd@qais",
                database="nova_casino"
            )
        bal_loop_cursor = cnx.cursor()
        query = "UPDATE gambling_prod SET balance=0"
        bal_loop_cursor.execute(query)
        cnx.commit()
        query = "UPDATE gambling_prod SET balance=%s WHERE name=%s"
        bal_loop_cursor.executemany(query,val)
        cnx.commit()
        bot_log_channel = get(guild.text_channels, name='bot-logs')
        await bot_log_channel.send(f"{len(val)} record(s) affected")
        bal_loop_cursor.close()
        cnx.close()
        ########################################################################################################
        logging.info("ImportBalance_loop ended")
        await casino_sync_start_msg.delete()
        await lottery_sync_start_msg.delete()
        em = discord.Embed(title="Synchronization",
                                description="Balance synchronization completed!",
                                color=discord.Color.green())
        await casino_channel.send(embed=em,delete_after=5)
        await lottery_channel.send(embed=em,delete_after=5)
        await casino_channel.set_permissions(alliance_role, send_messages=True, read_messages=True, read_message_history=True)
        await lottery_channel.set_permissions(alliance_role, send_messages=True, read_messages=True, read_message_history=True)
        await casino_channel.set_permissions(horde_role, send_messages=True, read_messages=True, read_message_history=True)
        await lottery_channel.set_permissions(horde_role, send_messages=True, read_messages=True, read_message_history=True)
    except Exception:
        logging.error(traceback.format_exc())
        bot_log_channel = get(guild.text_channels, name='bot-logs')
        embed_bot_log = discord.Embed(title="Casino Error Log.", description=traceback.format_exc(), color=discord.Color.orange())
        embed_bot_log.add_field(name="Source", value="on importBalance Loop", inline=True)
        embed_bot_log.set_footer(text=datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S"))
        await bot_log_channel.send(embed=embed_bot_log)
    
bot.run(token)