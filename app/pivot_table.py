
import pandas as pd

from database.schemas import CityDto, PlanetDto
from game.schemas import ORDER_TYPE_TRANSLATIONS, OrderInfo, OrderType


def make_pivot_table(
    path: str,
    planets: list[PlanetDto],
    cities: list[CityDto],
    order_info: list[dict[int, OrderInfo]],
) -> bool:
    writer = pd.ExcelWriter(path)

    planets_map = {planet.id: planet for planet in planets}
    cities_map = {city.id: city for city in cities}
    for i in range(len(order_info)):
        round = i + 1
        df = pd.DataFrame(
            columns=[planet.name for planet in planets],
            index=list(ORDER_TYPE_TRANSLATIONS.values()),
        )
        for order_type, row_name in ORDER_TYPE_TRANSLATIONS.items():
            for planet_id in order_info[i]:
                planet = planets_map[planet_id]
                if order_type in (OrderType.ECO, OrderType.INVENT):
                    df.loc[row_name, planet.name] = (
                        'Да'
                        if order_info[i][planet_id].get(order_type, False)
                        else 'Нет'
                    )
                elif order_type == OrderType.CREATE:
                    df.loc[row_name, planet.name] = str(
                        order_info[i][planet_id].get(order_type, 0)
                    )
                elif order_type == OrderType.SANCTIONS:
                    df.loc[row_name, planet.name] = ',\n'.join(
                        [
                            planets_map[planet_id].name
                            for planet_id in order_info[i][planet_id].get(
                                order_type, []
                            )
                        ]
                    )
                elif order_type == OrderType.ATTACK:
                    df.loc[row_name, planet.name] = ',\n'.join(
                        [
                            f'{cities_map[city_id].name} ({planets_map[cities_map[city_id].planet_id]})'
                            for city_id in order_info[i][planet_id].get(order_type, [])
                        ]
                    )
                else:
                    df.loc[row_name, planet.name] = ',\n'.join(
                        [
                            cities_map[city_id].name
                            for city_id in order_info[i][planet_id].get(order_type, [])
                        ]
                    )
        df.to_excel(writer, f'{round} раунд')
    writer.close()
