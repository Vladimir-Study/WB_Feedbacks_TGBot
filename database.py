from sqlite3 import IntegrityError
import asyncio
import aiosqlite
from logger import logger


class DataBase:
    async def modify_db(self):
        async with aiosqlite.connect("WB_feedbacks.sql") as db:
            # async with db.execute(
            #     "SELECT * FROM sqlite_master WHERE type='table';"
            # ) as cursor:
            #     async for row in cursor:
            #         print(row, row[1])
            async with db.execute("SELECT * FROM users;") as cursor:
                async for row in cursor:
                    print(row)
            # await db.execute(f"INSERT INTO users (uid, chat_id) VALUES (?, ?);", [12345555, 4321])
            # res = await db.commit()
            # print(res)
            # await db.execute(f"ALTER TABLE users ADD COLUMN signature VARCHAR(150) DEFAULT '';")
            # await db.commit()

    async def get_all_data(self):
        async with aiosqlite.connect("WB_feedbacks.sql") as db:
            async with db.execute("SELECT * FROM users;") as cursor:
                async for row in cursor:
                    print(row)

    async def get_user_data(self, uid):
        async with aiosqlite.connect("WB_feedbacks.sql") as db:
            try:
                cursor = await db.execute("SELECT * FROM users WHERE uid = ?;", [uid])
                user_data = await cursor.fetchone()
                logger.success("Get user data")
                print(user_data)
                return user_data
            except Exception as E:
                logger.error(f"Get user data: {E}")

    async def add_user_query(self, uid: int, chat_id: int):
        async with aiosqlite.connect("WB_feedbacks.sql") as db:
            try:
                await db.execute(
                    f"INSERT INTO users (uid, chat_id) VALUES (?, ?);", [uid, chat_id]
                )
                await db.commit()
                logger.success("User create in Database")
                return True
            except IntegrityError:
                logger.info("User was added in Database")
                return False

    async def add_user_signature(self, uid: int, signature: str):
        async with aiosqlite.connect("WB_feedbacks.sql") as db:
            try:
                await db.execute(
                    f"UPDATE users SET signature = ? WHERE uid = ?;", [signature, uid]
                )
                await db.commit()
                logger.success("User added signature")
                return True
            except IntegrityError:
                logger.info("Error added signature")
                return False

    async def payed_query_true(self, uid):
        async with aiosqlite.connect("WB_feedbacks.sql") as db:
            try:
                await db.execute(f"UPDATE users SET payed = TRUE WHERE uid = ?;", [uid])
                await db.commit()
                logger.success("Status payed is True")
            except Exception as E:
                logger.error(f"Status payed is True: {E}")

    async def payed_query_false(self, uid):
        async with aiosqlite.connect("WB_feedbacks.sql") as db:
            try:
                await db.execute(
                    f"UPDATE users SET payed = FALSE WHERE uid = ?;", [uid]
                )
                await db.commit()
                logger.success("Status payed is False")
            except Exception as E:
                logger.error(f"Status payed is False: {E}")

    async def get_count_query(self, uid: int):
        async with aiosqlite.connect("WB_feedbacks.sql") as db:
            try:
                cursor = await db.execute(
                    f"SELECT query_count FROM users WHERE uid = ?;", [uid]
                )
                count_query = await cursor.fetchone()
                logger.success("Return count query")
                return count_query[0]
            except Exception as E:
                logger.error(f"Return count query: {E}")

    async def add_count_query(self, uid: int, query_count: int):
        async with aiosqlite.connect("WB_feedbacks.sql") as db:
            try:
                await db.execute(
                    f"UPDATE users SET payed=TRUE, query_count=query_count+? WHERE uid=?;",
                    [query_count, uid],
                )
                await db.commit()
                logger.success(f"Update count query")
            except Exception as E:
                logger.error(f"Update count query: {E}")

    async def delete_query(self, uid: int):
        async with aiosqlite.connect("WB_feedbacks.sql") as db:
            try:
                await db.execute(
                    f"UPDATE users SET payed=TRUE, query_count=0 WHERE uid=?;", [uid]
                )
                await db.commit()
                logger.success(f"Count query set 0")
            except Exception as E:
                logger.error(f"Count query set 0: {E}")

    async def set_token_query(self, uid: int, token: str):
        async with aiosqlite.connect("WB_feedbacks.sql") as db:
            try:
                await db.execute(
                    f"UPDATE users SET wb_token=? WHERE uid=?;", [token, uid]
                )
                await db.commit()
                logger.success(f"Set WB token")
            except Exception as E:
                logger.error(f"Set WB token: {E}")

    async def minus_count_query(self, uid: int):
        async with aiosqlite.connect("WB_feedbacks.sql") as db:
            try:
                await db.execute(
                    f"UPDATE users SET payed=TRUE, query_count=query_count-1 WHERE uid=?;",
                    [uid],
                )
                await db.commit()
                logger.success(f"Minus 1 count query")
            except Exception as E:
                logger.error(f"Minus 1 count query: {E}")


if __name__ == "__main__":
    test = DataBase()
    asyncio.run(test.modify_db())
    # asyncio.run(test.get_count_query(6529453359))
    # asyncio.run(test.set_token_query(6529453359, '1sdf00'))
