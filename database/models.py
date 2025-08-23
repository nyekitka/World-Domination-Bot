import re
from sqlalchemy import BigInteger, Enum, ForeignKey, PrimaryKeyConstraint
from sqlalchemy.orm import (
    declared_attr,
    DeclarativeBase,
    Mapped,
    mapped_column,
)

from database.config import game_config
from database.schemas import GameStatus, MessageType, OrderType


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


class InfoMessage(ModelBase):
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    planet_id: Mapped[int] = mapped_column(
        ForeignKey("planet.id", ondelete="CASCADE"), nullable=False
    )
    message_type: Mapped[MessageType] = mapped_column(
        Enum(MessageType, name="MessageType"), nullable=False
    )


class Order(ModelBase):
    action: Mapped[OrderType] = mapped_column(
        Enum(OrderType, name="OrderType"), nullable=False
    )
    planet_id: Mapped[int] = mapped_column(
        ForeignKey("planet.id", ondelete="CASCADE"), nullable=False
    )
    argument: Mapped[int]
    round: Mapped[int] = mapped_column(nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint(action, planet_id, round, name="order_pkey"),
    )


class PlanetMessage(ModelBase):
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("planet.id", ondelete="CASCADE"), nullable=False
    )
    planet_id: Mapped[int] = mapped_column(
        ForeignKey("planet.id", ondelete="CASCADE"), nullable=False
    )
    message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    message_type: Mapped[MessageType] = mapped_column(
        Enum(OrderType, name="OrderType"), nullable=False
    )

    __table_args__ = (
        PrimaryKeyConstraint(
            owner_id, planet_id, message_id, name="planet_message_pkey"
        ),
    )


class Sanction(ModelBase):
    planet_from: Mapped[int] = mapped_column(
        ForeignKey("planet.id", ondelete="CASCADE"), nullable=False
    )
    planet_to: Mapped[int] = mapped_column(
        ForeignKey("planet.id", ondelete="CASCADE"), nullable=False
    )

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
