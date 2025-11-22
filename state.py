from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Literal, TYPE_CHECKING

if TYPE_CHECKING:
    from data_loader import MoveData


STAT_NAMES = ("HP", "Atk", "Def", "SpA", "SpD", "Spe")


@dataclass
class PokemonState:
    species: str
    level: int
    base_stats: Dict[str, int]
    types: List[str]
    ability: str
    item: Optional[str] = None
    nature: str = "Hardy"
    gender: Optional[str] = None
    ability_on: bool = True
    is_dynamaxed: bool = False
    is_salt_cure: bool = False
    allies_fainted: int = 0
    ivs: Dict[str, int] = field(
        default_factory=lambda: {stat: 31 for stat in STAT_NAMES}
    )
    evs: Dict[str, int] = field(
        default_factory=lambda: {stat: 0 for stat in STAT_NAMES}
    )
    current_hp: int = 0
    original_cur_hp: Optional[int] = None
    status: Optional[str] = None
    toxic_counter: int = 0
    stat_stages: Dict[str, int] = field(
        default_factory=lambda: {stat: 0 for stat in STAT_NAMES[1:]}
    )
    volatiles: Dict[str, Any] = field(default_factory=dict)
    tera_type: Optional[str] = None
    moves: List["MoveData"] = field(default_factory=list)
    overrides: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        max_hp = self.calc_stat("HP")
        if self.current_hp <= 0:
            self.current_hp = max_hp
        if self.original_cur_hp is None:
            self.original_cur_hp = self.current_hp

    @property
    def name(self) -> str:
        return self.species

    @name.setter
    def name(self, value: str) -> None:
        self.species = value

    @property
    def boosts(self) -> Dict[str, int]:
        return self.stat_stages

    def calc_stat(self, stat: str) -> int:
        base = self.base_stats.get(stat, 0)
        iv = self.ivs.get(stat, 31)
        ev = self.evs.get(stat, 0)
        lvl = self.level

        if stat == "HP":
            if base == 1:
                return 1
            return ((2 * base + iv + ev // 4) * lvl // 100) + lvl + 10

        raw = ((2 * base + iv + ev // 4) * lvl // 100) + 5

        nature_multipliers: Dict[str, tuple[str, str]] = {
            "Adamant": ("Atk", "SpA"),
            "Bold": ("Def", "Atk"),
            "Modest": ("SpA", "Atk"),
            "Timid": ("Spe", "Atk"),
        }
        if self.nature in nature_multipliers:
            inc, dec = nature_multipliers[self.nature]
            if stat == inc:
                raw = (raw * 110) // 100
            elif stat == dec:
                raw = (raw * 90) // 100

        if stat in self.stat_stages:
            stage = self.stat_stages[stat]
            if stage > 0:
                raw = raw * (2 + stage) // 2
            elif stage < 0:
                raw = raw * 2 // (2 - stage)

        return max(1, raw)

    def is_grounded(self, field: "FieldState") -> bool:
        if field.is_gravity:
            return True
        if "Flying" in self.types or self.ability == "Levitate":
            if self.item == "Iron Ball":
                return True
            return False
        if self.item == "Air Balloon":
            return False
        return True


@dataclass
class FieldSideState:
    spikes: int = 0
    steelsurge: bool = False
    vinelash: bool = False
    wildfire: bool = False
    cannonade: bool = False
    volcalith: bool = False
    is_sr: bool = False
    is_reflect: bool = False
    is_light_screen: bool = False
    is_protected: bool = False
    is_seeded: bool = False
    is_foresight: bool = False
    is_tailwind: bool = False
    is_helping_hand: bool = False
    is_flower_gift: bool = False
    is_friend_guard: bool = False
    is_aurora_veil: bool = False
    is_battery: bool = False
    is_power_spot: bool = False
    is_switching: Optional[Literal["out", "in"]] = None


@dataclass
class FieldState:
    game_type: str = "Singles"
    weather: Optional[str] = None
    terrain: Optional[str] = None
    weather_turns: int = 0
    terrain_turns: int = 0
    is_magic_room: bool = False
    is_wonder_room: bool = False
    is_gravity: bool = False
    is_aura_break: bool = False
    is_fairy_aura: bool = False
    is_dark_aura: bool = False
    is_beads_of_ruin: bool = False
    is_sword_of_ruin: bool = False
    is_tablets_of_ruin: bool = False
    is_vessel_of_ruin: bool = False
    attacker_side: FieldSideState = field(default_factory=FieldSideState)
    defender_side: FieldSideState = field(default_factory=FieldSideState)
    spikes: List[int] = field(default_factory=lambda: [0, 0])
    stealth_rocks: List[bool] = field(default_factory=lambda: [False, False])
    reflect: List[bool] = field(default_factory=lambda: [False, False])
    light_screen: List[bool] = field(default_factory=lambda: [False, False])
    aurora_veil: List[bool] = field(default_factory=lambda: [False, False])

    def has_weather(self, *weathers: str) -> bool:
        return bool(self.weather and self.weather in weathers)

    def has_terrain(self, *terrains: str) -> bool:
        return bool(self.terrain and self.terrain in terrains)


@dataclass
class SideState:
    active: List[PokemonState]
    party: List[PokemonState]
    is_player: bool = False


@dataclass
class BattleState:
    sides: List[SideState]
    field: FieldState
    turn: int = 1

    def get_opponent(self, side_idx: int) -> SideState:
        return self.sides[1 - side_idx]
