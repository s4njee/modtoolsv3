import logging
from datetime import timedelta
from pprint import pprint

import config
import datetime
import discord
import praw
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from b import Session
from discord.ext import commands
from models import ModLog, ModQueueItem, DiscordAction, Report, ModMailConversation, ModMailMessage
from prawmod import bot
from sqlalchemy import func, desc, or_
from sqlalchemy.sql import exists


logging.basicConfig()
#logging.getLogger('apscheduler').setLevel(logging.DEBUG)

# Base.metadata.create_all(engine)
# Create SqlAlchemy Session
session = Session()


# create scheduler for separate jobs
sched = AsyncIOScheduler()



# create discord client
BOT_PREFIX = ("!")
client = commands.Bot(command_prefix=BOT_PREFIX)

moderatorsList = bot.subreddit('nba').moderator()
moderators = []
for mod in moderatorsList:
    moderators.append(mod.name)
print(moderators)


# login message for discord client
@client.event
async def on_ready():
    print("We have logged in as {0.user}".format(client))


# Awaits User Command, Returns Modlist and corresponding emoji.

@client.command(brief='Shows emojis associated with each mod')
async def modlist(ctx):
    modlist = 'Mod: Emoji\n'
    for mod in config.modemojis.keys():
        if config.modemojis[mod] == 1:
            modlist = modlist + mod + ": <:" + config.modemojis[mod] + ">\n"
        else:
            modlist = modlist + mod + ": " + config.modemojis[mod] + "\n"
    await ctx.send(modlist)


# Awaits User Command, Return who the mod is based on the emoji
@client.command(brief='input an emoji to this command and see which mod it belongs to')
async def whois(ctx, *args):
    modreturn = ''
    for arg in args:
        for mod in config.modemojis.keys():
            if config.modemojis[mod] == 1:
                if arg == "<:" + config.modemojis[mod] + ">":
                    modreturn = modreturn + arg + ": " + mod + "\n"
            else:
                print(mod)
                print(config.modemojis[mod])
                if arg == config.modemojis[mod]:
                    modreturn = modreturn + arg + ": " + mod + "\n"
    if modreturn != '':
        await ctx.send(modreturn)
    else:
        await ctx.send("There are no moderators with these emojis: {}".format(', '.join(args)))


@client.command(brief='input username and see how many times they have appeared in modlog')
async def modlog(ctx, arg):
    channel = client.get_channel(int(config.commandchannel))
    if ctx.channel == channel:
        logs = session.query(ModLog.action, func.count(ModLog.action)).filter(ModLog.target_author == arg).\
            group_by(ModLog.action).all()
        message = 'Modlogs for user: ' + arg + "\n"
        messages = []
        for item in logs:
            if len(message) > 1000:
                messages.append(message[:-2])
                message = ''
            message += item[0] + '|' + str(item[1]) + '\n'

        if message != '':
            messages.append(message)
        for message in messages:
            await channel.send(message)


@client.command(brief='see how many removals(comments/links) for user')
async def removed(ctx, arg):
    channel = client.get_channel(int(config.commandchannel))
    if ctx.channel == channel:
        logs = session.query(ModLog.action, func.count(ModLog.action)).\
            filter(ModLog.target_author == arg, or_(ModLog.action == 'removelink', ModLog.action == 'removecomment'))\
            .group_by(ModLog.action).all()
        message = 'Removed for user: ' + arg + "\n"
        messages = []
        for item in logs:
            if len(message) > 1000:
                messages.append(message)
                message = ''
            message += item[0] + '|' + str(item[1]) + '\n'

        if message != '':
            messages.append(message)
        for message in messages:
            print(message)
            await channel.send(message)


@client.command(brief='input username to see how often user appeared in modmail')
async def modmail(ctx, arg):
    channel = client.get_channel(int(config.commandchannel))
    if ctx.channel == channel:
        mail = session.query(ModMailConversation.subject, ModMailConversation.participant, ModMailConversation.id, ModMailConversation.date)\
            .outerjoin(ModMailMessage, ModMailMessage.author == ModMailConversation.participant)\
            .distinct(ModMailConversation.id)\
            .filter(func.lower(ModMailConversation.participant) == func.lower(arg))\
            .order_by(ModMailConversation.id.desc()).all()
        await channel.send(str(len(mail))+ " modmail found for " + arg)
        message = ''
        messages = []
        for item in mail:
            if len(message) > 1000:
                messages.append(message[:-2])
                message = ''
            message += item.subject + " | https://mod.reddit.com/mail/archived/" + item.id + '\r\n'

        if message != '':
            messages.append(message[:-2])
        for message in messages:
            await channel.send(message)

@client.command(brief='input time to see mod statistics for timespan ')
async def mod(ctx, time='24'):
    if time == 'week':
        time = 168
    elif time == 'month':
        time = 730
    elif time == 'year':
        time = 8760
    elif time == 'all':
        time = 175200
    else:
        time = int(time)
    channel = client.get_channel(int(config.commandchannel))
    if ctx.channel == channel:
        activity = session.query(ModLog.mod, func.count(ModLog.mod).label('total')) \
            .filter(ModLog.action != 'approvelink', ModLog.date >= datetime.datetime.now() - timedelta(hours=time)) \
            .group_by(ModLog.mod).order_by(desc('total'))
        mails = session.query(ModMailMessage.author, func.count(ModMailMessage.author).label('total')) \
            .filter(ModMailMessage.author.in_(moderators),
                    ModMailMessage.date >= datetime.datetime.now() - timedelta(hours=time),
                    ~ModMailMessage.body.contains('Reminder from the Reddit staff')) \
            .group_by(ModMailMessage.author).order_by(desc('total'))
        em = discord.Embed()
        em.timestamp = datetime.datetime.utcnow()
        em.set_footer(text='posted on')
        amessage = ''
        for mod in activity:
            amessage += mod[0] + '|' + str(mod[1]) + '\n'
        mmessage = ''
        for mod in mails:
            mmessage += mod[0] + '|' + str(mod[1]) + '\n'
        if amessage != '':
            em.add_field(name='MODLOG', value=amessage, inline=True)
        if mmessage != '':
            em.add_field(name='MODMAIL', value=mmessage, inline=True)
        if amessage == '' and mmessage == '':
            em.add_field(name="Results", value='Nothings happened recently', inline=True)
        await ctx.send(embed=em)

@client.command(brief='similar to !mod but filters only for when mod has banned')
async def modbans(ctx, time='24'):
    if time == 'week':
        time = 168
    elif time == 'month':
        time = 730
    elif time == 'year':
        time = 8760
    elif time == 'all':
        time = 175200
    else:
        time = int(time)
    channel = client.get_channel(int(config.commandchannel))
    if ctx.channel == channel:
        activity = session.query(ModLog.mod, func.count(ModLog.mod).label('total')) \
            .filter(ModLog.action == 'banuser', ModLog.date >= datetime.datetime.now() - timedelta(hours=time)) \
            .group_by(ModLog.mod).order_by(desc('total'))
        mails = session.query(ModMailMessage.author, func.count(ModMailMessage.author).label('total')) \
            .filter(ModMailMessage.author.in_(moderators),
                    ModMailMessage.date >= datetime.datetime.now() - timedelta(hours=time),
                    ModMailMessage.body.contains('Reminder from the Reddit staff')) \
            .group_by(ModMailMessage.author).order_by(desc('total'))
        em = discord.Embed()
        em.timestamp = datetime.datetime.utcnow()
        em.set_footer(text='posted on')
        amessage = ''
        for mod in activity:
            amessage += mod[0] + '|' + str(mod[1]) + '\n'
        mmessage = ''
        for mod in mails:
            mmessage += mod[0] + '|' + str(mod[1]) + '\n'
        if amessage != '':
            em.add_field(name='MODLOG', value=amessage, inline=True)
        if mmessage != '':
            em.add_field(name='MODMAIL', value=mmessage, inline=True)
        if amessage == '' and mmessage == '':
            em.add_field(name="Results", value='Nothings happened recently', inline=True)
        await ctx.send(embed=em)
@client.command(brief='similar to !mod, but filters for when mod has unbanned')
async def modunbans(ctx, time='24'):
    if time == 'week':
        time = 168
    elif time == 'month':
        time = 730
    elif time == 'year':
        time = 8760
    elif time == 'all':
        time = 175200
    else:
        time = int(time)
    channel = client.get_channel(int(config.commandchannel))
    if ctx.channel == channel:
        activity = session.query(ModLog.mod, func.count(ModLog.mod).label('total')) \
            .filter(ModLog.action == 'unbanuser', ModLog.date >= datetime.datetime.now() - timedelta(hours=time)) \
            .group_by(ModLog.mod).order_by(desc('total'))
        em = discord.Embed()
        em.timestamp = datetime.datetime.utcnow()
        em.set_footer(text='posted on')
        amessage = ''
        for mod in activity:
            amessage += mod[0] + '|' + str(mod[1]) + '\n'
        if amessage != '':
            em.add_field(name='MODLOG', value=amessage, inline=True)
        if amessage == '':
            em.add_field(name="Results", value='Nothings happened recently', inline=True)
        await ctx.send(embed=em)

# adds moderation log to db every minute
@sched.scheduled_job("cron", second=30, misfire_grace_time=30)
async def addModlogs():
    # Get subreddit moderation logs
    for log in bot.subreddit(config.subreddit).mod.log(limit=100):

        d = datetime.datetime.fromtimestamp(log.created_utc)
        # Create ModLog item to insert into modlogs table
        m = ModLog(
            id=log.id,
            target_body=log.target_body,
            mod_id36=log.mod_id36,
            date=d,
            created_utc=log.created_utc,
            subreddit=log.subreddit,
            target_title=log.target_title,
            target_permalink=log.target_permalink,
            details=log.details,
            action=log.action,
            target_author=log.target_author,
            target_fullname=log.target_fullname,
            sr_id36=log.sr_id36,
            mod=log.mod.name,
        )

        if log.action == "approvelink" or log.action == "approvecomment":
            message = (
                session.query(DiscordAction)
                    .filter(DiscordAction.id == log.target_fullname.split("_")[1])
                    .first()
            )
            if message:
                messageID = message.messageID
                if log.target_body is None:
                    log.target_body = " "
                a = DiscordAction(
                    id=log.id,
                    action="approvereact",
                    messageID=messageID,
                    target_id=log.mod.name,
                    date=d,
                    link=log.target_permalink,
                    text=log.target_body[:2595],
                    target_type=log.action,
                    target_channel=config.channel,
                )
                session.merge(a)
        elif log.action == "removelink" or log.action == "removecomment":
            message = (
                session.query(DiscordAction)
                    .filter(DiscordAction.id == log.target_fullname.split("_")[1])
                    .first()
            )
            if message:
                messageID = message.messageID
                if log.target_body is None:
                    log.target_body = " "
                a = DiscordAction(
                    id=log.id,
                    action="removereact",
                    messageID=messageID,
                    target_id=log.mod.name,
                    date=d,
                    link=log.target_permalink,
                    text=log.target_body[:2595],
                    target_type=log.action,
                    target_channel=config.channel,
                )
                session.merge(a)
        # Merge + commit item to db
        try:
            session.merge(m)
            session.commit()
        except Exception as e:
            print(e)


# adds modqueue items every minute
@sched.scheduled_job("interval", seconds=30, misfire_grace_time=30)
def addModQueueItems():
    for item in bot.subreddit(config.subreddit).mod.modqueue(limit=None):
        try:
            if item.author is None:
                d = datetime.datetime.fromtimestamp(item.created_utc)
                m = ModQueueItem(
                    id=item.id,
                    link_title=item.link_title,
                    posttype="comment",
                    link_id=item.link_id,
                    author='deleted',
                    date=d,
                    edited=item.edited,
                    body=item.body,
                    permalink=item.permalink,
                )
                message = (
                    session.query(DiscordAction)
                        .filter(DiscordAction.id == item.id)
                        .first()
                )
                if message:
                    messageID = message.messageID
                    a = DiscordAction(
                        id=item.id,
                        action="deletereact",
                        messageID=messageID,
                        target_id="",
                        date=d,
                        link=item.permalink,
                        text=item.body,
                        target_type='deleted',
                        target_channel=config.channel,
                    )
                    session.merge(m)
                    session.merge(a)
                    session.commit()
        except Exception:
            print(e)
        if item.removed == True:
            print(pprint.pprint(vars(item)))
        session = Session()
        if item.edited == False:
            item.edited = 0
        if not session.query(exists().where(ModQueueItem.id == item.id)).scalar():
            d = datetime.datetime.fromtimestamp(item.created_utc)
            if type(item) != praw.models.reddit.submission.Submission:
                m = ModQueueItem(
                    id=item.id,
                    link_title=item.link_title,
                    posttype="comment",
                    link_id=item.link_id,
                    author=item.author.name,
                    date=d,
                    edited=item.edited,
                    body=item.body,
                    permalink=item.permalink,
                )
                a = DiscordAction(
                    action="sendmessage",
                    link=item.permalink,
                    text=item.body,
                    date=d,
                    target_id=None,
                    target_type="comment",
                    id=item.id,
                    completed=False,
                    target_user=item.author.name,
                    target_channel=config.channel,
                )
            else:
                m = ModQueueItem(
                    id=item.id,
                    posttype="submission",
                    link_title=item.title,
                    link_id=None,
                    author=item.author.name,
                    date=d,
                    edited=item.edited,
                    body=None,
                    permalink=item.permalink,
                )
                a = DiscordAction(
                    action="sendmessage",
                    link=item.permalink,
                    text=item.title,
                    target_id=None,
                    date=d,
                    target_type="submission",
                    id=item.id,
                    completed=False,
                    target_user=item.author.name,
                    target_channel=config.channel,
                )
            session.merge(m)

            if not session.query(exists().where(DiscordAction.id == item.id)).scalar():
                session.merge(a)
            session.commit()


# adds reports every minute
@sched.scheduled_job("cron", second=5, misfire_grace_time=30)
def addReports():
    for item in bot.subreddit(config.subreddit).mod.reports(limit=None):
        d = datetime.datetime.fromtimestamp(item.created_utc)
        for report in item.user_reports:
            session = Session()
            if report[0] is not None:
                r = Report(id=item.id, reason=report[0], count=str(report[1]), date=d)
                session.merge(r)
                session.commit()
        for report in item.mod_reports:
            session = Session()
            if report[0] is not None:
                r = Report(id=item.id, reason=report[0], count=report[1], date=d)
                session.merge(r)
                session.commit()
# @sched.scheduled_job("cron", second=30, misfire_grace_time=30)
# def addModMail(after='9u6m5', i=0, mmid=None):
#     print(i)
#     conversations = bot.subreddit(config.subreddit).modmail.conversations(after=after, state="archived", limit=500)
#     for c in conversations:
#         if c.participant:
#             mmc = ModMailConversation(
#                 id=c.id,
#                 participant=c.participant.name,
#                 subject=c.subject,
#                 date=c.last_updated,
#             )
#             i += 1
#             mmid = c.id
#             session.merge(mmc)
#             session.commit()
#             count = 0
#             print(mmc.date, file=open('./modmail.txt','a'))
#             for message in c.messages:
#                 if not hasattr(message,'date'):
#                     message.date = c.last_mod_update
#                 m = ModMailMessage(
#                     id = message.id,
#                     conversation_id = c.id,
#                     body = message.body,
#                     author = message.author.name,
#                     date = message.date
#                 )
#                 count += 1
#                 session.merge(m)
#                 session.commit()
#     addModMail(after=mmid, i=i)

@sched.scheduled_job("cron", second=30, misfire_grace_time=30)
def addModMail():
    conversations = bot.subreddit(config.subreddit).modmail.conversations(state="all", limit=100)
    session = Session()
    for c in conversations:
        if c.participant:
            mmc = ModMailConversation(
                id=c.id,
                participant=c.participant.name,
                subject=c.subject,
                date=c.last_updated,
            )
            a = DiscordAction(
                id=c.id,
                target_user=c.participant.name,
                action="sendmodmailmessage",
                date=c.last_updated,
                link="https://mod.reddit.com/mail/all/" + c.id,
                text=c.messages[-1].body_markdown,
                target_type="modmail",
                target_id=c.subject,
            )
            for message in c.messages:
                if not hasattr(message,'date'):
                    message.date = datetime.datetime.now()
                m = ModMailMessage(
                    id = message.id,
                    conversation_id = c.id,
                    body = message.body,
                    author = message.author.name,
                    date = message.date
                )
                session.merge(m)
                session.commit()

            session.merge(mmc)
            session.merge(a)
            session.commit()


# processes actions placed in discordactions table
@sched.scheduled_job("cron", second=45, misfire_grace_time=30)
async def processDiscordActions():
    session = Session()
    items = session.query(DiscordAction).filter(DiscordAction.completed == False).all()
    for item in items:
        if item.action == "sendmessage":
            item.completed = True
            session.commit()
            channel = client.get_channel(int(config.channel))
            reports = session.query(Report).filter(Report.id == item.id)
            embed = discord.Embed(
                title=item.target_type + " by /u/" + item.target_user,
                description=item.text[:2047],
                color=0x00ff00,
                url="http://reddit.com" + item.link,
            )
            for r in reports:
                embed.add_field(name=r.reason, value=r.count)
            await channel.send(embed=embed)
            messages = await channel.history().flatten()
            item.messageID = messages[0].id
            session.commit()
        if item.action == "sendmodmailmessage":
            channel = client.get_channel(int(config.channel))
            embed = discord.Embed(
                title="MODMAIL: " + item.target_id + " by /u/" + item.target_user,
                color=0xff0000,
                url=item.link,
            )
            item.completed = True
            session.commit()
            conversation = bot.subreddit(config.subreddit).modmail(
                item.id, mark_read=True
            )
            mentions = []
            for c in conversation.messages:
                mmm = ModMailMessage(
                    id=c.id,
                    conversation_id=conversation.id,
                    body=c.body_markdown,
                    author=c.author.name,
                    date=c.date
                )
                session.merge(mmm)
                try:
                    if c.author.name in config.discordIDs:
                        mentions.append("<@" + config.discordIDs[c.author.name] + ">")
                    embed.add_field(
                        name=c.author.name, value=c.body_markdown[:1023], inline=False
                    )
                except Exception:
                    pass
            await channel.send(embed=embed)
            try:
                if conversation.messages[-1].author.name not in config.discordIDs:
                    await channel.send(" ")
                    # await channel.send(" ".join(set(mentions)))
            except Exception:
                pass
            messages = await channel.history().flatten()
            item.messageID = messages[0].id
            session.commit()
        elif item.action == "removereact":
            react = "\u274c"
        elif item.action == "approvereact":
            react = "\u2705"
        elif item.action == "deletereact":
            react = "🚮"
        if item.action == "approvereact" or item.action == "removereact" or item.action == 'deletereact':
            print('deletereact')
            channel = client.get_channel(int(config.channel))
            if item.messageID:
                message = await channel.fetch_message(item.messageID)
                messageSQLobject = (
                    session.query(DiscordAction)
                        .filter(DiscordAction.messageID == str(message.id))
                        .first()
                )
                messageSQLobject.reactcompleted = True
                await message.add_reaction(react)
                if item.target_id and item.target_id in config.modemojis:
                    await message.add_reaction(config.modemojis[item.target_id])
                item.completed = True
                session.commit()
sched.start()
client.run(config.discordtoken)
