import re


class Answer:

    def __init__(self, company: str, product_name: str,
                 product_valuation: str, created_date: str,
                 text_feedback: str, ai_answer, message_id: int,
                 feedback_id: str, user_name: str):
        self.company = company
        self.product_name = product_name
        self.product_valuation = product_valuation
        self.created_date = created_date
        self.text_feedback = text_feedback
        self.ai_answer = ai_answer
        self.message_id = message_id
        self.feedback_id = feedback_id
        self.user_name = user_name


    async def create_message_not_signature(self):
        self.ai_answer = re.sub(r'\bС уважением.+(\n)?.+', '', self.ai_answer).replace('\n', '')
        answer_message = f"Я нашла новый отзыв в магазине {self.company}(Wildberries) и " \
                         f"сгенерировала на него ответ\n\n" \
                         f"*Товар:* {self.product_name}\n" \
                         f"*Оценка* {self.product_valuation}\n" \
                         f"*Дата*: {self.created_date[:10]}\n" \
                         f"*Текст отзыва:* {self.text_feedback}\n\n" \
                         f"*Ответ:*\n{self.ai_answer}"
        return answer_message


    async def create_message_with_signature(self):
        answer_message = f"Я нашла новый отзыв в магазине {self.company}(Wildberries) и " \
                         f"сгенерировала на него ответ\n\n" \
                         f"*Товар:* {self.product_name}\n" \
                         f"*Оценка* {self.product_valuation}\n" \
                         f"*Дата*: {self.created_date[:10]}\n" \
                         f"*Текст отзыва:* {self.text_feedback}\n\n" \
                         f"*Ответ:*\n{self.ai_answer}"
        return answer_message
