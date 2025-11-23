from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Literal, TYPE_CHECKING
import random

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
    accuracy_stage: int = 0
    evasion_stage: int = 0
    volatiles: Dict[str, Any] = field(default_factory=dict)
    moves: List["MoveData"] = field(default_factory=list)
    overrides: Dict[str, Any] = field(default_factory=dict)
    weight: float = 100.0
    substitute_hp: Optional[int] = None
    last_move_used: Optional[str] = None

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

    @property
    def max_hp(self) -> int:
        return self.calc_stat("HP")

    def calc_stat(self, stat: str) -> int:
        base = self.base_stats.get(stat, 0)
        iv = self.ivs.get(stat, 31)
        ev = 0  # Run & Bun: EVs are removed

        lvl = self.level

        if stat == "HP":
            if base == 1:
                return 1
            return ((2 * base + iv + ev // 4) * lvl // 100) + lvl + 10

        raw = ((2 * base + iv + ev // 4) * lvl // 100) + 5

        nature_multipliers: Dict[str, tuple[str, str]] = {
            # Atk+ natures
            "Lonely": ("Atk", "Def"),
            "Brave": ("Atk", "Spe"),
            "Adamant": ("Atk", "SpA"),
            "Naughty": ("Atk", "SpD"),
            # Def+ natures
            "Bold": ("Def", "Atk"),
            "Relaxed": ("Def", "Spe"),
            "Impish": ("Def", "SpA"),
            "Lax": ("Def", "SpD"),
            # Spe+ natures
            "Timid": ("Spe", "Atk"),
            "Hasty": ("Spe", "Def"),
            "Jolly": ("Spe", "SpA"),
            "Naive": ("Spe", "SpD"),
            # SpA+ natures
            "Modest": ("SpA", "Atk"),
            "Mild": ("SpA", "Def"),
            "Quiet": ("SpA", "Spe"),
            "Rash": ("SpA", "SpD"),
            # SpD+ natures
            "Calm": ("SpD", "Atk"),
            "Gentle": ("SpD", "Def"),
            "Sassy": ("SpD", "Spe"),
            "Careful": ("SpD", "SpA"),
        }

        if self.nature in nature_multipliers:
            inc, dec = nature_multipliers[self.nature]
            if stat == inc:
                raw = (raw * 110) // 100
            elif stat == dec:
                raw = (raw * 90) // 100

        # Stat stages + Soul Dew integration
        stage = self.stat_stages.get(stat, 0)
        if (
            self.item == "Soul Dew"
            and self.species in ("Latias", "Latios")
            and stat in ("SpA", "SpD")
        ):
            stage += 1

        if stage > 6:
            stage = 6
        if stage < -6:
            stage = -6

        if stage > 0:
            raw = raw * (2 + stage) // 2
        elif stage < 0:
            raw = raw * 2 // (2 - stage)

        if self.ability == "Marvel Scale" and self.status is not None and stat == "Def":
            raw = raw * 3 // 2

        return max(1, raw)
    
    def is_grounded(self, field: "FieldState") -> bool:
        if self.current_hp <= 0:
            return False

        if field.is_gravity:
            return True

        if "Flying" in self.types:
            if self.item == "Iron Ball":
                pass
            else:
                return False

        if self.ability == "Levitate":
            return False

        if self.volatiles.get("magnet_rise") or self.volatiles.get("telekinesis"):
            return False

        if self.item == "Air Balloon":
            return False

        return True

    def get_effective_speed(self, field: "FieldState", side_idx: Optional[int] = None) -> int:
        base_speed = self.calc_stat("Spe")
        mult = 1.0
        w = field.weather

        if w == "Rain" and self.ability == "Swift Swim":
            mult *= 2.0
        if w == "Sun" and self.ability == "Chlorophyll":
            mult *= 2.0
        if w == "Sandstorm" and self.ability == "Sand Rush":
            mult *= 2.0
        if w in ("Hail", "Snow") and self.ability == "Slush Rush":
            mult *= 2.0

        if self.status == "par":
            if self.ability != "Quick Feet":
                mult *= 0.25
        if self.ability == "Quick Feet" and self.status is not None:
            mult *= 1.5

        if side_idx is not None and 0 <= side_idx < len(field.tailwind):
            if field.tailwind[side_idx]:
                mult *= 2.0

        return max(1, int(base_speed * mult))

    def apply_status(self, status: str) -> bool:
        status = status.lower()
        if self.status is not None:
            return False

        if status == "slp":
            self.volatiles["sleep_turns"] = random.randint(1, 3)
        elif status == "tox":
            self.toxic_counter = 1
        elif status == "psn":
            self.toxic_counter = 0
        elif status == "frz":
            self.volatiles["frozen"] = True
        else:
            self.volatiles.pop("sleep_turns", None)

        self.status = status
        if self.item == "Lum Berry":
            self.cure_status()
            self.item = None
        return True

    def cure_status(self) -> None:
        current = self.status
        if current == "slp":
            self.volatiles.pop("sleep_turns", None)
        elif current == "frz":
            self.volatiles.pop("frozen", None)
        if current == "tox":
            self.toxic_counter = 0
        elif current == "psn":
            self.toxic_counter = 0
        self.status = None

    def get_stage_value(self, stat: str) -> int:
        key = stat.lower()
        if key in ("acc", "accuracy"):
            return self.accuracy_stage
        if key in ("eva", "evasion"):
            return self.evasion_stage
        normalized = stat
        if normalized not in self.stat_stages:
            normalized = stat.capitalize()
        return self.stat_stages.get(normalized, 0)

    def set_stage_value(self, stat: str, value: int) -> None:
        clamped = max(-6, min(6, value))
        key = stat.lower()
        if key in ("acc", "accuracy"):
            self.accuracy_stage = clamped
        elif key in ("eva", "evasion"):
            self.evasion_stage = clamped
        else:
            normalized = stat
            if normalized not in self.stat_stages:
                normalized = stat.capitalize()
            self.stat_stages[normalized] = clamped

    def clear_negative_stages(self) -> None:
        for stat in list(self.stat_stages.keys()):
            if self.stat_stages[stat] < 0:
                self.stat_stages[stat] = 0
        if self.accuracy_stage < 0:
            self.accuracy_stage = 0
        if self.evasion_stage < 0:
            self.evasion_stage = 0

    def _handle_stat_drop_reactions(self, from_opponent: bool) -> None:
        if from_opponent and self.item == "Eject Pack":
            self.volatiles["eject_pack_trigger"] = True
        if self.item == "White Herb":
            self.clear_negative_stages()
            self.item = None
        if from_opponent:
            if self.ability == "Defiant":
                self.change_stat_stage("Atk", 2, source=self, from_opponent=False, ignore_blockers=True, allow_contrary=False)
            if self.ability == "Competitive":
                self.change_stat_stage("SpA", 2, source=self, from_opponent=False, ignore_blockers=True, allow_contrary=False)

    def change_stat_stage(
        self,
        stat: str,
        stages: int,
        *,
        source: Optional["PokemonState"] = None,
        from_opponent: bool = False,
        ignore_blockers: bool = False,
        allow_contrary: bool = True,
        allow_simple: bool = True,
        intimidate: bool = False,
        via_mirror_armor: bool = False,
    ) -> int:
        if stages == 0:
            return 0

        delta = stages
        if allow_simple and self.ability == "Simple":
            delta *= 2
        if allow_contrary and self.ability == "Contrary":
            delta *= -1

        opponent_effect = from_opponent or (source is not None and source is not self)
        lowered = False

        if delta < 0:
            if intimidate and self.ability in {"Own Tempo", "Oblivious", "Scrappy", "Inner Focus"}:
                return 0
            if not ignore_blockers and opponent_effect:
                if self.ability in {"Clear Body", "White Smoke", "Full Metal Body"}:
                    return 0
                if self.ability == "Hyper Cutter" and stat.lower() in ("atk", "attack"):
                    return 0
                if self.ability == "Keen Eye" and stat.lower() in ("accuracy", "acc"):
                    return 0
                if self.item == "Clear Amulet":
                    return 0
            if (
                opponent_effect
                and self.ability == "Mirror Armor"
                and source is not None
                and source is not self
                and not via_mirror_armor
            ):
                source.change_stat_stage(
                    stat,
                    stages,
                    source=self,
                    from_opponent=True,
                    ignore_blockers=False,
                    allow_contrary=allow_contrary,
                    allow_simple=allow_simple,
                    intimidate=intimidate,
                    via_mirror_armor=True,
                )
                return 0

        current = self.get_stage_value(stat)
        new_stage = max(-6, min(6, current + delta))
        if new_stage == current:
            return 0

        self.set_stage_value(stat, new_stage)

        if new_stage < current:
            lowered = True

        if lowered:
            self._handle_stat_drop_reactions(opponent_effect)

        return new_stage - current


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
    toxic_spikes: List[int] = field(default_factory=lambda: [0, 0])
    sticky_web: List[bool] = field(default_factory=lambda: [False, False])
    steelsurge: List[bool] = field(default_factory=lambda: [False, False])
    tailwind: List[bool] = field(default_factory=lambda: [False, False])
    reflect: List[bool] = field(default_factory=lambda: [False, False])
    light_screen: List[bool] = field(default_factory=lambda: [False, False])
    aurora_veil: List[bool] = field(default_factory=lambda: [False, False])
    tailwind_turns: List[int] = field(default_factory=lambda: [0, 0])
    reflect_turns: List[int] = field(default_factory=lambda: [0, 0])
    light_screen_turns: List[int] = field(default_factory=lambda: [0, 0])
    aurora_veil_turns: List[int] = field(default_factory=lambda: [0, 0])
    gmax_vinelash_turns: List[int] = field(default_factory=lambda: [0, 0])
    gmax_wildfire_turns: List[int] = field(default_factory=lambda: [0, 0])
    gmax_cannonade_turns: List[int] = field(default_factory=lambda: [0, 0])
    gmax_volcalith_turns: List[int] = field(default_factory=lambda: [0, 0])

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
