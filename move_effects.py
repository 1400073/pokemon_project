# move_effects.py
from dataclasses import dataclass
from typing import Literal, Optional, List, Dict, Tuple
from state import BattleState, PokemonState
import random


EffectKind = Literal[
    "stat_stage",
    "status",
    "side_condition",
    "weather",
    "terrain",
    "hazard",
    "heal",
    "protect",
    "substitute",
    "phaze",
]

EffectTarget = Literal[
    "self",
    "foe",
    "self_side",
    "foe_side",
    "field",
]


@dataclass
class EffectSpec:
    kind: EffectKind
    target: EffectTarget
    stat: Optional[str] = None
    stages: int = 0
    status: Optional[str] = None
    condition: Optional[str] = None
    amount: Optional[int] = None
    duration: Optional[int] = None
    chance: int = 100
    hazard: Optional[str] = None


MOVE_EFFECTS: Dict[str, List[EffectSpec]] = {
    # --- Self-boosting setup moves ---

    "Swords Dance": [
        EffectSpec(kind="stat_stage", target="self", stat="Atk", stages=2)
    ],
    "Nasty Plot": [
        EffectSpec(kind="stat_stage", target="self", stat="SpA", stages=2)
    ],
    "Calm Mind": [
        EffectSpec(kind="stat_stage", target="self", stat="SpA", stages=1),
        EffectSpec(kind="stat_stage", target="self", stat="SpD", stages=1),
    ],
    "Bulk Up": [
        EffectSpec(kind="stat_stage", target="self", stat="Atk", stages=1),
        EffectSpec(kind="stat_stage", target="self", stat="Def", stages=1),
    ],
    # Dragon Dance: +1 Atk, +1 Spe 
    "Dragon Dance": [
        EffectSpec(kind="stat_stage", target="self", stat="Atk", stages=1),
        EffectSpec(kind="stat_stage", target="self", stat="Spe", stages=1),
    ],
    "Work Up": [
        EffectSpec(kind="stat_stage", target="self", stat="Atk", stages=1),
        EffectSpec(kind="stat_stage", target="self", stat="SpA", stages=1),
    ],
    # Growth: in Gen 8 it’s +1 Atk/+1 SpA (we ignore Sun bonus)
    "Growth": [
        EffectSpec(kind="stat_stage", target="self", stat="Atk", stages=1),
        EffectSpec(kind="stat_stage", target="self", stat="SpA", stages=1),
    ],
    "Iron Defense": [
        EffectSpec(kind="stat_stage", target="self", stat="Def", stages=2),
    ],
    "Acid Armor": [
        EffectSpec(kind="stat_stage", target="self", stat="Def", stages=2),
    ],
    "Barrier": [
        EffectSpec(kind="stat_stage", target="self", stat="Def", stages=2),
    ],
    "Cotton Guard": [
        EffectSpec(kind="stat_stage", target="self", stat="Def", stages=3),
    ],
    "Amnesia": [
        EffectSpec(kind="stat_stage", target="self", stat="SpD", stages=2),
    ],
    "Cosmic Power": [
        EffectSpec(kind="stat_stage", target="self", stat="Def", stages=1),
        EffectSpec(kind="stat_stage", target="self", stat="SpD", stages=1),
    ],
    # Quiver Dance: +1 SpA, +1 SpD, +1 Spe 
    "Quiver Dance": [
        EffectSpec(kind="stat_stage", target="self", stat="SpA", stages=1),
        EffectSpec(kind="stat_stage", target="self", stat="SpD", stages=1),
        EffectSpec(kind="stat_stage", target="self", stat="Spe", stages=1),
    ],
    # Shell Smash: +2 Atk, +2 SpA, +2 Spe, -1 Def, -1 SpD 
    "Shell Smash": [
        EffectSpec(kind="stat_stage", target="self", stat="Atk", stages=2),
        EffectSpec(kind="stat_stage", target="self", stat="SpA", stages=2),
        EffectSpec(kind="stat_stage", target="self", stat="Spe", stages=2),
        EffectSpec(kind="stat_stage", target="self", stat="Def", stages=-1),
        EffectSpec(kind="stat_stage", target="self", stat="SpD", stages=-1),
    ],
    "Coil": [
        EffectSpec(kind="stat_stage", target="self", stat="Atk", stages=1),
        EffectSpec(kind="stat_stage", target="self", stat="Def", stages=1),
    ],
    # Non-Ghost Curse: +1 Atk, +1 Def, -1 Spe
    "Curse": [
        EffectSpec(kind="stat_stage", target="self", stat="Atk", stages=1),
        EffectSpec(kind="stat_stage", target="self", stat="Def", stages=1),
        EffectSpec(kind="stat_stage", target="self", stat="Spe", stages=-1),
    ],
    # Speed boosting
    "Agility": [
        EffectSpec(kind="stat_stage", target="self", stat="Spe", stages=2),
    ],
    "Rock Polish": [
        EffectSpec(kind="stat_stage", target="self", stat="Spe", stages=2),
    ],
    "Autotomize": [
        EffectSpec(kind="stat_stage", target="self", stat="Spe", stages=2),
    ],

    # --- Target stat-lowering moves (simple stage changes only) ---

    "Growl": [
        EffectSpec(kind="stat_stage", target="foe", stat="Atk", stages=-1),
    ],
    "Charm": [
        EffectSpec(kind="stat_stage", target="foe", stat="Atk", stages=-2),
    ],
    "Feather Dance": [
        EffectSpec(kind="stat_stage", target="foe", stat="Atk", stages=-2),
    ],
    "Tail Whip": [
        EffectSpec(kind="stat_stage", target="foe", stat="Def", stages=-1),
    ],
    "Leer": [
        EffectSpec(kind="stat_stage", target="foe", stat="Def", stages=-1),
    ],
    "Screech": [
        EffectSpec(kind="stat_stage", target="foe", stat="Def", stages=-2),
    ],
    "Fake Tears": [
        EffectSpec(kind="stat_stage", target="foe", stat="SpD", stages=-2),
    ],
    "Metal Sound": [
        EffectSpec(kind="stat_stage", target="foe", stat="SpD", stages=-2),
    ],
    "Cotton Spore": [
        EffectSpec(kind="stat_stage", target="foe", stat="Spe", stages=-2),
    ],
    "String Shot": [
        EffectSpec(kind="stat_stage", target="foe", stat="Spe", stages=-1),
    ],
    "Scary Face": [
        EffectSpec(kind="stat_stage", target="foe", stat="Spe", stages=-2),
    ],
    "Tickle": [
        EffectSpec(kind="stat_stage", target="foe", stat="Atk", stages=-1),
        EffectSpec(kind="stat_stage", target="foe", stat="Def", stages=-1),
    ],
    "Memento": [
        EffectSpec(kind="stat_stage", target="foe", stat="Atk", stages=-2),
        EffectSpec(kind="stat_stage", target="foe", stat="SpA", stages=-2),
        # User KO effect is handled elsewhere if you want it
    ],
    "Parting Shot": [
        EffectSpec(kind="stat_stage", target="foe", stat="Atk", stages=-1),
        EffectSpec(kind="stat_stage", target="foe", stat="SpA", stages=-1),
        # Switching effect not modeled here
    ],
    "Noble Roar": [
        EffectSpec(kind="stat_stage", target="foe", stat="Atk", stages=-1),
        EffectSpec(kind="stat_stage", target="foe", stat="SpA", stages=-1),
    ],

    # --- Status conditions (non-volatile) ---

    "Thunder Wave": [
        EffectSpec(kind="status", target="foe", status="par")
    ],
    "Stun Spore": [
        EffectSpec(kind="status", target="foe", status="par")
    ],
    "Glare": [
        EffectSpec(kind="status", target="foe", status="par")
    ],
    "Will-O-Wisp": [
        EffectSpec(kind="status", target="foe", status="brn")
    ],
    "Toxic": [
        EffectSpec(kind="status", target="foe", status="tox")
    ],
    "Poison Powder": [
        EffectSpec(kind="status", target="foe", status="psn")
    ],
    # Sleep family
    "Sleep Powder": [
        EffectSpec(kind="status", target="foe", status="slp")
    ],
    "Spore": [
        EffectSpec(kind="status", target="foe", status="slp")
    ],
    "Hypnosis": [
        EffectSpec(kind="status", target="foe", status="slp")
    ],
    "Sing": [
        EffectSpec(kind="status", target="foe", status="slp")
    ],
    "Lovely Kiss": [
        EffectSpec(kind="status", target="foe", status="slp")
    ],
    "Dark Void": [
        EffectSpec(kind="status", target="foe", status="slp")
    ],
    # Yawn is really “drowsy then sleep”; we approximate as immediate sleep
    "Yawn": [
        EffectSpec(kind="status", target="foe", status="slp")
    ],

    # --- Entry hazards ---

    "Stealth Rock": [
        EffectSpec(kind="hazard", target="foe_side", hazard="stealth_rock")
    ],
    "Spikes": [
        EffectSpec(kind="hazard", target="foe_side", hazard="spikes")
    ],
    "Toxic Spikes": [
        EffectSpec(kind="hazard", target="foe_side", hazard="toxic_spikes")
    ],
    "Sticky Web": [
        EffectSpec(kind="hazard", target="foe_side", hazard="sticky_web")
    ],
    "G-Max Steelsurge": [
        EffectSpec(kind="hazard", target="foe_side", hazard="steelsurge")
    ],

    # --- Screens and team side conditions ---

    "Reflect": [
        EffectSpec(
            kind="side_condition",
            target="self_side",
            condition="reflect",
            duration=5,
        )
    ],
    "Light Screen": [
        EffectSpec(
            kind="side_condition",
            target="self_side",
            condition="light_screen",
            duration=5,
        )
    ],
    "Aurora Veil": [
        EffectSpec(
            kind="side_condition",
            target="self_side",
            condition="aurora_veil",
            duration=5,
        )
    ],
    "Tailwind": [
        EffectSpec(
            kind="side_condition",
            target="self_side",
            condition="tailwind",
            duration=4,
        )
    ],

    # --- Weather and terrain ---

    "Rain Dance": [
        EffectSpec(kind="weather", target="field", condition="Rain", duration=5)
    ],
    "Sunny Day": [
        EffectSpec(kind="weather", target="field", condition="Sun", duration=5)
    ],
    "Sandstorm": [
        EffectSpec(kind="weather", target="field", condition="Sand", duration=5)
    ],
    "Hail": [
        EffectSpec(kind="weather", target="field", condition="Hail", duration=5)
    ],

    "Electric Terrain": [
        EffectSpec(kind="terrain", target="field", condition="Electric", duration=5)
    ],
    "Grassy Terrain": [
        EffectSpec(kind="terrain", target="field", condition="Grassy", duration=5)
    ],
    "Misty Terrain": [
        EffectSpec(kind="terrain", target="field", condition="Misty", duration=5)
    ],
    "Psychic Terrain": [
        EffectSpec(kind="terrain", target="field", condition="Psychic", duration=5)
    ],

    # --- Protect-style moves (including Run & Bun Defend Order change) ---

    "Protect": [
        EffectSpec(kind="protect", target="self")
    ],
    "Detect": [
        EffectSpec(kind="protect", target="self")
    ],
    "King's Shield": [
        EffectSpec(kind="protect", target="self")
    ],
    "Spiky Shield": [
        EffectSpec(kind="protect", target="self")
    ],
    "Baneful Bunker": [
        EffectSpec(kind="protect", target="self")
    ],
    "Obstruct": [
        EffectSpec(kind="protect", target="self")
    ],
    # Run & Bun: Defend Order functions like Protect (Move Changes.xlsx)
    "Defend Order": [
        EffectSpec(kind="protect", target="self")
    ],

    # --- Substitute and similar ---

    "Substitute": [
        EffectSpec(kind="substitute", target="self", amount=25)
    ],

    # --- Healing moves (simplified to 50% HP for now) ---

    "Recover": [
        EffectSpec(kind="heal", target="self", amount=50)
    ],
    "Roost": [
        EffectSpec(kind="heal", target="self", amount=50)
    ],
    "Soft-Boiled": [
        EffectSpec(kind="heal", target="self", amount=50)
    ],
    "Slack Off": [
        EffectSpec(kind="heal", target="self", amount=50)
    ],
    "Milk Drink": [
        EffectSpec(kind="heal", target="self", amount=50)
    ],
    "Synthesis": [
        EffectSpec(kind="heal", target="self", amount=50)
    ],
    "Morning Sun": [
        EffectSpec(kind="heal", target="self", amount=50)
    ],
    "Moonlight": [
        EffectSpec(kind="heal", target="self", amount=50)
    ],
    "Shore Up": [
        EffectSpec(kind="heal", target="self", amount=50)
    ],
    "Heal Order": [
        EffectSpec(kind="heal", target="self", amount=50)
    ],
    # Wish is delayed in-game; we approximate as instant heal on user
    "Wish": [
        EffectSpec(kind="heal", target="self", amount=50)
    ],
    # Rest: full heal + sleep, simplified
    "Rest": [
        EffectSpec(kind="heal", target="self", amount=100),
        EffectSpec(kind="status", target="self", status="slp"),
    ],

    # --- Phazing moves (force switch) ---

    "Roar": [
        EffectSpec(kind="phaze", target="foe")
    ],
    "Whirlwind": [
        EffectSpec(kind="phaze", target="foe")
    ],
    "Dragon Tail": [
        EffectSpec(kind="phaze", target="foe")
    ],
    "Circle Throw": [
        EffectSpec(kind="phaze", target="foe")
    ],
}
# move_effects.py (continued)

def _clamp_stage(stage: int) -> int:
    return max(-6, min(6, stage))


def _get_side_indices(actor_side_idx: int) -> Tuple[int, int]:
    actor = actor_side_idx
    foe = 1 - actor_side_idx
    return actor, foe


def _apply_stat_stage(
    pokemon: PokemonState,
    spec: EffectSpec,
    source: PokemonState,
) -> None:
    if spec.stat is None or spec.stages == 0:
        return
    pokemon.change_stat_stage(
        spec.stat,
        spec.stages,
        source=source,
        from_opponent=source is not pokemon,
    )


def _apply_status(
    state: BattleState,
    pokemon: PokemonState,
    spec: EffectSpec,
    target_side_idx: int,
) -> None:
    if spec.status is None:
        return
    field = state.field
    grounded = pokemon.is_grounded(field)

    if grounded and field.has_terrain("Misty"):
        return
    if grounded and spec.status == "slp" and field.has_terrain("Electric"):
        return

    pokemon.apply_status(spec.status)


def _apply_hazard(
    state: BattleState,
    actor_side_idx: int,
    spec: EffectSpec,
) -> None:
    actor_idx, foe_idx = _get_side_indices(actor_side_idx)
    if spec.target == "self_side":
        idx = actor_idx
    elif spec.target == "foe_side":
        idx = foe_idx
    else:
        idx = foe_idx

    hazard_name = spec.hazard or spec.condition
    if not hazard_name:
        return
    hazard_name = hazard_name.lower()

    if hazard_name in ("stealth_rock", "stealth_rocks"):
        state.field.stealth_rocks[idx] = True
    elif hazard_name == "spikes":
        state.field.spikes[idx] = min(3, state.field.spikes[idx] + 1)
    elif hazard_name == "toxic_spikes":
        state.field.toxic_spikes[idx] = min(2, state.field.toxic_spikes[idx] + 1)
    elif hazard_name == "sticky_web":
        state.field.sticky_web[idx] = True
    elif hazard_name == "steelsurge":
        state.field.steelsurge[idx] = True


def _apply_side_condition(
    state: BattleState,
    actor_side_idx: int,
    spec: EffectSpec,
    source: Optional[PokemonState] = None,
) -> None:
    actor_idx, foe_idx = _get_side_indices(actor_side_idx)
    if spec.target == "self_side":
        idx = actor_idx
    elif spec.target == "foe_side":
        idx = foe_idx
    else:
        idx = actor_idx

    duration = spec.duration or 0
    if spec.side_condition in ("reflect", "light_screen", "aurora_veil"):
        if source and source.item == "Light Clay":
            duration += 3

    if spec.side_condition == "reflect":
        state.field.reflect[idx] = True
        state.field.reflect_turns[idx] = duration
    elif spec.side_condition == "light_screen":
        state.field.light_screen[idx] = True
        state.field.light_screen_turns[idx] = duration
    elif spec.side_condition == "aurora_veil":
        state.field.aurora_veil[idx] = True
        state.field.aurora_veil_turns[idx] = duration
    elif spec.side_condition == "tailwind":
        state.field.tailwind[idx] = True
        state.field.tailwind_turns[idx] = duration or 4


def _apply_weather(
    state: BattleState,
    spec: EffectSpec,
) -> None:
    if spec.weather is None:
        return
    if spec.weather == "rain":
        state.field.weather = "Rain"
    elif spec.weather == "sun":
        state.field.weather = "Sun"
    elif spec.weather == "sand":
        state.field.weather = "Sand"
    elif spec.weather == "hail":
        state.field.weather = "Hail"
    

def _apply_heal(
    pokemon: PokemonState,
    spec: EffectSpec,
    weather: Optional[str],
) -> None:
    if spec.heal_fraction is None:
        return

    num, den = spec.heal_fraction
    frac = num / den

    if frac == 0.5 and weather in ("Sun", "Sand", "Hail", "Rain"):
        frac = 1 / 3

    amount = int(pokemon.max_hp * frac)
    pokemon.current_hp = min(pokemon.max_hp, pokemon.current_hp + max(1, amount))


def _apply_protect(
    state: BattleState,
    actor_side_idx: int,
) -> None:
    actor_idx, _ = _get_side_indices(actor_side_idx)
    state.field.protect[actor_idx] = True


def _apply_substitute(
    pokemon: PokemonState,
) -> None:
    if pokemon.substitute_hp is not None:
        return
    hp = pokemon.max_hp // 4
    if pokemon.current_hp <= hp:
        return
    pokemon.current_hp -= hp
    pokemon.substitute_hp = hp


def _apply_phaze(
    state: BattleState,
    actor_side_idx: int,
) -> None:
    foe_idx = 1 - actor_side_idx
    side = state.sides[foe_idx]
    if len(side.bench) == 0:
        return
    if side.active[0].current_hp <= 0:
        return
    new_idx = random.randrange(len(side.bench))
    side.active[0], side.bench[new_idx] = side.bench[new_idx], side.active[0]


def apply_effects_for_move(
    state: BattleState,
    attacker: PokemonState,
    defender: PokemonState,
    move_name: str,
    actor_side_idx: int,
    success: bool,
) -> None:
    if not success:
        return

    effects = MOVE_EFFECTS.get(move_name)
    if not effects:
        return

    actor_idx, foe_idx = _get_side_indices(actor_side_idx)

    for spec in effects:
        if spec.chance < 100:
            roll = random.randint(1, 100)
            if roll > spec.chance:
                continue

        if spec.kind == "stat_stage":
            if spec.target == "self":
                _apply_stat_stage(attacker, spec, attacker)
            elif spec.target == "foe":
                _apply_stat_stage(defender, spec, attacker)

        elif spec.kind == "status":
            if spec.target == "self":
                _apply_status(state, attacker, spec, actor_idx)
            elif spec.target == "foe":
                _apply_status(state, defender, spec, foe_idx)

        elif spec.kind == "hazard":
            _apply_hazard(state, actor_side_idx, spec)

        elif spec.kind == "side_condition":
            _apply_side_condition(state, actor_side_idx, spec, attacker)

        elif spec.kind == "weather":
            _apply_weather(state, spec)

        elif spec.kind == "heal":
            if spec.target == "self":
                _apply_heal(attacker, spec, state.field.weather)
            elif spec.target == "foe":
                _apply_heal(defender, spec, state.field.weather)

        elif spec.kind == "protect":
            _apply_protect(state, actor_side_idx)

        elif spec.kind == "substitute":
            if spec.target == "self":
                _apply_substitute(attacker)
            elif spec.target == "foe":
                _apply_substitute(defender)

        elif spec.kind == "phaze":
            _apply_phaze(state, actor_side_idx)