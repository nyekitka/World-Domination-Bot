import asyncio
import logging
import pytest
from pytest_lazy_fixtures import lf

from database.config import game_config
from database.models import City, Game, Negotiation, Order, Planet, Sanction
from database.schemas import FailureReason, GameStatus, OrderDto, OrderType, SanctionDto


logger = logging.getLogger(__name__)


@pytest.mark.parametrize(
    ("balance", "exp_new_balance", "exp_result"),
    [
        (game_config.SHIELD_COST + 1, 1, FailureReason.SUCCESS),
        (1, 1, FailureReason.NOT_ENOUGH_MONEY),
    ],
)
@pytest.mark.asyncio
async def test_order_shield_for_city_without_order(
    mock_actions_client,
    city_id,
    planet_id,
    game_id,
    balance,
    exp_new_balance,
    exp_result,
):
    async with mock_actions_client.session() as s:
        planet = await s.get(Planet, planet_id)
        game = await s.get(Game, game_id)
        game.status = GameStatus.ROUND
        game.round = 1
        planet.balance = balance
        await s.commit()

        result = await mock_actions_client.order_shield_for_city(city_id)
        updated_planet = await s.get(Planet, planet_id)
        new_balance = updated_planet.balance

        assert result == exp_result
        assert new_balance == exp_new_balance

        new_order = await s.get(
            Order,
            {
                "action": OrderType.SHIELD,
                "planet_id": planet_id,
                "round": 1,
                "argument": city_id,
            },
        )
        if exp_result == FailureReason.SUCCESS:
            assert new_order


@pytest.mark.asyncio
async def test_order_shield_for_city_with_order(
    mock_actions_client,
    city_id,
    planet_id,
    game_id,
):
    order = Order(
        action=OrderType.SHIELD, planet_id=planet_id, argument=city_id, round=1
    )
    async with mock_actions_client.session() as s:
        planet = await s.get(Planet, planet_id)
        game = await s.get(Game, game_id)
        game.status = GameStatus.ROUND
        game.round = 1
        old_balance = planet.balance
        s.add(order)
        await s.commit()

        result = await mock_actions_client.order_shield_for_city(city_id)

        assert result == FailureReason.SUCCESS

        updated_planet = await s.get(Planet, planet_id)
        new_balance = updated_planet.balance

        assert new_balance - old_balance == game_config.SHIELD_COST

        order = await s.get(
            Order,
            {
                "action": OrderType.SHIELD,
                "planet_id": planet_id,
                "round": 1,
                "argument": city_id,
            },
        )

        assert order is None


@pytest.mark.asyncio
async def test_build_shield_for_cities(mock_actions_client, city_id, city_id_2):
    await mock_actions_client.build_shield_for_cities(city_id, city_id_2)
    async with mock_actions_client.session() as s:
        city1 = await s.get(City, city_id)
        city2 = await s.get(City, city_id_2)

        assert city1.is_shielded
        assert city2.is_shielded


@pytest.mark.parametrize(
    ("balance", "exp_new_balance", "exp_result"),
    [
        (game_config.DEVELOPMENT_COST + 1, 1, FailureReason.SUCCESS),
        (1, 1, FailureReason.NOT_ENOUGH_MONEY),
    ],
)
@pytest.mark.asyncio
async def test_order_development(
    mock_actions_client,
    city_id,
    planet_id,
    game_id,
    balance,
    exp_new_balance,
    exp_result,
):
    async with mock_actions_client.session() as s:
        planet = await s.get(Planet, planet_id)
        game = await s.get(Game, game_id)
        game.status = GameStatus.ROUND
        game.round = 1
        planet.balance = balance
        await s.commit()

        result = await mock_actions_client.order_development(city_id)
        updated_planet = await s.get(Planet, planet_id)
        new_balance = updated_planet.balance

        assert result == exp_result
        assert new_balance == exp_new_balance

        new_order = await s.get(
            Order,
            {
                "action": OrderType.DEVELOP,
                "planet_id": planet_id,
                "round": 1,
                "argument": city_id,
            },
        )
        if exp_result == FailureReason.SUCCESS:
            assert new_order


@pytest.mark.asyncio
async def test_develop_cities(mock_actions_client, city_id, city_id_2):
    async with mock_actions_client.session() as s:
        city1 = await s.get(City, city_id)
        city2 = await s.get(City, city_id_2)
        development1 = city1.development
        development2 = city2.development

    await mock_actions_client.develop_cities(city_id, city_id_2)
    async with mock_actions_client.session() as s:
        city1 = await s.get(City, city_id)
        city2 = await s.get(City, city_id_2)

        assert city1.development - development1 == game_config.DEVELOPMENT_BOOST
        assert city2.development - development2 == game_config.DEVELOPMENT_BOOST


@pytest.mark.parametrize(
    ["planet_from", "planet_to", "expected"],
    [
        (lf("planet_id"), lf("planet_id_2"), FailureReason.ALREADY_NEGOTIATING),
        (lf("planet_id_2"), lf("planet_id"), FailureReason.BILATERAL_NEGOTIATIONS),
        (lf("planet_id_3"), lf("planet_id_2"), FailureReason.PLANET_IS_BUSY),
        (lf("planet_id_3"), lf("planet_id"), FailureReason.SUCCESS),
    ],
)
@pytest.mark.asyncio
async def test_accept_diplomatist(
    planet_from,
    planet_to,
    expected,
    planet_id,
    planet_id_2,
    game_id,
    mock_actions_client,
):
    async with mock_actions_client.session() as s:
        negotiation = Negotiation(planet_from=planet_from, planet_to=planet_to)
        s.add(negotiation)
        game = await s.get(Game, game_id)
        game.status = GameStatus.ROUND
        await s.commit()

    result = await mock_actions_client.accept_diplomatist(planet_id, planet_id_2)
    assert result == expected

    if result == FailureReason.SUCCESS:
        async with mock_actions_client.session() as s:
            new_negotiation = await s.get(
                Negotiation, {"planet_from": planet_id, "planet_to": planet_id_2}
            )
            assert new_negotiation


@pytest.mark.asyncio
async def test_accept_diplomatist_when_not_round(
    mock_actions_client, planet_id, planet_id_2
):
    result = await mock_actions_client.accept_diplomatist(planet_id, planet_id_2)
    assert result == FailureReason.UNTIMELY_NEGOTIATIONS


@pytest.mark.asyncio
async def test_end_negotiations(mock_actions_client, planet_id, planet_id_2):
    async with mock_actions_client.session() as s:
        negotiation = Negotiation(planet_from=planet_id, planet_to=planet_id_2)
        s.add(negotiation)
        await s.commit()

    await mock_actions_client.end_negotiations(planet_id, planet_id_2)

    async with mock_actions_client.session() as s:
        negotiation = await s.get(
            Negotiation, {"planet_from": planet_id, "planet_to": planet_id_2}
        )
        assert negotiation is None


@pytest.mark.parametrize(
    ("balance", "exp_new_balance", "is_invented", "exp_result"),
    [
        (game_config.INVENTION_COST + 1, 1, False, FailureReason.SUCCESS),
        (
            game_config.INVENTION_COST + 1,
            game_config.INVENTION_COST + 1,
            True,
            FailureReason.ALREADY_INVENTED,
        ),
        (1, 1, False, FailureReason.NOT_ENOUGH_MONEY),
    ],
)
@pytest.mark.asyncio
async def test_order_invent(
    mock_actions_client,
    planet_id,
    game_id,
    balance,
    exp_new_balance,
    is_invented,
    exp_result,
):
    async with mock_actions_client.session() as s:
        planet = await s.get(Planet, planet_id)
        game = await s.get(Game, game_id)
        game.status = GameStatus.ROUND
        game.round = 1
        planet.balance = balance
        planet.is_invented = is_invented
        await s.commit()

        result = await mock_actions_client.order_invent(planet_id)
        updated_planet = await s.get(Planet, planet_id)
        new_balance = updated_planet.balance

        assert result == exp_result
        assert new_balance == exp_new_balance

        if exp_result == FailureReason.SUCCESS:
            new_order = await s.get(
                Order,
                {
                    "action": OrderType.INVENT,
                    "planet_id": planet_id,
                    "round": 1,
                    "argument": 0,
                },
            )

            assert new_order


@pytest.mark.asyncio
async def test_order_invent_when_ordered(mock_actions_client, planet_id, game_id):
    async with mock_actions_client.session() as s:
        planet = await s.get(Planet, planet_id)
        game = await s.get(Game, game_id)
        game.round = 1
        old_balance = planet.balance
        order = Order(action=OrderType.INVENT, planet_id=planet_id, round=1, argument=0)
        s.add(order)
        await s.commit()

    result = await mock_actions_client.order_invent(planet_id)
    result == FailureReason.SUCCESS

    async with mock_actions_client.session() as s:
        planet = await s.get(Planet, planet_id)
        assert planet.balance - old_balance == game_config.INVENTION_COST


@pytest.mark.asyncio
async def test_invent_for_planets(mock_actions_client, planet_id, planet_id_2):
    await mock_actions_client.invent_for_planets(planet_id, planet_id_2)

    async with mock_actions_client.session() as s:
        planet = await s.get(Planet, planet_id)
        planet_2 = await s.get(Planet, planet_id_2)

        assert planet.is_invented
        assert planet_2.is_invented


@pytest.mark.asyncio
async def test_is_invent_in_order(mock_actions_client, planet_id, game_id):
    async with mock_actions_client.session() as s:
        game = await s.get(Game, game_id)
        game.round = 1
        await s.commit()

    res = await mock_actions_client.is_invent_in_order(planet_id)
    assert not res

    async with mock_actions_client.session() as s:
        game = await s.get(Game, game_id)
        order = Order(action=OrderType.INVENT, planet_id=planet_id, round=1, argument=0)
        s.add(order)
        await s.commit()

    res = await mock_actions_client.is_invent_in_order(planet_id)
    assert res


@pytest.mark.parametrize(
    ["num_meteorites", "balance", "exp_new_balance", "result"],
    [
        (1, game_config.CREATE_COST, 0, FailureReason.SUCCESS),
        (3, 3 * game_config.CREATE_COST, 0, FailureReason.SUCCESS),
        (
            3,
            2 * game_config.CREATE_COST,
            2 * game_config.CREATE_COST,
            FailureReason.NOT_ENOUGH_MONEY,
        ),
    ],
)
@pytest.mark.asyncio
async def test_order_create_meteorites_without_existing_order(
    mock_actions_client, planet_id, num_meteorites, balance, exp_new_balance, result
):
    async with mock_actions_client.session() as s:
        planet = await s.get(Planet, planet_id)
        planet.balance = balance
        planet.is_invented = True
        await s.commit()

    res = await mock_actions_client.order_create_meteorites(planet_id, num_meteorites)
    assert res == result

    async with mock_actions_client.session() as s:
        planet = await s.get(Planet, planet_id)
        assert planet.balance == exp_new_balance


@pytest.mark.asyncio
async def test_order_create_meteorites_when_its_not_invented(
    mock_actions_client, planet_id
):
    res = await mock_actions_client.order_create_meteorites(planet_id, 1)
    assert res == FailureReason.IS_NOT_INVENTED


@pytest.mark.parametrize(
    ["ordered_num", "num_to_order", "balance", "exp_new_balance"],
    [
        (1, 2, 2 * game_config.CREATE_COST, game_config.CREATE_COST),
        (2, 1, game_config.CREATE_COST, 2 * game_config.CREATE_COST),
    ],
)
@pytest.mark.asyncio
async def test_order_create_meteorites_with_existing_order(
    mock_actions_client,
    planet_id,
    game_id,
    ordered_num,
    num_to_order,
    balance,
    exp_new_balance,
):
    async with mock_actions_client.session() as s:
        planet = await s.get(Planet, planet_id)
        game = await s.get(Game, game_id)
        game.round = 1
        planet.balance = balance
        planet.is_invented = True
        order = Order(
            action=OrderType.CREATE, planet_id=planet_id, round=1, argument=ordered_num
        )
        s.add(order)
        await s.commit()

    res = await mock_actions_client.order_create_meteorites(planet_id, num_to_order)
    assert res == FailureReason.SUCCESS

    async with mock_actions_client.session() as s:
        planet = await s.get(Planet, planet_id)
        assert planet.balance == exp_new_balance
        order = await s.get(
            Order,
            {
                "action": OrderType.CREATE,
                "planet_id": planet_id,
                "round": 1,
                "argument": num_to_order,
            },
        )
        assert order


@pytest.mark.parametrize(
    ["num_to_create", "meteorites", "result"], [(1, 2, 3), (2, 2, 4)]
)
@pytest.mark.asyncio
async def test_create_meteorites(
    mock_actions_client, planet_id, num_to_create, meteorites, result
):
    async with mock_actions_client.session() as s:
        planet = await s.get(Planet, planet_id)
        planet.meteorites = meteorites
        await s.commit()

    await mock_actions_client.create_meteorites(planet_id, num_to_create)

    async with mock_actions_client.session() as s:
        planet = await s.get(Planet, planet_id)
        assert planet.meteorites == result


@pytest.mark.parametrize(
    ["attacking_planet_id", "num_meteorites", "result"],
    [
        (lf("planet_id"), 1, FailureReason.SELF_ATTACK),
        (lf("planet_id_2"), 0, FailureReason.NOT_ENOUGH_METEORITES),
        (lf("planet_id_2"), 1, FailureReason.SUCCESS),
    ],
)
@pytest.mark.asyncio
async def test_order_attack_city(
    mock_actions_client, game_id, city_id, attacking_planet_id, num_meteorites, result
):
    async with mock_actions_client.session() as s:
        planet = await s.get(Planet, attacking_planet_id)
        game = await s.get(Game, game_id)
        game.round = 1
        planet.meteorites = num_meteorites
        planet.is_invented = True
        await s.commit()

    res = await mock_actions_client.order_attack_city(attacking_planet_id, city_id)
    assert res == result

    if res == FailureReason.SUCCESS:
        async with mock_actions_client.session() as s:
            order = await s.get(
                Order,
                {
                    "action": OrderType.ATTACK,
                    "planet_id": attacking_planet_id,
                    "round": 1,
                    "argument": city_id,
                },
            )
            assert order


@pytest.mark.asyncio
async def test_order_attack_city_when_not_invented(
    mock_actions_client,
    planet_id_2,
    city_id,
):
    res = await mock_actions_client.order_attack_city(planet_id_2, city_id)
    assert res == FailureReason.IS_NOT_INVENTED


@pytest.mark.asyncio
async def test_order_attack_with_existing_order(
    mock_actions_client, planet_id_2, city_id, game_id
):
    async with mock_actions_client.session() as s:
        planet = await s.get(Planet, planet_id_2)
        game = await s.get(Game, game_id)
        game.round = 1
        planet.is_invented = True
        order = Order(
            action=OrderType.ATTACK, round=1, planet_id=planet_id_2, argument=city_id
        )
        s.add(order)
        await s.commit()

    res = await mock_actions_client.order_attack_city(planet_id_2, city_id)
    assert res == FailureReason.SUCCESS

    async with mock_actions_client.session() as s:
        planet = await s.get(Planet, planet_id_2)
        assert planet.meteorites == 1

        order = await s.get(
            Order,
            {
                "action": OrderType.ATTACK,
                "planet_id": planet_id_2,
                "round": 1,
                "argument": city_id,
            },
        )
        assert order is None


@pytest.fixture()
def orders1(planet_id_2, city_id, city_id_2):
    return [
        OrderDto(
            action=OrderType.ATTACK, planet_id=planet_id_2, round=1, argument=city_id
        ),
        OrderDto(
            action=OrderType.ATTACK, planet_id=planet_id_2, round=1, argument=city_id_2
        ),
    ]


@pytest.fixture()
def orders2(planet_id_2, planet_id_3, city_id, city_id_2):
    return [
        OrderDto(
            action=OrderType.ATTACK, planet_id=planet_id_2, round=1, argument=city_id
        ),
        OrderDto(
            action=OrderType.ATTACK, planet_id=planet_id_2, round=1, argument=city_id_2
        ),
        OrderDto(
            action=OrderType.ATTACK, planet_id=planet_id_3, round=1, argument=city_id
        ),
    ]


@pytest.mark.parametrize(
    ["orders", "alive"], [(lf("orders1"), (60, 0)), (lf("orders2"), (0, 0))]
)
@pytest.mark.asyncio
async def test_attack_cities(
    mock_actions_client, orders, alive, city_id, city_id_2, game_id
):
    async with mock_actions_client.session() as s:
        city1 = await s.get(City, city_id)
        game = await s.get(Game, game_id)
        game.round = 1
        city1.is_shielded = True
        await s.commit()

    await mock_actions_client.attack_cities(orders)

    async with mock_actions_client.session() as s:
        city1 = await s.get(City, city_id)
        city2 = await s.get(City, city_id_2)

        assert city1.development == alive[0]
        assert city2.development == alive[1]


@pytest.mark.parametrize(
    ["meteorites", "result", "exp_meteorites"],
    [(1, FailureReason.SUCCESS, 0), (0, FailureReason.NOT_ENOUGH_METEORITES, 0)],
)
@pytest.mark.asyncio
async def test_order_eco_boost(
    mock_actions_client, planet_id, game_id, meteorites, result, exp_meteorites
):
    async with mock_actions_client.session() as s:
        planet = await s.get(Planet, planet_id)
        game = await s.get(Game, game_id)
        game.round = 1
        planet.meteorites = meteorites
        planet.is_invented = True
        await s.commit()

    res = await mock_actions_client.order_eco_boost(planet_id)
    assert res == result

    async with mock_actions_client.session() as s:
        planet = await s.get(Planet, planet_id)
        assert planet.meteorites == exp_meteorites

        if res == FailureReason.SUCCESS:
            order = await s.get(
                Order,
                {
                    "action": OrderType.ECO,
                    "planet_id": planet_id,
                    "round": 1,
                    "argument": 0,
                },
            )
            assert order


@pytest.mark.asyncio
async def test_order_eco_boost_when_exists(mock_actions_client, planet_id, game_id):
    async with mock_actions_client.session() as s:
        planet = await s.get(Planet, planet_id)
        game = await s.get(Game, game_id)
        game.round = 1
        planet.is_invented = True
        order = Order(action=OrderType.ECO, round=1, planet_id=planet_id, argument=0)
        s.add(order)
        await s.commit()

    res = await mock_actions_client.order_eco_boost(planet_id)
    assert res == FailureReason.SUCCESS

    async with mock_actions_client.session() as s:
        planet = await s.get(Planet, planet_id)
        assert planet.meteorites == 1

        order = await s.get(
            Order,
            {
                "action": OrderType.ATTACK,
                "planet_id": planet_id,
                "round": 1,
                "argument": 0,
            },
        )
        assert order is None


@pytest.mark.parametrize(
    ["times", "result"],
    [
        (1, game_config.DEFAULT_GAME_ECO_RATE + game_config.ECO_BOOST_RATE),
        (2, game_config.DEFAULT_GAME_ECO_RATE + 2 * game_config.ECO_BOOST_RATE),
    ],
)
@pytest.mark.asyncio
async def test_eco_boost(mock_actions_client, game_id, times, result):
    await mock_actions_client.eco_boost(game_id, times)

    async with mock_actions_client.session() as s:
        game = await s.get(Game, game_id)
        assert game.ecorate == result


@pytest.mark.asyncio
async def test_order_sanctions(mock_actions_client, planet_id, planet_id_2, game_id):
    async with mock_actions_client.session() as s:
        game = await s.get(Game, game_id)
        game.round = 1
        await s.commit()

    await mock_actions_client.order_sanctions(planet_id, planet_id_2)

    async with mock_actions_client.session() as s:
        order = await s.get(
            Order,
            {
                "planet_id": planet_id,
                "action": OrderType.SANCTIONS,
                "round": 1,
                "argument": planet_id_2,
            },
        )
        assert order


@pytest.mark.asyncio
async def test_order_sanctions_when_exist(
    mock_actions_client, planet_id, planet_id_2, game_id
):
    async with mock_actions_client.session() as s:
        game = await s.get(Game, game_id)
        game.round = 1
        order = Order(
            planet_id=planet_id,
            action=OrderType.SANCTIONS,
            round=game.round,
            argument=planet_id_2,
        )
        s.add(order)
        await s.commit()

    await mock_actions_client.order_sanctions(planet_id, planet_id_2)

    async with mock_actions_client.session() as s:
        order = await s.get(
            Order,
            {
                "planet_id": planet_id,
                "action": OrderType.SANCTIONS,
                "round": 1,
                "argument": planet_id_2,
            },
        )
        assert order is None


@pytest.mark.asyncio
async def test_send_sanctions(mock_actions_client, planet_id, planet_id_2):
    sanctions = [
        SanctionDto(planet_from=planet_id, planet_to=planet_id_2),
        SanctionDto(planet_from=planet_id_2, planet_to=planet_id),
    ]

    await mock_actions_client.send_sanctions(sanctions)

    async with mock_actions_client.session() as s:
        for sanction in sanctions:
            db_sanc = await s.get(Sanction, sanction.model_dump())
            assert db_sanc


@pytest.mark.parametrize(
    ["balance", "amount", "result"],
    [
        (100, -100, FailureReason.NEGATIVE_AMOUNT),
        (100, 200, FailureReason.NOT_ENOUGH_MONEY),
        (200, 100, FailureReason.SUCCESS),
    ],
)
@pytest.mark.asyncio
async def test_transfer(
    mock_actions_client, planet_id, planet_id_2, balance, amount, result
):
    async with mock_actions_client.session() as s:
        planet = await s.get(Planet, planet_id)
        planet.balance = balance
        await s.commit()

    res = await mock_actions_client.transfer(planet_id, planet_id_2, amount)
    assert res == result

    if result == FailureReason.SUCCESS:
        async with mock_actions_client.session() as s:
            planet1 = await s.get(Planet, planet_id)
            planet2 = await s.get(Planet, planet_id_2)
            assert planet1.balance == balance - amount
            assert planet2.balance == game_config.DEFAULT_BALANCE + amount


@pytest.mark.asyncio
async def test_end_current_round(
    mock_actions_client, mocker, planet_id, planet_id_2, game_id, city_id
):
    all_orders = [
        Order(
            action=OrderType.ATTACK, planet_id=planet_id_2, round=2, argument=city_id
        ),
        Order(action=OrderType.DEVELOP, planet_id=planet_id, round=2, argument=city_id),
        Order(action=OrderType.SHIELD, planet_id=planet_id, round=2, argument=city_id),
        Order(action=OrderType.CREATE, planet_id=planet_id, round=2, argument=1),
        Order(action=OrderType.CREATE, planet_id=planet_id_2, round=2, argument=2),
        Order(action=OrderType.ECO, planet_id=planet_id, round=2, argument=0),
        Order(action=OrderType.ECO, planet_id=planet_id_2, round=2, argument=0),
        Order(action=OrderType.ECO, planet_id=planet_id_2, round=1, argument=0),
        Order(
            action=OrderType.SANCTIONS,
            planet_id=planet_id,
            round=2,
            argument=planet_id_2,
        ),
        Order(action=OrderType.INVENT, planet_id=planet_id_2, round=2, argument=0),
        Order(action=OrderType.INVENT, planet_id=planet_id, round=1, argument=0),
    ]

    async with mock_actions_client.session() as s:
        game = await s.get(Game, game_id)
        game.round = 2
        game.status = GameStatus.ROUND
        s.add_all(all_orders)
        await s.commit()

    mock_future = asyncio.Future()
    mock_future.set_result(None)

    mock_create_meteorites = mocker.patch.object(
        mock_actions_client, "create_meteorites", return_value=mock_future
    )
    mock_develop_cities = mocker.patch.object(
        mock_actions_client, "develop_cities", return_value=mock_future
    )
    mock_attack_cities = mocker.patch.object(
        mock_actions_client, "attack_cities", return_value=mock_future
    )
    mock_build_shield_for_cities = mocker.patch.object(
        mock_actions_client, "build_shield_for_cities", return_value=mock_future
    )
    mock_invent_for_planets = mocker.patch.object(
        mock_actions_client, "invent_for_planets", return_value=mock_future
    )
    mock_send_sanctions = mocker.patch.object(
        mock_actions_client, "send_sanctions", return_value=mock_future
    )
    mock_eco_boost = mocker.patch.object(
        mock_actions_client, "eco_boost", return_value=mock_future
    )

    await mock_actions_client.end_current_round(game_id)

    mock_create_meteorites.assert_any_call(planet_id, 1)
    mock_create_meteorites.assert_any_call(planet_id_2, 2)
    mock_develop_cities.assert_any_call(city_id)
    mock_attack_cities.assert_any_call(
        [
            OrderDto(
                action=OrderType.ATTACK,
                planet_id=planet_id_2,
                round=2,
                argument=city_id,
            )
        ]
    )
    mock_build_shield_for_cities.assert_any_call(city_id)
    mock_invent_for_planets.assert_any_call(planet_id_2)
    mock_send_sanctions.assert_any_call(
        [SanctionDto(planet_from=planet_id, planet_to=planet_id_2)]
    )
    mock_eco_boost.assert_any_call(game_id, 2)

    async with mock_actions_client.session() as s:
        game = await s.get(Game, game_id)
        assert game.status == GameStatus.MEETING


@pytest.mark.parametrize(
    ["status", "result"],
    [
        (GameStatus.MEETING, FailureReason.SUCCESS),
        (GameStatus.WAITING, FailureReason.SUCCESS),
        (GameStatus.ROUND, FailureReason.CANNOT_START_ROUND),
    ],
)
@pytest.mark.asyncio
async def test_start_new_round(
    mock_actions_client, game_id, player_ids, planet_ids, status, result
):
    round = None
    async with mock_actions_client.session() as s:
        for player_id, planet_id in zip(player_ids, planet_ids):
            planet = await s.get(Planet, planet_id)
            planet.owner_id = player_id
            await s.commit()

        game = await s.get(Game, game_id)
        game.status = status
        if status != GameStatus.WAITING:
            game.round = 1
        round = game.round
        await s.commit()

    if round is None:
        round = 0

    res = await mock_actions_client.start_new_round(game_id)
    assert res == result

    if result == FailureReason.SUCCESS:
        async with mock_actions_client.session() as s:
            game = await s.get(Game, game_id)
            new_round = game.round
            assert new_round - round == 1
