from typing import Union

from discord.ext import menus

#from src.common.reacts import Reacts


class _BaseMenu(menus.Menu):

	async def send_initial_message(self, ctx, channel):
		raise NotImplementedError()

	def reaction_check(self, payload):
		""" Ignore reaction removals as events if the menu is in a guild. """

		if self.message.guild and payload.event_type == "REACTION_REMOVE":
			return False

		return super().reaction_check(payload)


class PageDisplay(_BaseMenu):
	def __init__(self, *, pages = None, timeout: int = 180):
		super().__init__(timeout=timeout, clear_reactions_after=True)

		self.current = 0

		self.pages = pages
		print(self.pages)

	async def send_initial_message(self, ctx, destination):
		return await destination.send(embed=self.pages[self.current])

	async def get_embed(self, index):
		return self.pages.get(index)

	async def remove_reaction(self, message, emoji, member):
		perms = message.channel.permissions_for(message.channel.guild.me)

		if message.guild and perms.manage_messages:
			await message.remove_reaction(emoji, member)

	async def on_reaction(self, payload, index):
		await self.remove_reaction(self.message, payload.emoji, payload.member)
		self.current = index
		print(self.current)
		await self.message.edit(embed=self.pages[self.current])


	@staticmethod
	def _update_pages(pages):
		if isinstance(pages, list):
			return {i: ele for i, ele in enumerate(pages)}

		return pages

	@menus.button('⬅')
	async def go_prev(self, payload):
		print(len(self.pages), (self.current - 1))
		await self.on_reaction(payload, (self.current - 1)%len(self.pages))

	@menus.button('➡')
	async def go_next(self, payload):
		await self.on_reaction(payload, (self.current + 1)%len(self.pages))


class DynamicPageDisplay(PageDisplay):
	def __init__(self, generator, formatter):
		super().__init__()

		self.generator = generator
		self.formatter = formatter

	async def start(self, ctx, *, channel=None, wait=False):
		self.pages[0] = await self.get_embed(index=self.current)

		await super().start(ctx, channel=channel, wait=wait)

	async def get_embed(self, index):
		t = await self.generator(index)
		if results == t:
			return await self.formatter(index, results)