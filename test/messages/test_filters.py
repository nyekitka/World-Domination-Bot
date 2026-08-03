"""
Тесты для messages.filters: time_filter, escape_md, ordinal, make_agree_with.

Некоторые ожидаемые значения основаны на предположениях о поведении
на неочевидных случаях (0 секунд, границы 11-14, английская локаль
для make_agree_with и т.д.) — они помечены комментарием `# NOTE`.
Поправьте эти значения под фактическую реализацию, если она отличается.
"""

from datetime import timedelta

import pytest

from messages.filters import time_filter, escape_md, ordinal, make_agree_with


@pytest.mark.parametrize(
    "seconds, expected",
    [
        (0, "0 секунд"),
        (431, "7 минут 11 секунд"),
        (120, "2 минуты"),
        (3601, "1 час 1 секунда"),
        (45, "45 секунд"),
        (1, "1 секунда"),
        (2, "2 секунды"),
        (5, "5 секунд"),
        (11, "11 секунд"),
        (180, "3 минуты"),
        (300, "5 минут"),
        (3600, "1 час"),
        (7200, "2 часа"),
        (18000, "5 часов"),
        (75600, "21 час"),
        (79200, "22 часа"),
        (90000, "25 часов"),
    ],
)
def test_time_filter_ru(seconds, expected):
    assert time_filter(timedelta(seconds=seconds), "ru") == expected


@pytest.mark.parametrize(
    "seconds, expected",
    [
        (431, "7 minutes 11 seconds"),
        (120, "2 minutes"),
        (3601, "1 hour 1 second"),
        (45, "45 seconds"),
        (1, "1 second"),
        (2, "2 seconds"),
        (3600, "1 hour"),
        (7200, "2 hours"),
    ],
)
def test_time_filter_en(seconds, expected):
    assert time_filter(timedelta(seconds=seconds), "en") == expected


RESERVED_MD_CHARS = "_*[]()~`>#+-=|{}.!"


@pytest.mark.parametrize("char", list(RESERVED_MD_CHARS))
def test_escape_md_single_reserved_char(char):
    assert escape_md(char) == "\\" + char


def test_escape_md_plain_text_unchanged():
    text = "Привет мир 123 hello world"
    assert escape_md(text) == text


def test_escape_md_mixed_text():
    text = "Hello_world* [test](link) 100% done! (maybe) 2+2=4 | {ok}"
    expected = (
        "Hello\\_world\\* \\[test\\]\\(link\\) 100% done\\! "
        "\\(maybe\\) 2\\+2\\=4 \\| \\{ok\\}"
    )
    assert escape_md(text) == expected


def test_escape_md_dot_and_hyphen():
    assert escape_md("3.14") == "3\\.14"
    assert escape_md("2023-01-01") == "2023\\-01\\-01"


def test_escape_md_empty_string():
    assert escape_md("") == ""


def test_escape_md_no_double_escaping_of_backslash_input():
    # NOTE: предполагается, что уже присутствующий в тексте backslash
    # тоже экранируется, чтобы не сломать итоговую разметку.
    assert escape_md("a\\b") == "a\\\\b"


@pytest.mark.parametrize(
    "n, expected",
    [
        (1, "первый"),
        (2, "второй"),
        (3, "третий"),
        (4, "четвёртый"),
        (5, "пятый"),
        (6, "шестой"),
        (7, "седьмой"),
        (8, "восьмой"),
        (9, "девятый"),
        (10, "десятый"),
        (11, "одиннадцатый"),
        (12, "двенадцатый"),
        (13, "тринадцатый"),
        (20, "двадцатый"),
        (21, "двадцать первый"),
        (22, "двадцать второй"),
        (30, "тридцатый"),
    ],
)
def test_ordinal_ru(n, expected):
    assert ordinal(n, "ru") == expected


@pytest.mark.parametrize(
    "n, expected",
    [
        (1, "first"),
        (2, "second"),
        (3, "third"),
        (4, "fourth"),
        (5, "fifth"),
        (10, "tenth"),
        (11, "eleventh"),
        (12, "twelfth"),
        (13, "thirteenth"),
        (20, "twentieth"),
        (21, "twenty-first"),
        (22, "twenty-second"),
        (23, "twenty-third"),
    ],
)
def test_ordinal_en(n, expected):
    assert ordinal(n, "en") == expected


@pytest.mark.parametrize(
    "word, number, expected",
    [
        ("волк", 1, "волк"),
        ("волк", 2, "волка"),
        ("волк", 3, "волка"),
        ("волк", 4, "волка"),
        ("волк", 5, "волков"),
        ("волк", 10, "волков"),
        ("волк", 11, "волков"),
        ("волк", 12, "волков"),
        ("волк", 21, "волк"),
        ("волк", 22, "волка"),
        ("волк", 25, "волков"),
    ],
)
def test_make_agree_with_ru(word, number, expected):
    assert make_agree_with(word, number, "ru") == expected


def test_make_agree_with_ru_zero():
    # NOTE: 0 обычно согласуется как множественное число ("волков")
    assert make_agree_with("волк", 0, "ru") == "волков"


@pytest.mark.parametrize(
    "word, number, expected",
    [
        ("cat", 1, "cat"),
        ("cat", 2, "cats"),
        ("cat", 5, "cats"),
        ("cat", 0, "cats"),
        ("mouse", 1, "mouse"),
        ("mouse", 2, "mice"),
    ],
)
def test_make_agree_with_en(word, number, expected):
    assert make_agree_with(word, number, "en") == expected