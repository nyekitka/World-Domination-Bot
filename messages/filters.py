from datetime import timedelta

from inflect import engine
from num2words import num2words
from pymorphy3 import MorphAnalyzer

morph = MorphAnalyzer()
inflect_engine = engine()


def time_filter(value: timedelta, locale: str = 'en') -> str:
    secs = int(value.total_seconds())
    mins = (secs // 60) % 60
    hours = secs // 3600
    secs %= 60

    if locale == 'ru':
        hours_word = morph.parse('час')[0].make_agree_with_number(hours).word
        mins_word = morph.parse('минута')[0].make_agree_with_number(mins).word
        secs_word = morph.parse('секунда')[0].make_agree_with_number(secs).word
    else:
        hours_word = 'hour' if hours == 1 else 'hours'
        mins_word = 'minute' if mins == 1 else 'minutes'
        secs_word = 'second' if secs == 1 else 'seconds'

    parts = []
    if hours > 0:
        parts.append(f'{hours} {hours_word}')
    if mins > 0:
        parts.append(f'{mins} {mins_word}')
    if secs > 0 or not parts:
        parts.append(f'{secs} {secs_word}')
    return ' '.join(parts)


def escape_md(text: str) -> str:
    escape_chars = r'\_*[]()~`>#+-=|{}.!'
    for char in escape_chars:
        text = text.replace(char, f'\\{char}')
    return text


def ordinal(n: int, locale: str = 'en') -> str:
    return num2words(n, to='ordinal', lang=locale)


def make_agree_with(word: str, number: int, locale: str = 'en') -> str:
    if locale == 'ru':
        parsed_word = morph.parse(word)[0]
        agreed_word = parsed_word.make_agree_with_number(number)
        return agreed_word.word
    else:
        return inflect_engine.plural_noun(word, number)


def tag_person(id: int, name: str) -> str:
    return f'[{name}](tg://user?id={id})'


ALL_FILTERS = (
    time_filter,
    escape_md,
    ordinal,
    make_agree_with,
    tag_person,
)
