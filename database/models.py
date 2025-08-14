import re
from sqlalchemy import BigInteger, CheckConstraint, ForeignKey
from sqlalchemy.orm import (
    declared_attr,
    DeclarativeBase,
    Mapped,
    mapped_column,
)

from database.schemas import GameStatus, MessageType, OrderType


class ModelBase(DeclarativeBase):
    @declared_attr.directive
    def __tablename__(cls) -> str:
        match = re.findall(r"[A-Z][a-z]*", cls.__name__)
        return "_".join(list(map(lambda x: x.lower(), match)))


class Game(ModelBase):
    id: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[GameStatus] = mapped_column(
        nullable=False, default=GameStatus.WAITING
    )
    ecorate: Mapped[int] = mapped_column(nullable=False, default=95)
    round: Mapped[int] = mapped_column(nullable=True)

    __table_args__ = CheckConstraint(
        "status == 'waiting' or status == 'ended' or round IS NOT NULL",
        name="round_partly_nullable",
    )


class Player(ModelBase):
    tg_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("game.id"))


class Admin(ModelBase):
    tg_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("game.id"), nullable=True)


class Planet(ModelBase):
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    game_id: Mapped[int] = mapped_column(
        ForeignKey("game.id", ondelete="CASCADE"), nullable=False
    )
    owner_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("player.id"))
    balance: Mapped[int] = mapped_column(nullable=False, default=1000)
    meteorites: Mapped[int] = mapped_column(nullable=False, default=0)
    is_invented: Mapped[bool] = mapped_column(nullable=False, default=False)


class City(ModelBase):
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    planet_id: Mapped[int] = mapped_column(
        ForeignKey("planet.id", ondelete="CASCADE"), nullable=False
    )
    is_shielded: Mapped[bool] = mapped_column(nullable=False, default=False)
    development: Mapped[int] = mapped_column(nullable=False, default=60)


class InfoMessage(ModelBase):
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    planet_id: Mapped[int] = mapped_column(
        ForeignKey("planet.id", ondelete="CASCADE"), nullable=False
    )
    message_type: Mapped[MessageType] = mapped_column(nullable=False)


class Order(ModelBase):
    action: Mapped[OrderType] = mapped_column(nullable=False)
    planet_id: Mapped[int] = mapped_column(
        ForeignKey("planet.id", ondelete="CASCADE"), nullable=False
    )
    argument: Mapped[int]
    round: Mapped[int] = mapped_column(nullable=False)


class PlanetMessage(ModelBase):
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("planet.id", ondelete="CASCADE"), nullable=False
    )
    planet_id: Mapped[int] = mapped_column(
        ForeignKey("planet.id", ondelete="CASCADE"), nullable=False
    )
    message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    message_type: Mapped[MessageType] = mapped_column(nullable=False)


class Sanction(ModelBase):
    planet_from: Mapped[int] = mapped_column(
        ForeignKey("planet.id", ondelete="CASCADE"), nullable=False
    )
    planet_to: Mapped[int] = mapped_column(
        ForeignKey("planet.id", ondelete="CASCADE"), nullable=False
    )


class Negotiation(ModelBase):
    planet_from: Mapped[int] = mapped_column(
        ForeignKey("planet.id", ondelete="CASCADE"), nullable=False
    )
    planet_to: Mapped[int] = mapped_column(
        ForeignKey("planet.id", ondelete="CASCADE"), nullable=False
    )
