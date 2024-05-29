from aiohttp import ClientSession
from envparse import Env
from pprint import pprint
from logger import logger
import asyncio


env = Env()
env.read_envfile()


class YandexAI:
    IAM_TOKEN_URL = "https://iam.api.cloud.yandex.net/iam/v1/tokens"
    FEEDBACK_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

    def __init__(self, token: str):
        self.token = token
        self.IAM_token = None

    @staticmethod
    async def create_request(
        url: str, method: str, headers: dict = None, body: dict = None, params: dict = None
    ) -> dict:
        try:
            async with ClientSession() as session:
                if method == "post":
                    async with session.post(
                        url=url, json=body, headers=headers, params=params
                    ) as response:
                        logger.info(response.status)
                        return await response.json()
                if method == "get":
                    async with session.get(
                            url=url, json=body, headers=headers, params=params
                    ) as response:
                        logger.info(f" Request status: {response.status}")
                        return await response.json()
        except Exception as E:
            logger.error({
                "Error request": E
            })
            return {
                "Error request": E
            }

    async def get_IAM_token(self):
        body = {"yandexPassportOauthToken": self.token}
        return await YandexAI.create_request(self.IAM_TOKEN_URL, "post", body=body)

    async def create_feetbacks(self, feedback_text: str, company: str):
        aim_token = await self.get_IAM_token()
        catalog_uid = env("CATALOG_UID")
        headers = {"Authorization": f"Bearer {aim_token.get('iamToken')}"}
        body = {
            "modelUri": f"gpt://{catalog_uid}/yandexgpt",
            "completionOptions": {
                "stream": False,
                "temperature": 0.3,
                "maxTokens": "1000",
            },
            "messages": [
                {
                    "role": "system",
                    "text": f"Ты — комьюнити-менеджер и работаешь с обратной связью "
                            f"клиентов на продукты компании {company}. Напиши вежливый ответ "
                            f"на отзыв покупателя в Интернете. Длинной до 500 символов. С подписью: "
                            f"С Уважением компания {company}",
                },
                {
                    "role": "user",
                    "text": feedback_text,
                },
            ],
        }
        try:
            response = await YandexAI.create_request(self.FEEDBACK_URL, "post", headers, body)
            logger.success("Generate AI feedback")
            return response
        except Exception as E:
            logger.error(f"Generate AI feedback: {E}")