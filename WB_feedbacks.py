import asyncio
from pprint import pprint

from envparse import Env
from yandex_AI import YandexAI
from logger import logger


env = Env()
env.read_envfile()


class WBParser:
    GET_FEEDBACK_URL = "https://feedbacks-api.wb.ru/api/v1/feedbacks"

    def __init__(self, token):
        self.token = token

    async def get_feedback(self, is_answered: str = 'false', take: int = 30, skip: int = 0):
        params = {
            "isAnswered": is_answered,
            "take": take,
            "skip": skip
        }
        headers = {
            "Authorization": self.token
        }
        try:
            response = await YandexAI.create_request(self.GET_FEEDBACK_URL, 'get', headers=headers, params=params)
            logger.success("Get feedbacks")
            return response
        except Exception as E:
            logger.error(f"Get feedbacks {E}")

    async def feedback_answer(self, feedback_id: str, feedback_text: str):
        headers = {
            "Authorization": self.token
        }
        body = {
            "id": feedback_id,
            "text": feedback_text
        }
        try:
            response = await YandexAI.create_request(self.GET_FEEDBACK_URL, 'patch', headers=headers, body=body)
            logger.success("Answer feedback")
            return response
        except Exception as E:
            logger.error(f"Answer feedback {E}")

    async def check_feedback(self, feedback_id: str):
        headers = {
            "Authorization": self.token
        }
        body = {
            "id": feedback_id,
            "wasViewed": True
        }
        try:
            response = await YandexAI.create_request(self.GET_FEEDBACK_URL, 'patch', headers=headers, body=body)
            logger.success("Update check feedback")
            return response
        except Exception as E:
            logger.error(f"Update check feedback {E}")


async def main():
    token = env("WB_TOKEN")
    parser = WBParser(token)
    print(await parser.get_feedback())

if __name__ == "__main__":
    asyncio.run(main())
