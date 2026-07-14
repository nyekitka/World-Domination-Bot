import re
from sqlalchemy import (
    BigInteger, Enum,
    ForeignKey, PrimaryKeyConstraint,
    func, inspect, select
)
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import (
    declared_attr,
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship
)

from database.schemas import GameStatus
from game.schemas import OrderType
from game.config import game_config

class ModelBase(DeclarativeBase):
    @declared_attr.directive
    def __tablename__(cls) -> str:
        match = re.findall(r"[A-Z][a-z]*", cls.__name__)
        return "_".join(list(map(lambda x: x.lower(), match)))


class Game(ModelBase):
    id: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[GameStatus] = mapped_column(
        Enum(GameStatus, name="GameStatus"), nullable=False, default=GameStatus.WAITING
    )
    ecorate: Mapped[int] = mapped_column(
        nullable=False, default=game_config.DEFAULT_GAME_ECO_RATE
    )
    round: Mapped[int] = mapped_column(nullable=True)
    num_planets: Mapped[int] = mapped_column(nullable=True)

    planets: Mapped[list['Planet']] = relationship(back_populates='game')


class Player(ModelBase):
    tg_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("game.id"), nullable=True)


class Admin(ModelBase):
    tg_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("game.id"), nullable=True)


class Planet(ModelBase):
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    game_id: Mapped[int] = mapped_column(
        ForeignKey("game.id", ondelete="CASCADE"), nullable=False
    )
    owner_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("player.tg_id"), nullable=True
    )
    balance: Mapped[int] = mapped_column(
        nullable=False, default=game_config.DEFAULT_BALANCE
    )
    meteorites: Mapped[int] = mapped_column(nullable=False, default=0)
    is_invented: Mapped[bool] = mapped_column(nullable=False, default=False)

    game: Mapped[Game] = relationship(back_populates='planets')
    cities: Mapped[list['City']] = relationship(back_populates='planet')

    @hybrid_property
    def development(self) -> float:
        state = inspect(self)

        if 'cities' in state.unloaded or 'game' in state.unloaded:
            return None
        if len(self.cities) == 0:
            return 0
        avg_development = sum(
            city.development
            for city in self.cities
        ) / len(self.cities)
        return avg_development * self.game.ecorate / 100
    
    @development.expression
    def development(cls):
        avg_development = (
            select(func.avg(City.development))
            .where(City.planet_id == cls.id)
            .scalar_subquery()
        )

        eco_rate = (
            select(Game.ecorate / 100)
            .where(Game.id == cls.game_id)
            .scalar_subquery()
        )

        return func.coalesce(avg_development, 0.0) * eco_rate


class City(ModelBase):
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    planet_id: Mapped[int] = mapped_column(
        ForeignKey("planet.id", ondelete="CASCADE"), nullable=False
    )
    is_shielded: Mapped[bool] = mapped_column(nullable=False, default=False)
    development: Mapped[int] = mapped_column(
        nullable=False, default=game_config.DEFAULT_DEVELOPMENT
    )

    planet: Mapped[Planet] = relationship(back_populates='cities')

    @hybrid_property
    def rate_of_life(self):
        state = inspect(self)

        if 'planet' in state.unloaded:
            return None
        return self.development * self.planet.game.ecorate / 100
    
    @rate_of_life.expression
    def rate_of_life(cls):
        eco_rate = (
            select(Game.ecorate)
            .join(Planet, Planet.game_id == Game.id)
            .join(City, City.planet_id == Planet.id)
            .where(City.id == cls.id)
        )
        return eco_rate * cls.development / 100


class Order(ModelBase):
    action: Mapped[OrderType] = mapped_column(
        Enum(OrderType, name="OrderType"), nullable=False
    )
    planet_id: Mapped[int] = mapped_column(
        ForeignKey("planet.id", ondelete="CASCADE"), nullable=False
    )
    argument: Mapped[int] = mapped_column(default=0, nullable=False)
    round: Mapped[int] = mapped_column(nullable=False, default=0)

    __table_args__ = (
        PrimaryKeyConstraint(action, planet_id, round, argument, name="order_pkey"),
    )


class Sanction(ModelBase):
    planet_from: Mapped[int] = mapped_column(
        ForeignKey("planet.id", ondelete="CASCADE"), nullable=False
    )
    planet_to: Mapped[int] = mapped_column(
        ForeignKey("planet.id", ondelete="CASCADE"), nullable=False
    )
    num_round: Mapped[int] = mapped_column(nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint(planet_from, planet_to, name="sanction_pkey"),
    )


class Negotiation(ModelBase):
    planet_from: Mapped[int] = mapped_column(
        ForeignKey("planet.id", ondelete="CASCADE"), nullable=False
    )
    planet_to: Mapped[int] = mapped_column(
        ForeignKey("planet.id", ondelete="CASCADE"), nullable=False
    )

    __table_args__ = (
        PrimaryKeyConstraint(planet_from, planet_to, name="negotiation_pkey"),
    )
