"""An example of connecting to a conduit and subscribing to EventSub when a User Authorizes the application.

This bot can be restarted as many times without needing to subscribe or worry about tokens:
- Tokens are stored in '.tio.tokens.json' by default
- Subscriptions last 72 hours after the bot is disconnected and refresh when the bot starts.

Consider reading through the documentation for AutoBot for more in depth explanations.
"""

import asyncio
import logging
import random
from typing import TYPE_CHECKING

import asqlite

import twitchio
from twitchio import eventsub
from twitchio.ext import commands
from twitchio.web import StarletteAdapter
from twitchio.web import AiohttpAdapter

import twitchio.web as web

import redis
import json
import os


if TYPE_CHECKING:
    import sqlite3


r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)


LOGGER: logging.Logger = logging.getLogger("Bot")

CREDS_FILE = 'credentials.json'

def load_credentials():
    """Loads credentials from the JSON file or creates a default template if missing."""
    defaults = {
        "client_id": "",
        "client_secret": "",
        "owner_id": "",
        "bot_id": "",
        "token": ""
    }
    if not os.path.exists(CREDS_FILE):
        with open(CREDS_FILE, 'w') as f:
            json.dump(defaults, f, indent=4)
        print("✅ Created default credentials.json file.")
        return defaults
    
    with open(CREDS_FILE, 'r') as f:
        try:
            data = json.load(f)
            return {**defaults, **data}
        except json.JSONDecodeError:
            return defaults

creds = load_credentials()
CLIENT_ID: str = creds.get('client_id', '')
CLIENT_SECRET: str = creds.get('client_secret', '')
OWNER_ID = creds.get('owner_id', '')
BOT_ID = creds.get('bot_id', '')

SCOPES = [
    "chat:read",
    "chat:write",
    "chat:edit",
    "user:read:chat",
    "moderator:read:followers"
]


class Bot(commands.AutoBot):
    def __init__(self, *, token_database: asqlite.Pool, subs: list[eventsub.SubscriptionPayload]) -> None:
        self.token_database = token_database

        super().__init__(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            owner_id=OWNER_ID,
            bot_id=BOT_ID,
            prefix="!",
            subscriptions=subs,
            force_subscribe=True,
            adapter = web.AiohttpAdapter(host="0.0.0.0", port=4343),
            scopes=SCOPES,
        )

    #THIS ONE MIGHT NOT BE NEEDED, ADDE WHEN TROUBLESHOOTING
    async def event_token_refreshed(self, payload: twitchio.TokenRefreshedPayload) -> None:
        # This event fires whenever TwitchIO automatically refreshes a token
        query = """
        UPDATE tokens 
        SET token = ?, refresh = ? 
        WHERE user_id = ?
        """
        async with self.token_database.acquire() as connection:
            await connection.execute(query, (payload.access_token, payload.refresh_token, payload.user_id))
        
        LOGGER.info("Successfully updated database with REFRESHED tokens for: %s", payload.user_id)







    async def event_command_error(self, payload: commands.CommandErrorPayload) -> None:
        pass


    async def setup_hook(self) -> None:
        # Add our component which contains our commands...
        await self.add_component(MyComponent(self))

    async def event_oauth_authorized(self, payload: twitchio.authentication.UserTokenPayload) -> None:
        await self.add_token(payload.access_token, payload.refresh_token)

        if not payload.user_id:
            return

        if payload.user_id == self.bot_id:
            # We usually don't want subscribe to events on the bots channel...
            return

        # A list of subscriptions we would like to make to the newly authorized channel...
        subs: list[eventsub.SubscriptionPayload] = [
            eventsub.ChatMessageSubscription(broadcaster_user_id=payload.user_id, user_id=self.bot_id),
        ]

        resp: twitchio.MultiSubscribePayload = await self.multi_subscribe(subs)
        if resp.errors:
            LOGGER.warning("Failed to subscribe to: %r, for user: %s", resp.errors, payload.user_id)

    async def add_token(self, token: str, refresh: str) -> twitchio.authentication.ValidateTokenPayload:
        # Make sure to call super() as it will add the tokens interally and return us some data...
        resp: twitchio.authentication.ValidateTokenPayload = await super().add_token(token, refresh)

        # Store our tokens in a simple SQLite Database when they are authorized...
        query = """
        INSERT INTO tokens (user_id, token, refresh)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id)
        DO UPDATE SET
            token = excluded.token,
            refresh = excluded.refresh;
        """

        async with self.token_database.acquire() as connection:
            await connection.execute(query, (resp.user_id, token, refresh))

        LOGGER.info("Added token to the database for user: %s", resp.user_id)
        return resp

    async def event_ready(self) -> None:
        LOGGER.info("Successfully logged in as: %s", self.bot_id)


class MyComponent(commands.Component):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot



    @commands.Component.listener()
    async def safari_bot_chat(self, r_client, twitch_channel): #added self, remove it it breaks things
        while True:
            # 'blpop' waits until there is something in the list (blocking pop)
            # result will be (key, value)
            result = await r_client.blpop("twitch:chat_queue", timeout=1)
            
            if result:
                msg_text = result[1].decode('utf-8')
                await ctx.send(f"{msg_tex}t")

            await asyncio.sleep(0.1)




    @commands.Component.listener()
    @commands.cooldown(rate=1, per=10, key=commands.BucketType.channel)
    async def event_message(self, payload: twitchio.ChatMessage) -> None:
        print(f"[{payload.broadcaster.name}] - {payload.chatter.name}: {payload.text}")

        # Bot ID filter
        bot_id = getattr(self.bot, 'user_id', None) or getattr(self.bot.user, 'id', None)
        if payload.chatter.id == bot_id:
            return

        text = payload.text.lower().strip()
        
        if text.startswith('!slew_'):
            raw_data = r.get("nina:available_targets")
            if raw_data:
                targets = json.loads(raw_data)
                target = next((t for t in targets if t['trigger'].lower() == text), None)

                if target:
                    r.set("nina:current_target", json.dumps(target))
                    slew_payload = {
                        "action": "slew", 
                        "name": target['name'], 
                        "ra": target.get('ra', 0), 
                        "ra_min": target.get('ra_min', 0),
                        "dec": target.get('dec', 0),
                        "dec_min": target.get('dec_min', 0)
                    }
                    r.publish("nina:commands", json.dumps(slew_payload))
                    #TTS TEST, i have inconsistent ways of getting chatte name, like below and also ctx.chatter
                    #r.publish("nina:speech", f"{payload.chatter.name} is Slewing to {target['name']}")

                    return 





    @commands.command()
    @commands.cooldown(rate=1, per=10, key=commands.BucketType.channel)
    async def capture(self, ctx: commands.Context) -> None:
            raw_target = r.get("nina:current_target")
            if raw_target:
                target = json.loads(raw_target)
                exposure_time = 60
                image_payload ={
                   "action": "sequence",
                   "name": target['name'],
                   "exposure": exposure_time
                }
                r.publish("nina:commands", json.dumps(image_payload))
                #r.publish("nina:speech", f"{ctx.chatter} is starting an sequence of {exposure_time} second exposures of {target['name']}")
                await ctx.reply(f"{ctx.chatter} is starting an sequence of {exposure_time} second exposures of {target['name']}!")
            else:
                await ctx.send("x No current target found in memory. Slew to a target first")







    @commands.command()
    @commands.cooldown(rate=1, per=10, key=commands.BucketType.channel)
    async def hi(self, ctx: commands.Context) -> None:
        await ctx.reply(f"Hi {ctx.chatter}!")

    @commands.command()
    @commands.cooldown(rate=1, per=10, key=commands.BucketType.channel)
    async def list(self, ctx: commands.Context) -> None:
        r.publish("twitch:updates", json.dumps("!list"))
        await asyncio.sleep(1)
        raw_data = r.get("nina:available_targets")
        if raw_data:
            targets = json.loads(raw_data)
            if targets:
                target_names = ", ".join([t['trigger'] for t in targets])
                await ctx.send(f"| Commands: !list !capture || 🔭 Available targets: {target_names}")
                r.publish("nina:speech", f"{ctx.chatter} , Available targets are listed in chat, an example trigger could be: !slew_andromeda")



    @commands.group(invoke_fallback=True)
    @commands.cooldown(rate=1, per=10, key=commands.BucketType.channel)
    async def socials(self, ctx: commands.Context) -> None:
        await ctx.send("discord.gg/XZ2Ft8N3Vu, youtube.com/@castronomy, twitch.tv/castronomy")

    @commands.command(invoke_fallback=True)
    @commands.cooldown(rate=1, per=10, key=commands.BucketType.channel)
    async def discord(self, ctx: commands.Context) -> None:
        await ctx.send("discord.gg/...")

    @commands.command(invoke_fallback=True)
    @commands.cooldown(rate=1, per=10, key=commands.BucketType.channel)
    async def equipment(self, ctx: commands.Context) -> None:
        await ctx.send("Telescope: Skywatcher 80ed | Mount: Sal-33 / Umi17r| Camera: Nikon D5000 / Touptek 678m")
        r.publish("nina:speech", f"Telescope: Skywatcher 80ed | Mount: Sal-33 / Umi17r | Camera: Nikon D5000 / Touptek 678m")

    @commands.command(invoke_fallback=True)
    @commands.cooldown(rate=1, per=10, key=commands.BucketType.channel)
    async def slew_carina(self, ctx: commands.Context) -> None:
        await ctx.send("Aussie Aussie Aussie! Oi Oi Oi!")
        r.publish("nina:speech", f"Aussie Aussie Aussie! Oi Oi Oi!")

    @commands.command(invoke_fallback=True)
    @commands.cooldown(rate=1, per=10, key=commands.BucketType.channel)
    async def slew_sun(self, ctx: commands.Context) -> None:
        await ctx.send("Ikarus Daedalus was watching through a telescope...")
        r.publish("nina:speech", f"Ikarus Daedalus was watching through a telescope...")


async def setup_database(db: asqlite.Pool) -> tuple[list[tuple[str, str]], list[eventsub.SubscriptionPayload]]:
    # Create our token table, if it doesn't exist..

    query = """CREATE TABLE IF NOT EXISTS tokens(user_id TEXT PRIMARY KEY, token TEXT NOT NULL, refresh TEXT NOT NULL)"""
    async with db.acquire() as connection:
        await connection.execute(query)

        # Fetch any existing tokens...
        rows: list[sqlite3.Row] = await connection.fetchall("""SELECT * from tokens""")

        tokens: list[tuple[str, str]] = []
        subs: list[eventsub.SubscriptionPayload] = []

        for row in rows:
            tokens.append((row["token"], row["refresh"]))

            if row["user_id"] == BOT_ID:
                continue

            subs.extend([eventsub.ChatMessageSubscription(broadcaster_user_id=row["user_id"], user_id=BOT_ID)])

    return tokens, subs


# Main entry point for our Bot
def main() -> None:
    twitchio.utils.setup_logging(level=logging.INFO)

    async def runner() -> None:
        async with asqlite.create_pool("tokens.db") as tdb:
            tokens, subs = await setup_database(tdb)

            async with Bot(token_database=tdb, subs=subs) as bot:
                for pair in tokens:
                    await bot.add_token(*pair)

                await bot.start(load_tokens=False)
                #IF having token problems, try use this instead.
                #await bot.start()

    try:
        asyncio.run(runner())
    except KeyboardInterrupt:
        LOGGER.warning("Shutting down due to KeyboardInterrupt")


if __name__ == "__main__":
    main()

