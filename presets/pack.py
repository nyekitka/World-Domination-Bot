from pydantic import BaseModel, TypeAdapter

pack_file_path = "./presets/packs.json"


class PackCity(BaseModel):
    name: str


class PackPlanet(BaseModel):
    name: str
    cities: list[PackCity]


class Pack(BaseModel):
    name: str
    planets: list[PackPlanet]


with open(pack_file_path, encoding='utf-8') as file:
    _packs = file.read()

packs = TypeAdapter(list[Pack]).validate_json(_packs)
