import os
import discord
import copy
from discord.ext import commands
from .utils.dataIO import dataIO
import random

class SmartReact:

    """Create automatic reactions when trigger words are typed in chat"""

    def __init__(self, bot):
        self.bot = bot
        self.settings_path = "data/smortreacts/settings.json"
        self.settings = dataIO.load_json(self.settings_path)
        self.NONWORDS = set(" ~!@#$%^&*()_=+`'\"/.,;:\\|[]\{\}<>")

    @commands.command(name="addreact", no_pm=True, pass_context=True)
    async def addreact(self, ctx, word, emoji, chance=0.1):
        """Add an auto reaction to a word"""
        server = ctx.message.server
        message = ctx.message
        self.load_settings(server.id)
        emoji = self.fix_custom_emoji(emoji)
        await self.create_smart_reaction(server, word, emoji, message, chance)

    @commands.command(name="delreact", no_pm=True, pass_context=True)
    async def delreact(self, ctx, word, emoji):
        """Delete an auto reaction to a word"""
        server = ctx.message.server
        message = ctx.message
        self.load_settings(server.id)
        emoji = self.fix_custom_emoji(emoji)
        await self.remove_smart_reaction(server, word, emoji, message)

    def load_settings(self, server_id):
        self.settings = dataIO.load_json(self.settings_path)
        if server_id not in self.settings.keys():
            self.add_default_settings(server_id)

    def add_default_settings(self, server_id):
        self.settings[server_id] = {}
        dataIO.save_json(self.settings_path, self.settings)

    def fix_custom_emoji(self, emoji):
        try:
            if emoji[:2] != "<:":
                return emoji
            return [r for server in self.bot.servers for r in server.emojis if r.id == emoji.split(':')[2][:-1]][0]
        except IndexError:
            return None

    # From Twentysix26's trigger.py cog
    def is_command(self, msg):
        if callable(self.bot.command_prefix):
            prefixes = self.bot.command_prefix(self.bot, msg)
        else:
            prefixes = self.bot.command_prefix
        for p in prefixes:
            if msg.content.startswith(p):
                return True
        return False

    async def create_smart_reaction(self, server, word, emoji, message, chance):
        word = word.lower()
        try:
            # Use the reaction to see if it's valid
            await self.bot.add_reaction(message, emoji)
            if str(emoji) in self.settings[server.id]:
                chancedict = self.settings[server.id][str(emoji)]
                if word in chancedict:
                    oldchance = chancedict[word]
                    if chance == oldchance:
                        await self.bot.say("This smart reaction already exists.")
                        return
                    else:
                        await self.bot.say("Updating react chance from %f to %f" % (oldchance, chance))
                chancedict[word] = chance
            else:
                self.settings[server.id][str(emoji)] = {word:chance}
            await self.bot.say("Successfully added this reaction.")
            dataIO.save_json(self.settings_path, self.settings)

        except (discord.errors.HTTPException, discord.errors.InvalidArgument):
            await self.bot.say("That's not an emoji I recognize.")

    async def remove_smart_reaction(self, server, word, emoji, message):
        word = word.lower()
        try:
            # Use the reaction to see if it's valid
            await self.bot.add_reaction(message, emoji)
            if str(emoji) in self.settings[server.id]:
                chancedict = self.settings[server.id][str(emoji)]
                if word in chancedict:
                    del chancedict[word]
                    await self.bot.say("Removed this smart reaction.")
                else:
                    await self.bot.say("That emoji is not used as a reaction for that word.")
            else:
                await self.bot.say("There are no smart reactions which use this emoji.")

            dataIO.save_json(self.settings_path, self.settings)

        except (discord.errors.HTTPException, discord.errors.InvalidArgument):
            await self.bot.say("That's not an emoji I recognize.")

    async def msg_listener(self, message):
        if message.author == self.bot.user:
            return
        if self.is_command(message):
            return
        server = message.server
        if server is None:
            return
        if server.id not in self.settings:
            return
        react_dict = copy.deepcopy(self.settings[server.id])
        words = message.content.lower().split()
        for emoji in react_dict:
            triggers = react_dict[emoji]
            for trigger, chance in triggers.items():
                # short-circuit chance, because chance <= 1
                if random.random() < chance and self.is_word_boundary(message.content, trigger):
                    fixed_emoji = self.fix_custom_emoji(emoji)
                    if fixed_emoji is not None:
                        await self.bot.add_reaction(message, fixed_emoji)

    # makes sure that the trigger is surrounded by word boundaries
    # such as $, ^, a non-alphanumeric, etc
    def is_word_boundary(self, string, trigger):
        i = string.find(trigger)
        print(i, string, trigger)
        if i == -1:
            return False
        if 0 < i:
            c = string[i-1]
            if c not in self.NONWORDS:
                return False
        # find character after trigger
        i += len(trigger)
        if i < len(string) - 1:
            c = string[i]
            if c not in self.NONWORDS:
                return False
        return True

def check_folders():
    folder = "data/smortreacts"
    if not os.path.exists(folder):
        print("Creating {} folder...".format(folder))
        os.makedirs(folder)


def check_files():
    default = {}
    if not dataIO.is_valid_json("data/smortreacts/settings.json"):
        print("Creating default smortreacts settings.json...")
        dataIO.save_json("data/smortreacts/settings.json", default)


def setup(bot):
    check_folders()
    check_files()
    n = SmartReact(bot)
    bot.add_cog(n)
    bot.add_listener(n.msg_listener, "on_message")