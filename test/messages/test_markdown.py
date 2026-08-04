import pytest

from database.schemas import PlanetDto
from game.config import game_config
from test.messages.markdown_validator import MarkdownV2Error, validate_markdown_v2


def assert_valid_markdown_v2(rendered: dict) -> None:
    assert rendered['parse_mode'] == 'MarkdownV2', (
        "Ожидался markdown=True для этого ключа, но renderer вернул "
        f"parse_mode={rendered['parse_mode']!r}. Возможно, флаг markdown "
        "в .yml был изменён — актуализируйте набор тестов в этом файле."
    )
    try:
        validate_markdown_v2(rendered['text'])
    except MarkdownV2Error as e:
        pytest.fail(f"Невалидный MarkdownV2: {e}")



@pytest.mark.parametrize('round', (1, 2))
def test_start_round_for_players_is_valid_markdown(renderer_ru, renderer_en, game, round):
    game.round = round
    assert_valid_markdown_v2(renderer_ru.render('start_round_for_players', game=game))
    assert_valid_markdown_v2(renderer_en.render('start_round_for_players', game=game))


@pytest.mark.parametrize('round', (1, 2))
def test_start_round_for_admins_is_valid_markdown(renderer_ru, renderer_en, game, round):
    game.round = round
    assert_valid_markdown_v2(renderer_ru.render('start_round_for_admins', game=game))
    assert_valid_markdown_v2(renderer_en.render('start_round_for_admins', game=game))


def test_common_planet_info_is_valid_markdown(renderer_ru, renderer_en, planet, cities):
    assert_valid_markdown_v2(renderer_ru.render('common_planet_info', planet=planet, cities=cities))
    assert_valid_markdown_v2(renderer_en.render('common_planet_info', planet=planet, cities=cities))


@pytest.mark.parametrize(
    'sanctioned_planets',
    (['Марс', 'Юпитер'], []),
)
def test_sanctions_info_is_valid_markdown(renderer_ru, renderer_en, sanctioned_planets):
    assert_valid_markdown_v2(renderer_ru.render('sanctions_info', sanctioned_planets=sanctioned_planets))
    assert_valid_markdown_v2(renderer_en.render('sanctions_info', sanctioned_planets=sanctioned_planets))


def test_meteorites_info_invented_is_valid_markdown(renderer_ru, renderer_en, planet):
    assert_valid_markdown_v2(renderer_ru.render('meteorites_info', planet=planet))
    assert_valid_markdown_v2(renderer_en.render('meteorites_info', planet=planet))


def test_meteorites_info_not_invented_is_valid_markdown(renderer_ru, renderer_en, planet_not_invented):
    assert_valid_markdown_v2(renderer_ru.render('meteorites_info', planet=planet_not_invented))
    assert_valid_markdown_v2(renderer_en.render('meteorites_info', planet=planet_not_invented))


def test_meteorites_info_singular_agreement_is_valid_markdown(renderer_ru):
    planet_one = PlanetDto(
        id=5,
        game_id=1,
        name='Венера',
        is_invented=True,
        meteorites=1,
    )
    assert_valid_markdown_v2(renderer_ru.render('meteorites_info', planet=planet_one))


def test_eco_info_is_valid_markdown(renderer_ru, renderer_en, game):
    assert_valid_markdown_v2(renderer_ru.render('eco_info', game=game))
    assert_valid_markdown_v2(renderer_en.render('eco_info', game=game))


def test_other_planet_info_is_valid_markdown(renderer_ru, renderer_en, planet, cities):
    assert_valid_markdown_v2(renderer_ru.render('other_planet_info', planet=planet, cities=cities))
    assert_valid_markdown_v2(renderer_en.render('other_planet_info', planet=planet, cities=cities))


def test_round_end_for_admin_is_valid_markdown(renderer_ru, renderer_en, game):
    assert_valid_markdown_v2(renderer_ru.render('round_end_for_admin', game=game))
    assert_valid_markdown_v2(renderer_en.render('round_end_for_admin', game=game))


def test_round_end_for_players_is_valid_markdown(renderer_ru, renderer_en, game):
    assert_valid_markdown_v2(renderer_ru.render('round_end_for_players', game=game))
    assert_valid_markdown_v2(renderer_en.render('round_end_for_players', game=game))


def test_end_of_the_game_is_valid_markdown(renderer_ru, renderer_en):
    assert_valid_markdown_v2(renderer_ru.render('end_of_the_game'))
    assert_valid_markdown_v2(renderer_en.render('end_of_the_game'))


def test_request_notification_for_leader_is_valid_markdown(renderer_ru, renderer_en, user_ru, user_en):
    assert_valid_markdown_v2(renderer_ru.render('request_notification_for_leader', user=user_ru))
    assert_valid_markdown_v2(renderer_en.render('request_notification_for_leader', user=user_en))


def test_help_is_valid_markdown(renderer_ru, renderer_en):
    assert_valid_markdown_v2(renderer_ru.render('help', game_config=game_config))
    assert_valid_markdown_v2(renderer_en.render('help', game_config=game_config))
