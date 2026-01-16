# handlers/database.py

import datetime
import motor.motor_asyncio
from configs import Config

class Database:

    def __init__(self, uri, database_name):
        self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self.db = self._client[database_name]
        self.col = self.db.users
        self.config_col = self.db.config

    # -------- নতুন ফাংশন শুরু (ক্যাপশন ও সেটিংস) --------
    
    async def get_protect_content(self):
        config = await self.config_col.find_one({'id': 'bot_settings'})
        return config.get('protect_content', False) if config else False

    async def set_protect_content(self, value: bool):
        await self.config_col.update_one(
            {'id': 'bot_settings'}, 
            {'$set': {'protect_content': value}}, 
            upsert=True
        )

    async def get_auto_delete_time(self):
        config = await self.config_col.find_one({'id': 'bot_settings'})
        return config.get('auto_delete_time', 0) if config else 0

    async def set_auto_delete_time(self, time_in_seconds: int):
        await self.config_col.update_one(
            {'id': 'bot_settings'},
            {'$set': {'auto_delete_time': time_in_seconds}},
            upsert=True
        )

    # কাস্টম ক্যাপশন সেট করা
    async def set_caption(self, caption):
        await self.config_col.update_one(
            {'id': 'bot_settings'},
            {'$set': {'caption': caption}},
            upsert=True
        )

    # কাস্টম ক্যাপশন আনা
    async def get_caption(self):
        config = await self.config_col.find_one({'id': 'bot_settings'})
        return config.get('caption', None) if config else None

    # -------- নতুন ফাংশন শেষ --------

    def new_user(self, id):
        return dict(
            id=id,
            join_date=datetime.date.today().isoformat(),
            ban_status=dict(
                is_banned=False,
                ban_duration=0,
                banned_on=datetime.date.max.isoformat(),
                ban_reason=''
            )
        )

    async def add_user(self, id):
        user = self.new_user(id)
        await self.col.insert_one(user)

    async def is_user_exist(self, id):
        user = await self.col.find_one({'id': int(id)})
        return True if user else False

    async def total_users_count(self):
        count = await self.col.count_documents({})
        return count

    async def get_all_users(self):
        all_users = self.col.find({})
        return all_users

    async def delete_user(self, user_id):
        await self.col.delete_many({'id': int(user_id)})

    async def remove_ban(self, id):
        ban_status = dict(
            is_banned=False,
            ban_duration=0,
            banned_on=datetime.date.max.isoformat(),
            ban_reason=''
        )
        await self.col.update_one({'id': id}, {'$set': {'ban_status': ban_status}})

    async def ban_user(self, user_id, ban_duration, ban_reason):
        ban_status = dict(
            is_banned=True,
            ban_duration=ban_duration,
            banned_on=datetime.date.today().isoformat(),
            ban_reason=ban_reason
        )
        await self.col.update_one({'id': user_id}, {'$set': {'ban_status': ban_status}})

    async def get_ban_status(self, id):
        default = dict(
            is_banned=False,
            ban_duration=0,
            banned_on=datetime.date.max.isoformat(),
            ban_reason=''
        )
        user = await self.col.find_one({'id': int(id)})
        return user.get('ban_status', default)

    async def get_all_banned_users(self):
        banned_users = self.col.find({'ban_status.is_banned': True})
        return banned_users

db = Database(Config.DATABASE_URL, Config.BOT_USERNAME)
