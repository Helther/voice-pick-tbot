import sqlite3
from os import path, rmdir, listdir
from typing import List
from bot_utils import DATA_PATH, VOICES_PATH


DB_NAME = "bot.db"
DB_PATH = path.join(DATA_PATH, DB_NAME)
USERS_TABLE = "users"
VOICES_TABLE = "voices"
CREATE_USERS_TABLE = f"""CREATE TABLE "{USERS_TABLE}" (
"uid"	INTEGER NOT NULL,
"emotion_type"	INTEGER DEFAULT 0,
"sample_num"	INTEGER DEFAULT 1,
"voice_fid" INTEGER DEFAULT NULL,
"default_voice" Text DEFAULT "random",
PRIMARY KEY("uid"),
FOREIGN KEY("voice_fid") REFERENCES voices(id)
)"""
CREATE_VOICES_TABLE = f"""CREATE TABLE "{VOICES_TABLE}" (
"id"	INTEGER NOT NULL,
"user_fid" INTEGER NOT NULL,
"name"	TEXT,
"path"	TEXT,
PRIMARY KEY("id"),
FOREIGN KEY("user_fid") REFERENCES users(uid)
    ON DELETE CASCADE
)"""


"""
Class that interfaces with sqlite3 database, through which all operations are performed
Exception catching and handling is reserved for the user (every query can potentially throw)
"""


class DBHandle(object):
    def __init__(self) -> None:
        load_existing_db = path.exists(DB_PATH)
        self.conn = sqlite3.connect(DB_PATH)
        self.cursor = self.conn.cursor()

        if load_existing_db:
            self.load_db()
        else:
            self.create_db()
        self.validate_db()

    def __del__(self) -> None:
        self.conn.close()

    def load_db(self) -> None:
        # check if all tables are in place
        with self.conn:
            res = self.conn.execute("SELECT name FROM sqlite_master")
            tables = res.fetchall()  # [(name,)]
            if USERS_TABLE not in tables[0][0]:
                self.conn.execute(CREATE_USERS_TABLE)
            if VOICES_TABLE not in tables[1][0]:
                self.conn.execute(CREATE_VOICES_TABLE)

    def create_db(self) -> None:
        with self.conn:
            self.conn.execute(CREATE_USERS_TABLE)
            self.conn.execute(CREATE_VOICES_TABLE)
        self.load_db()

    def validate_db(self) -> None:
        # get db tables up-to-date with bot-data (delete voices entries with missing data)
        # check user folders for integrity
        with self.conn:
            res = self.conn.execute(f"SELECT uid FROM {USERS_TABLE}")
            users_db = set([str(uid[0]) for uid in res.fetchall()])
            users_dirs = [i for i in listdir(VOICES_PATH) if path.isdir(path.join(VOICES_PATH, i))]
            for dir in users_dirs:
                if dir not in users_db:
                    try:
                        uid = int(dir)
                    except BaseException:
                        pass
                    else:
                        self.conn.execute(f"INSERT INTO {USERS_TABLE} (uid) VALUES ({uid})")

            # check voices for integrity for all users
            for user_voices_dir in users_dirs:
                try:
                    uid = int(user_voices_dir)
                    user_voices_path = path.join(VOICES_PATH, user_voices_dir)
                except BaseException:
                    rmdir(user_voices_path)  # remove not uid named folders
                else:
                    res = self.conn.execute(f"SELECT name FROM {VOICES_TABLE} WHERE user_fid={uid}")
                    user_voices_db = set([uid[0] for uid in res.fetchall()])
                    voice_dirs = set([i for i in listdir(user_voices_path) if path.isdir(path.join(user_voices_path, i))])
                    for v in user_voices_db - voice_dirs:
                        self.conn.execute(f"DELETE FROM {VOICES_TABLE} WHERE name={v} AND user_fid={uid}")
                    for v in voice_dirs - user_voices_db:
                        self.conn.execute(f"""INSERT INTO {VOICES_TABLE} (user_fid,name,path)
                                            VALUES ({uid},'{v}','{path.join(user_voices_path, v)}')""")

    def init_user(self, user_id: int) -> None:
        # check if user exists and create if not
        with self.conn:
            res = self.conn.execute(f"SELECT * FROM {USERS_TABLE} WHERE uid={user_id}")
            if res.fetchone() is None:
                self.conn.execute(f"INSERT INTO {USERS_TABLE} (uid) VALUES ({user_id})")

    def update_emot_setting(self, user_id: int, emot: int) -> None:
        # update emotion_type for user in users
        with self.conn:
            self.conn.execute(f"UPDATE {USERS_TABLE} SET emotion_type={emot} WHERE uid={user_id}")

    def update_user_voice_setting(self, user_id: int, voice_id: int) -> None:
        # update voice_fid for user in users
        with self.conn:
            self.conn.execute(f"UPDATE {USERS_TABLE} SET voice_fid={voice_id} WHERE uid={user_id}")

    def update_default_voice_setting(self, user_id: int, voice_name: str) -> None:
        # update voice_fid for user in users
        with self.conn:
            self.conn.execute(f"UPDATE {USERS_TABLE} SET default_voice='{voice_name}',voice_fid=NULL WHERE uid={user_id}")

    def get_user_voices(self, user_id: int) -> List[tuple]:
        # return list of (id, name) tuples for user
        res = self.cursor.execute(f"SELECT id,name FROM {VOICES_TABLE} WHERE user_fid={user_id}")
        return res.fetchall()

    def get_user_voice_setting(self, user_id: int) -> str:
        res = self.cursor.execute(f"""SELECT {USERS_TABLE}.default_voice, {USERS_TABLE}.voice_fid,{VOICES_TABLE}.name
            FROM {USERS_TABLE}
            LEFT JOIN {VOICES_TABLE} ON {USERS_TABLE}.voice_fid={VOICES_TABLE}.id
            WHERE {USERS_TABLE}.uid={user_id}""")
        temp = res.fetchone()
        default_voice, voice_fid, name = temp
        if voice_fid is None:
            return default_voice
        else:
            return name

    def get_user_emotion(self, user_id: int) -> int:
        res = self.cursor.execute(f"SELECT emotion_type FROM {USERS_TABLE} WHERE uid={user_id}")
        type = res.fetchone()[0]
        return type


db_handle = DBHandle()
