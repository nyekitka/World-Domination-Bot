from aiogram import types
from aiogram.filters import Filter


class InlineButtonFilter(Filter):
    def __init__(self, id: str):
        self.id = id
    
    def __call__(self, call: types.CallbackQuery) -> bool:
        return call.data.startswith(self.id)


class ReplyButtonFilter(Filter):
    def __init__(self, text: str):
        self.text = text
    
    def __call__(self, message: types.Message) -> bool:
        return self.text == message.text
