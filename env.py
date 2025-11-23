# env.py
from typing import Any, Dict, Optional, Tuple
import random
import math

from data_loader import MoveData
from move_effects import apply_effects_for_move
from state import BattleState, SideState, PokemonState, FieldState
from damage import calculate_damage, type_effectiveness
from ai_policy import choose_move


CONFUSION_SELF_HIT_MOVE = MoveData(
    name="Confusion Self-Hit",
    type="Typeless",
    category="Physical",
    power=40,
    accuracy=100,
    pp=0,
)

NON_CONTACT_PHYSICAL_MOVES = {
    "earthquake",
    "magnitude",
    "bulldoze",
    "rock slide",
    "stone edge",
    "rock throw",
    "rock blast",
    "ancient power",
    "bonemerang",
    "bone club",
    "earth power",
    "self-destruct",
    "explosion",
    "gyro ball",
    "seed bomb",
    "signal beam",
    "shadow ball",
    "psyshock",
    "secret sword",
    "aura sphere",
}

PROTECT_MOVES = {
    "Protect",
    "Detect",
    "King's Shield",
    "Spiky Shield",
    "Baneful Bunker",
    "Obstruct",
    "Defend Order",
}

SUBSTITUTE_MOVES = {"Substitute"}

TAUNT_MOVES = {"Taunt"}
ENCORE_MOVES = {"Encore"}
DISABLE_MOVES = {"Disable"}
TORMENT_MOVES = {"Torment"}
INFATUATION_MOVES = {"Attract"}

CONFUSION_STATUS_MOVES = {
    "Confuse Ray",
    "Supersonic",
    "Swagger",
    "Flatter",
    "Sweet Kiss",
    "Teeter Dance",
}

RAMPAGE_MOVES = {
    "Outrage",
    "Thrash",
    "Petal Dance",
}

CHARGE_MOVES = {
    "Solar Beam",
    "Solar Blade",
    "Sky Attack",
    "Razor Wind",
    "Skull Bash",
    "Meteor Beam",
}

PARTIAL_TRAP_MOVES = {
    "Fire Spin",
    "Clamp",
    "Whirlpool",
    "Bind",
    "Wrap",
    "Sand Tomb",
    "Magma Storm",
    "Infestation",
    "Snap Trap",
    "Thunder Cage",
}

LEECH_SEED_MOVES = {"Leech Seed"}

FOCUS_PUNCH_NAME = "Focus Punch"

PINCH_BERRIES = {
    "Figy Berry",
    "Wiki Berry",
    "Mago Berry",
    "Aguav Berry",
    "Iapapa Berry",
}

ABSORB_ABILITY_TYPES = {
    "Lightning Rod": ("Electric", "SpA"),
    "Storm Drain": ("Water", "SpA"),
    "Sap Sipper": ("Grass", "Atk"),
}

PIVOT_MOVES = {
    "U-turn",
    "Volt Switch",
    "Flip Turn",
    "Parting Shot",
    "Baton Pass",
}

PHASING_MOVES = {
    "Roar",
    "Whirlwind",
    "Dragon Tail",
    "Circle Throw",
}

BATON_PASS_VOLATILES = {
    "aqua_ring",
    "ingrain",
    "focus_energy",
    "laser_focus",
    "magnet_rise",
    "power_trick",
    "substitute",
}

ALWAYS_CRIT_MOVES = {
    "Frost Breath",
    "Storm Throw",
}

CRIT_ITEM_SPECIES = {
    "Stick": {"Farfetch'd", "Farfetch’d", "Sirfetch'd", "Sirfetch’d"},
    "Leek": {"Farfetch'd", "Farfetch’d", "Sirfetch'd", "Sirfetch’d"},
    "Lucky Punch": {"Chansey"},
}


def stage_multiplier(stage: int) -> float:
    if stage > 6:
        stage = 6
    if stage < -6:
        stage = -6
    if stage >= 0:
        return (3 + stage) / 3.0
    else:
        return 3.0 / (3 - stage)


def get_effective_accuracy(
    attacker: PokemonState,
    defender: PokemonState,
    move: MoveData,
    field: FieldState,
    moved_second: bool = False,
) -> Optional[float]:
    if move.accuracy is None:
        return None

    if attacker.ability == "No Guard" or defender.ability == "No Guard":
        return None

    if move.name == "Blizzard" and field.has_weather("Hail", "Snow"):
        return None

    acc = float(move.accuracy)

    if attacker.ability == "Compound Eyes":
        acc *= 1.3
    elif attacker.ability == "Hustle" and move.category == "Physical":
        acc *= 0.8

    if attacker.ability == "Victory Star":
        acc *= 1.1

    if defender.ability in ("Sand Veil", "Snow Cloak") and field.has_weather("Sandstorm", "Hail", "Snow"):
        acc *= 0.8

    if defender.item in ("Bright Powder", "Lax Incense"):
        acc *= 0.9
    if attacker.item == "Wide Lens":
        acc *= 1.1
    elif attacker.item == "Zoom Lens" and moved_second:
        acc *= 1.2

    if field.is_gravity:
        acc *= 5.0 / 3.0

    stage = attacker.accuracy_stage - defender.evasion_stage
    stage = max(-6, min(6, stage))
    if stage > 0:
        acc *= (3 + stage) / 3
    elif stage < 0:
        acc *= 3 / (3 - stage)

    return max(1.0, min(100.0, acc))



CRIT_STAGE_CHANCES = {
    0: 1.0 / 16.0,
    1: 1.0 / 8.0,
    2: 1.0 / 2.0,
    3: 1.0,  # always crit
}

HIGH_CRIT_MOVES = {
    "Slash",
    "Night Slash",
    "Shadow Claw",
    "Cross Chop",
    "Poison Tail",
    "Leaf Blade",
    "Drill Run",
    "Stone Edge",
    "Psycho Cut",
    "Karate Chop",
    "Razor Leaf",
    "Crabhammer",
    "Blaze Kick",
    "Air Cutter",
    "Sky Attack",
    "Sniper Shot",
}


def get_crit_stage(attacker: PokemonState, move: MoveData) -> int:
    stage = 0

    if move.name in HIGH_CRIT_MOVES:
        stage += 1
    if attacker.ability == "Super Luck":
        stage += 1
    if attacker.volatiles.get("focus_energy", False):
        stage += 2
    if attacker.item in ("Scope Lens", "Razor Claw"):
        stage += 1

    species_boost = CRIT_ITEM_SPECIES.get(attacker.item)
    if species_boost and attacker.species in species_boost:
        stage += 2

    return min(stage, 3)


def roll_crit(
    attacker: PokemonState,
    defender: PokemonState,
    move: MoveData,
    field: FieldState,
    force_crit: bool = False,
) -> bool:
    if move.category not in ("Physical", "Special") or move.power <= 0:
        return False

    # Abilities that prevent crits (Gen 8 + RnB Magma Armor)
    if defender.ability in ("Battle Armor", "Shell Armor", "Magma Armor"):
        return False

    if force_crit or move.name in ALWAYS_CRIT_MOVES:
        return True

    if attacker.ability == "Merciless" and defender.status in ("psn", "tox"):
        return True

    stage = get_crit_stage(attacker, move)
    chance = CRIT_STAGE_CHANCES.get(stage, 1.0)

    if chance >= 1.0:
        return True

    return random.random() < chance


def compute_damage_for_hit(
    attacker: PokemonState,
    defender: PokemonState,
    move: MoveData,
    field: FieldState,
    attacker_side_idx: int,
    crit: bool,
) -> int:
    # Status / non-damaging moves
    if move.category == "Status" or move.power <= 0:
        return 0

    name = move.name.lower()
    ohko_names = {"sheer cold", "fissure", "guillotine", "horn drill"}
    fixed_names = {"seismic toss", "night shade", "dragon rage", "sonic boom", "super fang", "final gambit"}

    if name in fixed_names or name in ohko_names:
        dmg_min, dmg_max = calculate_damage(
            attacker,
            defender,
            move,
            field,
            attacker_side_idx=attacker_side_idx,
        )
        return dmg_min

    dmg_min, dmg_max = calculate_damage(
        attacker,
        defender,
        move,
        field,
        attacker_side_idx=attacker_side_idx,
    )

    if crit:
        orig_attacker_stages = attacker.stat_stages.copy()
        orig_defender_stages = defender.stat_stages.copy()
        orig_reflect = field.reflect[:]
        orig_ls = field.light_screen[:]
        orig_veil = field.aurora_veil[:]

        for stat in ("Atk", "SpA"):
            if attacker.stat_stages.get(stat, 0) < 0:
                attacker.stat_stages[stat] = 0

        for stat in ("Def", "SpD"):
            if defender.stat_stages.get(stat, 0) > 0:
                defender.stat_stages[stat] = 0

        defender_side_idx = 1 - attacker_side_idx
        field.reflect[defender_side_idx] = False
        field.light_screen[defender_side_idx] = False
        field.aurora_veil[defender_side_idx] = False

        dmg_min, dmg_max = calculate_damage(
            attacker,
            defender,
            move,
            field,
            attacker_side_idx=attacker_side_idx,
        )

        attacker.stat_stages = orig_attacker_stages
        defender.stat_stages = orig_defender_stages
        field.reflect = orig_reflect
        field.light_screen = orig_ls
        field.aurora_veil = orig_veil

        crit_mult = 1.5
        if attacker.ability == "Sniper":
            crit_mult *= 1.5

        dmg_min = int(math.floor(dmg_min * crit_mult))
        dmg_max = int(math.floor(dmg_max * crit_mult))

    if dmg_min > dmg_max:
        dmg_min, dmg_max = dmg_max, dmg_min

    if dmg_max <= 0:
        return 0

    dmg_min = max(1, dmg_min)

    return random.randint(dmg_min, dmg_max)


def get_effective_priority(
    attacker: PokemonState,
    move: MoveData,
    field: Optional[FieldState] = None,
) -> int:
    prio = move.priority
    if attacker.ability == "Gale Wings" and move.type == "Flying" and move.category != "Status":
        prio += 1
    return prio


class BattleEnv:
    def __init__(self, battle_state: BattleState):
        self.state = battle_state
        self.done = False
        self.winner: Optional[int] = None  # 0 = player, 1 = AI
        self._turn_skip_action = [False, False]
        self._turn_has_acted = [False, False]
        for side_idx, side in enumerate(self.state.sides):
            for mon in side.active:
                self._on_switch_in(side_idx, mon)   

    def _find_move_by_name(self, mon: PokemonState, move_name: Optional[str]) -> Optional[MoveData]:
        if not move_name:
            return None
        for mv in mon.moves:
            if mv.name == move_name:
                return mv
        return None

    def _boost_stat_stage(self, mon: PokemonState, stat: str, stages: int) -> None:
        mon.change_stat_stage(
            stat,
            stages,
            source=mon,
            from_opponent=False,
            ignore_blockers=True,
        )

    def _apply_move_absorption(self, target: PokemonState, move: MoveData) -> bool:
        ability = target.ability
        absorb = ABSORB_ABILITY_TYPES.get(ability)
        if not absorb or move.type != absorb[0]:
            return False
        self._boost_stat_stage(target, absorb[1], 1)
        return True

    def _maybe_trigger_focus_sash(self, target: PokemonState, damage: int) -> Optional[int]:
        if (
            target.item == "Focus Sash"
            and target.current_hp == target.max_hp
            and damage >= target.current_hp
        ):
            dealt = target.current_hp - 1
            target.current_hp = 1
            target.item = None
            self._check_hp_items(target)
            return dealt
        return None

    def _check_hp_items(self, mon: PokemonState) -> None:
        if mon.current_hp <= 0 or not mon.item:
            return
        if mon.item == "Sitrus Berry" and mon.current_hp <= mon.max_hp // 2:
            heal = max(1, mon.max_hp // 4)
            mon.current_hp = min(mon.max_hp, mon.current_hp + heal)
            mon.item = None
            return
        if mon.item in PINCH_BERRIES and mon.current_hp <= mon.max_hp // 4:
            heal = max(1, mon.max_hp // 2)
            mon.current_hp = min(mon.max_hp, mon.current_hp + heal)
            mon.item = None
            return

    def _force_switch(
        self,
        side_idx: int,
        *,
        random_choice: bool = False,
        skip_action_if_pending: bool = False,
    ) -> bool:
        side = self.state.sides[side_idx]
        bench = [m for m in side.party if m.current_hp > 0 and m not in side.active]
        if not bench:
            return False
        replacement = random.choice(bench) if random_choice else bench[0]
        side.active[0] = replacement
        self._on_switch_in(side_idx, replacement)
        if skip_action_if_pending and not self._turn_has_acted[side_idx]:
            self._turn_skip_action[side_idx] = True
        return True

    def _handle_defender_damage_items(
        self,
        defender: PokemonState,
        attacker: PokemonState,
        defender_side_idx: int,
        attacker_side_idx: int,
        effectiveness: float,
        hp_damage: int,
    ) -> None:
        if defender.current_hp <= 0 or hp_damage <= 0:
            return

        item = defender.item
        if not item:
            return

        if item == "Air Balloon":
            defender.item = None
            return

        if item == "Eject Button":
            defender.item = None
            self._force_switch(defender_side_idx, skip_action_if_pending=True)
            return

        if item == "Red Card" and attacker.current_hp > 0:
            defender.item = None
            self._force_switch(
                attacker_side_idx,
                random_choice=True,
                skip_action_if_pending=False,
            )
            return

        if item == "Weakness Policy" and effectiveness > 1.0:
            defender.item = None
            self._boost_stat_stage(defender, "Atk", 2)
            self._boost_stat_stage(defender, "SpA", 2)

    def _attempt_protect(self, mon: PokemonState) -> bool:
        streak = mon.volatiles.get("protect_streak", 0)
        success_chance = 1.0 / (2 ** streak) if streak > 0 else 1.0
        if random.random() > success_chance:
            mon.volatiles["protect_streak"] = streak
            return False
        mon.volatiles["protect_active"] = True
        mon.volatiles["protect_streak"] = streak + 1
        return True

    def _reset_protect_counter(self, mon: PokemonState, move_name: str) -> None:
        if move_name in PROTECT_MOVES:
            return
        mon.volatiles.pop("protect_streak", None)

    def _use_substitute(self, mon: PokemonState) -> bool:
        if mon.substitute_hp is not None:
            return False
        hp_cost = mon.max_hp // 4
        if hp_cost <= 0 or mon.current_hp <= hp_cost:
            return False
        mon.current_hp -= hp_cost
        mon.substitute_hp = hp_cost
        return True

    def _apply_confusion(self, target: PokemonState, min_turns: int = 2, max_turns: int = 5) -> None:
        target.volatiles["confusion_turns"] = random.randint(min_turns, max_turns)

    def _apply_taunt(self, target: PokemonState, duration: int = 3) -> None:
        target.volatiles["taunt_turns"] = duration

    def _apply_torment(self, target: PokemonState) -> None:
        target.volatiles["torment"] = True

    def _apply_encore(self, target: PokemonState, duration: int = 3) -> None:
        if not target.last_move_used:
            return
        target.volatiles["encore"] = {
            "move": target.last_move_used,
            "turns": duration,
        }

    def _apply_disable(self, target: PokemonState, duration: int = 4) -> None:
        if not target.last_move_used:
            return
        target.volatiles["disable"] = {
            "move": target.last_move_used,
            "turns": duration,
        }

    def _apply_infatuation(self, target: PokemonState, source_idx: int) -> None:
        target.volatiles["infatuated_with"] = source_idx

    def _apply_leech_seed(self, target: PokemonState, source_idx: int) -> None:
        if "Grass" in target.types:
            return
        target.volatiles["leech_seed"] = source_idx

    def _handle_custom_status_move(
        self,
        attacker: PokemonState,
        defender: PokemonState,
        move: MoveData,
        actor_idx: int,
        target_idx: int,
        move_landed: bool,
    ) -> bool:
        name = move.name

        if name in PROTECT_MOVES:
            self._attempt_protect(attacker)
            return True

        if name == "Focus Energy":
            attacker.volatiles["focus_energy"] = True
            return True

        if name == "Laser Focus":
            attacker.volatiles["laser_focus"] = True
            return True

        if name in SUBSTITUTE_MOVES:
            self._use_substitute(attacker)
            return True

        if not move_landed and name not in PROTECT_MOVES:
            return False

        if name in TAUNT_MOVES:
            if defender.substitute_hp is None and not defender.volatiles.get("protect_active"):
                self._apply_taunt(defender)
            return True

        if name in ENCORE_MOVES:
            if defender.substitute_hp is None and not defender.volatiles.get("protect_active"):
                self._apply_encore(defender)
            return True

        if name in DISABLE_MOVES:
            if defender.substitute_hp is None and not defender.volatiles.get("protect_active"):
                self._apply_disable(defender)
            return True

        if name in TORMENT_MOVES:
            if defender.substitute_hp is None and not defender.volatiles.get("protect_active"):
                self._apply_torment(defender)
            return True

        if name in INFATUATION_MOVES:
            if defender.substitute_hp is None and not defender.volatiles.get("protect_active"):
                self._apply_infatuation(defender, actor_idx)
            return True

        if name in CONFUSION_STATUS_MOVES:
            if defender.substitute_hp is None and not defender.volatiles.get("protect_active"):
                self._apply_confusion(defender)
            if name == "Swagger":
                defender.change_stat_stage("Atk", 2, source=attacker, from_opponent=True)
            elif name == "Flatter":
                defender.change_stat_stage("SpA", 1, source=attacker, from_opponent=True)
            return True

        if name in LEECH_SEED_MOVES:
            if defender.substitute_hp is None and not defender.volatiles.get("protect_active"):
                self._apply_leech_seed(defender, actor_idx)
            return True

        return False

    def _can_skip_charge(self, move: MoveData) -> bool:
        if move.name in ("Solar Beam", "Solar Blade"):
            return self.state.field.has_weather("Sun")
        return False

    def _resolve_move_choice(
        self,
        attacker: PokemonState,
        requested_move: MoveData,
    ) -> Tuple[MoveData, bool]:
        resolved = requested_move

        locked = attacker.volatiles.get("locked_move")
        if locked:
            forced = self._find_move_by_name(attacker, locked.get("move"))
            if forced:
                resolved = forced

        encore = attacker.volatiles.get("encore")
        if encore:
            forced = self._find_move_by_name(attacker, encore.get("move"))
            if forced:
                resolved = forced
            else:
                attacker.volatiles.pop("encore", None)

        charge = attacker.volatiles.get("charging_move")
        if charge:
            stored = charge.get("move")
            if stored:
                resolved = stored
            attacker.volatiles.pop("charging_move", None)
            return resolved, False

        if resolved and resolved.name in CHARGE_MOVES and not self._can_skip_charge(resolved):
            attacker.volatiles["charging_move"] = {"move": resolved}
            return resolved, True

        return resolved, False

    def _is_move_blocked(self, attacker: PokemonState, move: MoveData) -> bool:
        disable = attacker.volatiles.get("disable")
        if disable and disable.get("move") == move.name:
            return True

        taunt_turns = attacker.volatiles.get("taunt_turns", 0)
        if taunt_turns and move.category == "Status":
            return True

        if attacker.volatiles.get("torment") and attacker.last_move_used == move.name:
            return True

        return False

    def _apply_partial_trap(self, target: PokemonState, source_idx: int) -> None:
        duration = 4 + random.randint(0, 1)
        target.volatiles["partial_trap"] = {
            "turns": duration,
            "source": source_idx,
        }

    def _start_lock_in(self, attacker: PokemonState, move: MoveData) -> None:
        locked = attacker.volatiles.get("locked_move")
        if locked and locked.get("move") == move.name:
            turns = locked.get("turns", 0) - 1
            if turns <= 0:
                attacker.volatiles.pop("locked_move", None)
                if locked.get("confuse", False):
                    self._apply_confusion(attacker)
            else:
                locked["turns"] = turns
            return

        duration = random.randint(2, 3)
        if duration <= 1:
            return
        attacker.volatiles["locked_move"] = {
            "move": move.name,
            "turns": duration - 1,
            "confuse": True,
        }

    def _is_contact_move(self, move: MoveData) -> bool:
        if move.category != "Physical" or move.power <= 0:
            return False
        return move.name.lower() not in NON_CONTACT_PHYSICAL_MOVES

    def _active_index(self, mon: PokemonState) -> Optional[int]:
        for idx, side in enumerate(self.state.sides):
            if mon in side.active:
                return idx
        return None

    def _handle_faint(self, side_idx: Optional[int]) -> None:
        if side_idx is None or self.done:
            return
        side = self.state.sides[side_idx]
        mon = side.active[0]
        if mon.current_hp > 0:
            return
        if side_idx == 0:
            self.done = True
            self.winner = 1
            return

        alive = [m for m in side.party if m.current_hp > 0 and m not in side.active]
        if alive:
            swapped = self._force_switch(side_idx, skip_action_if_pending=True)
            if not swapped:
                self.done = True
                self.winner = 0
        else:
            self.done = True
            self.winner = 0

    def _deal_damage(self, target: PokemonState, amount: int) -> int:
        if amount <= 0 or target.current_hp <= 0:
            return 0
        if target.volatiles.get("focus_punch_pending"):
            target.volatiles["focus_punch_failed"] = True
        target.current_hp = max(0, target.current_hp - amount)
        self._check_hp_items(target)
        if target.current_hp == 0:
            self._handle_faint(self._active_index(target))
        return amount

    def _apply_confusion_self_hit(self, attacker: PokemonState) -> None:
        dmg_min, dmg_max = calculate_damage(attacker, attacker, CONFUSION_SELF_HIT_MOVE, self.state.field)
        if dmg_max <= 0:
            return
        low = max(1, min(dmg_min, dmg_max))
        high = max(1, max(dmg_min, dmg_max))
        damage = random.randint(low, high)
        self._deal_damage(attacker, damage)

    def _process_confusion(self, attacker: PokemonState) -> bool:
        turns = attacker.volatiles.get("confusion_turns")
        if not turns:
            return True
        turns -= 1
        if turns <= 0:
            attacker.volatiles.pop("confusion_turns", None)
        else:
            attacker.volatiles["confusion_turns"] = turns
        if random.random() < (1 / 3):
            self._apply_confusion_self_hit(attacker)
            return False
        return True

    def _process_infatuation(self, attacker: PokemonState, target: PokemonState) -> bool:
        source_idx = attacker.volatiles.get("infatuated_with")
        if source_idx is None:
            return True
        target_idx = self._active_index(target)
        if target_idx != source_idx:
            attacker.volatiles.pop("infatuated_with", None)
            return True
        if random.random() < 0.5:
            return False
        return True

    def _process_primary_status(self, attacker: PokemonState, move: MoveData) -> bool:
        if attacker.status == "slp":
            turns = attacker.volatiles.get("sleep_turns")
            if turns is None:
                turns = random.randint(1, 3)
                attacker.volatiles["sleep_turns"] = turns
            if turns > 0:
                turns -= 1
                attacker.volatiles["sleep_turns"] = turns
                if turns == 0:
                    attacker.cure_status()
                return False

        if attacker.status == "frz":
            thawing_moves = {
                "Flame Wheel",
                "Sacred Fire",
                "Flare Blitz",
                "Steam Eruption",
                "Scald",
                "Fusion Flare",
            }
            forced_thaw = move.type == "Fire" or move.name in thawing_moves
            if forced_thaw or random.random() < 0.2:
                attacker.cure_status()
            else:
                return False

        if attacker.status == "par" and random.random() < 0.25:
            return False

        if attacker.volatiles.pop("flinch", False):
            return False

        return True

    def _can_act_this_turn(self, attacker: PokemonState, target: PokemonState, move: MoveData) -> bool:
        if not self._process_primary_status(attacker, move):
            return False
        if not self._process_infatuation(attacker, target):
            return False
        if not self._process_confusion(attacker):
            return False
        return True

    def _handle_post_damage_effects(
        self,
        attacker: PokemonState,
        defender: PokemonState,
        move: MoveData,
        total_damage: int,
    ) -> None:
        if total_damage <= 0 or self.done:
            return
        self._handle_contact_recoil(attacker, defender, move)
        if self.done:
            return
        self._handle_attacker_items(attacker, total_damage)

    def _handle_contact_recoil(
        self,
        attacker: PokemonState,
        defender: PokemonState,
        move: MoveData,
    ) -> None:
        if attacker.current_hp <= 0 or not self._is_contact_move(move):
            return

        magic_guard = attacker.ability == "Magic Guard"

        if defender.item == "Rocky Helmet" and not magic_guard:
            dmg = max(1, attacker.max_hp // 6)
            self._deal_damage(attacker, dmg)
            if self.done or attacker.current_hp <= 0:
                return

        if defender.ability in ("Rough Skin", "Iron Barbs") and not magic_guard:
            dmg = max(1, attacker.max_hp // 8)
            self._deal_damage(attacker, dmg)

    def _handle_attacker_items(self, attacker: PokemonState, total_damage: int) -> None:
        if attacker.current_hp <= 0:
            return

        if attacker.item == "Life Orb" and attacker.ability != "Magic Guard":
            recoil = max(1, attacker.max_hp // 10)
            self._deal_damage(attacker, recoil)
            if self.done or attacker.current_hp <= 0:
                return

        if attacker.item == "Shell Bell":
            heal = max(1, total_damage // 8)
            attacker.current_hp = min(attacker.max_hp, attacker.current_hp + heal)

    def _handle_eject_pack_trigger(self, side_idx: int, force_skip: Optional[bool] = None) -> None:
        mon = self.state.sides[side_idx].active[0]
        if mon.current_hp <= 0:
            mon.volatiles.pop("eject_pack_trigger", None)
            return
        if not mon.volatiles.pop("eject_pack_trigger", False):
            return
        if mon.item != "Eject Pack":
            return
        mon.item = None
        if force_skip is None:
            skip = not self._turn_has_acted[side_idx]
        else:
            skip = force_skip
        self._force_switch(side_idx, skip_action_if_pending=skip)

    def _handle_pivoting_move(self, actor_idx: int, move: MoveData, move_landed: bool) -> None:
        if move.name not in PIVOT_MOVES or not move_landed:
            return
        mon = self.state.sides[actor_idx].active[0]
        if mon.current_hp <= 0:
            return
        baton_pass = move.name == "Baton Pass"
        transfer_payload: Optional[Dict[str, Any]] = None
        if baton_pass:
            transfer_payload = {
                "stat_stages": mon.stat_stages.copy(),
                "accuracy": mon.accuracy_stage,
                "evasion": mon.evasion_stage,
                "substitute": mon.substitute_hp,
                "volatiles": {
                    k: v for k, v in mon.volatiles.items() if k in BATON_PASS_VOLATILES
                },
            }
        switched = self._force_switch(actor_idx, skip_action_if_pending=False)
        if baton_pass and switched and transfer_payload:
            new_mon = self.state.sides[actor_idx].active[0]
            new_mon.stat_stages = transfer_payload["stat_stages"].copy()
            new_mon.accuracy_stage = transfer_payload["accuracy"]
            new_mon.evasion_stage = transfer_payload["evasion"]
            new_mon.substitute_hp = transfer_payload["substitute"]
            mon.substitute_hp = None
            for key, value in transfer_payload["volatiles"].items():
                new_mon.volatiles[key] = value
                mon.volatiles.pop(key, None)

    def _handle_phazing_move(self, target_idx: int, move: MoveData, move_landed: bool) -> None:
        if move.name not in PHASING_MOVES or not move_landed:
            return
        mon = self.state.sides[target_idx].active[0]
        if mon.current_hp <= 0:
            return
        self._force_switch(
            target_idx,
            random_choice=True,
            skip_action_if_pending=True,
        )

    def _apply_intimidate(self, side_idx: int) -> None:
        user = self.state.sides[side_idx].active[0]
        if user.current_hp <= 0 or user.ability != "Intimidate":
            return
        target_idx = 1 - side_idx
        target = self.state.sides[target_idx].active[0]
        if target.current_hp <= 0:
            return
        target.change_stat_stage(
            "Atk",
            -1,
            source=user,
            from_opponent=True,
            intimidate=True,
        )
        self._handle_eject_pack_trigger(target_idx, force_skip=False)
        self._handle_eject_pack_trigger(side_idx, force_skip=False)

    def _handle_special_move_followups(
        self,
        attacker: PokemonState,
        defender: PokemonState,
        move: MoveData,
        actor_idx: int,
        target_idx: int,
        move_landed: bool,
        total_damage: int,
    ) -> None:
        if self.done:
            return

        name = move.name

        if name == "Rapid Spin" and move_landed and total_damage > 0:
            self._remove_user_bindings(attacker)
            self._clear_hazards_from_side(actor_idx)
            attacker.change_stat_stage("Spe", 1, source=attacker, from_opponent=False, ignore_blockers=True)
            return

        if name == "Defog" and move_landed:
            self._clear_hazards_from_side(target_idx)
            self._clear_screens_from_side(target_idx)
            return

        if name == "Court Change" and move_landed:
            self._swap_side_conditions()
            return

        gmax_residual_map = {
            "G-Max Vine Lash": ("gmax_vinelash_turns", 4),
            "G-Max Wildfire": ("gmax_wildfire_turns", 4),
            "G-Max Cannonade": ("gmax_cannonade_turns", 4),
            "G-Max Volcalith": ("gmax_volcalith_turns", 4),
        }

        if name in gmax_residual_map and total_damage > 0:
            attr, turns = gmax_residual_map[name]
            getattr(self.state.field, attr)[target_idx] = turns

    def _remove_user_bindings(self, mon: PokemonState) -> None:
        mon.volatiles.pop("partial_trap", None)
        mon.volatiles.pop("leech_seed", None)
        mon.is_salt_cure = False

    def _clear_hazards_from_side(self, side_idx: int) -> None:
        field = self.state.field
        field.spikes[side_idx] = 0
        field.toxic_spikes[side_idx] = 0
        field.stealth_rocks[side_idx] = False
        field.sticky_web[side_idx] = False
        field.steelsurge[side_idx] = False

    def _clear_screens_from_side(self, side_idx: int) -> None:
        field = self.state.field
        field.reflect[side_idx] = False
        field.reflect_turns[side_idx] = 0
        field.light_screen[side_idx] = False
        field.light_screen_turns[side_idx] = 0
        field.aurora_veil[side_idx] = False
        field.aurora_veil_turns[side_idx] = 0

    def _swap_side_conditions(self) -> None:
        field = self.state.field
        for attr in (
            "spikes",
            "toxic_spikes",
            "stealth_rocks",
            "sticky_web",
            "steelsurge",
            "reflect",
            "light_screen",
            "aurora_veil",
            "tailwind",
            "gmax_vinelash_turns",
            "gmax_wildfire_turns",
            "gmax_cannonade_turns",
            "gmax_volcalith_turns",
            "tailwind_turns",
            "reflect_turns",
            "light_screen_turns",
            "aurora_veil_turns",
        ):
            arr = getattr(field, attr)
            arr[0], arr[1] = arr[1], arr[0]

    def _apply_entry_hazards(self, side_idx: int, mon: PokemonState) -> None:
        field = self.state.field
        hazard_blocked = mon.item == "Heavy-Duty Boots"
        grounded = mon.is_grounded(field)
        magic_guard = mon.ability == "Magic Guard"

        if field.stealth_rocks[side_idx] and not hazard_blocked:
            eff = type_effectiveness("Rock", mon.types, field)
            if eff > 0 and not magic_guard:
                dmg = max(1, math.floor(mon.max_hp * eff / 8))
                self._deal_damage(mon, dmg)
                if self.done:
                    return

        spikes_layers = field.spikes[side_idx]
        if spikes_layers and grounded and not hazard_blocked and not magic_guard:
            denom_map = {1: 8, 2: 6, 3: 4}
            denom = denom_map.get(spikes_layers, 8)
            dmg = max(1, mon.max_hp // denom)
            self._deal_damage(mon, dmg)
            if self.done:
                return

        if field.steelsurge[side_idx] and not hazard_blocked and not magic_guard:
            eff = type_effectiveness("Steel", mon.types, field)
            if eff > 0:
                dmg = max(1, math.floor(mon.max_hp * eff / 6))
                self._deal_damage(mon, dmg)
                if self.done:
                    return

        tox_layers = field.toxic_spikes[side_idx]
        if tox_layers and grounded and not hazard_blocked:
            if "Poison" in mon.types:
                field.toxic_spikes[side_idx] = 0
            elif "Steel" in mon.types or mon.status is not None:
                pass
            elif field.has_terrain("Misty") and grounded:
                pass
            else:
                status = "psn" if tox_layers == 1 else "tox"
                mon.apply_status(status)

        if field.sticky_web[side_idx] and grounded and not hazard_blocked:
            mon.change_stat_stage("Spe", -1, source=None, from_opponent=True)

    def _apply_side_residuals(self, side_idx: int) -> None:
        field = self.state.field
        mon = self.state.sides[side_idx].active[0]
        magic_guard = mon.ability == "Magic Guard" if mon.current_hp > 0 else False

        residuals = [
            ("gmax_vinelash_turns", "Grass"),
            ("gmax_wildfire_turns", "Fire"),
            ("gmax_cannonade_turns", "Water"),
            ("gmax_volcalith_turns", "Rock"),
        ]

        for attr, immune_type in residuals:
            turns = getattr(field, attr)[side_idx]
            if turns <= 0:
                continue

            if mon.current_hp > 0 and not magic_guard:
                if immune_type not in mon.types:
                    dmg = max(1, mon.max_hp // 6)
                    self._deal_damage(mon, dmg)
                    if self.done:
                        return

            getattr(field, attr)[side_idx] = max(0, turns - 1)

    def apply_turn(self, player_move: MoveData, player_target_idx: int = 1):
        ai_side = self.state.sides[1]
        player_side = self.state.sides[0]
        ai_active = ai_side.active[0]
        player_active = player_side.active[0]

        ai_move, ai_target = choose_move(
            ai_active,
            player_active,
            self.state,
            [m for m in ai_active.moves],
        )

        p_priority = get_effective_priority(player_active, player_move, self.state.field)
        ai_priority = get_effective_priority(ai_active, ai_move, self.state.field)

        if p_priority != ai_priority:
            first_actor = 0 if p_priority > ai_priority else 1
        else:
            p_speed = player_active.get_effective_speed(self.state.field, 0)
            ai_speed = ai_active.get_effective_speed(self.state.field, 1)
            if p_speed == ai_speed:
                first_actor = 0 if random.random() < 0.5 else 1
            else:
                first_actor = 0 if p_speed > ai_speed else 1

        prep_actions = [
            (0, player_active, player_move),
            (1, ai_active, ai_move),
        ]
        for _, attacker, move in prep_actions:
            if move.name == FOCUS_PUNCH_NAME:
                attacker.volatiles["focus_punch_pending"] = True
                attacker.volatiles.pop("focus_punch_failed", None)

        actions = [
            (0, player_move),
            (1, ai_move),
        ]
        if first_actor == 1:
            actions.reverse()

        self._turn_skip_action = [False, False]
        self._turn_has_acted = [False, False]

        for actor_idx, move in actions:
            if self.done:
                break
            if self._turn_skip_action[actor_idx]:
                continue

            attacker = self.state.sides[actor_idx].active[0]
            target_idx = 1 - actor_idx
            target = self.state.sides[target_idx].active[0]

            if attacker.current_hp <= 0 or target.current_hp <= 0:
                self._turn_has_acted[actor_idx] = True
                continue

            move, skip_action = self._resolve_move_choice(attacker, move)
            moved_second = actor_idx != first_actor

            if move.name != FOCUS_PUNCH_NAME:
                attacker.volatiles.pop("focus_punch_pending", None)
                attacker.volatiles.pop("focus_punch_failed", None)

            self._turn_has_acted[actor_idx] = True

            if skip_action:
                attacker.last_move_used = move.name
                self._reset_protect_counter(attacker, move.name)
                attacker.volatiles.pop("focus_punch_pending", None)
                continue

            if self._is_move_blocked(attacker, move):
                attacker.volatiles.pop("focus_punch_pending", None)
                attacker.last_move_used = move.name
                self._reset_protect_counter(attacker, move.name)
                continue

            if move.name == FOCUS_PUNCH_NAME:
                if attacker.volatiles.pop("focus_punch_failed", False):
                    attacker.volatiles.pop("focus_punch_pending", None)
                    attacker.last_move_used = move.name
                    self._reset_protect_counter(attacker, move.name)
                    continue

            if (
                move.priority > 0
                and target is not attacker
                and self.state.field.has_terrain("Psychic")
                and target.is_grounded(self.state.field)
            ):
                attacker.volatiles.pop("focus_punch_pending", None)
                attacker.last_move_used = move.name
                self._reset_protect_counter(attacker, move.name)
                continue

            if not self._can_act_this_turn(attacker, target, move):
                attacker.volatiles.pop("focus_punch_pending", None)
                attacker.last_move_used = move.name
                self._reset_protect_counter(attacker, move.name)
                continue

            move_lands = True

            effective_acc = get_effective_accuracy(
                attacker,
                target,
                move,
                self.state.field,
                moved_second=moved_second,
            )
            if effective_acc is not None:
                if random.randint(1, 100) > int(effective_acc):
                    move_lands = False

            force_crit = False

            if move.category == "Status":
                if (
                    move_lands
                    and target is not attacker
                    and self._apply_move_absorption(target, move)
                ):
                    attacker.last_move_used = move.name
                    attacker.volatiles.pop("focus_punch_pending", None)
                    self._reset_protect_counter(attacker, move.name)
                    continue

                status_user = attacker
                status_target = target
                status_actor_idx = actor_idx
                status_target_idx = target_idx

                if (
                    move_lands
                    and target is not attacker
                    and target.ability == "Magic Bounce"
                ):
                    status_user = target
                    status_target = attacker
                    status_actor_idx, status_target_idx = target_idx, actor_idx

                handled = self._handle_custom_status_move(
                    status_user,
                    status_target,
                    move,
                    status_actor_idx,
                    status_target_idx,
                    move_lands,
                )

                if not handled and move_lands:
                    if status_target is status_user or not status_target.volatiles.get("protect_active"):
                        if status_target is status_user or status_target.substitute_hp is None:
                            apply_effects_for_move(
                                self.state,
                                status_user,
                                status_target,
                                move.name,
                                actor_side_idx=status_actor_idx,
                                success=True,
                            )
                    self._handle_special_move_followups(
                        status_user,
                        status_target,
                        move,
                        status_actor_idx,
                        status_target_idx,
                        move_lands,
                        0,
                    )
                self._handle_eject_pack_trigger(status_actor_idx)
                self._handle_eject_pack_trigger(status_target_idx)
                self._handle_pivoting_move(status_actor_idx, move, move_lands)
                self._handle_phazing_move(status_target_idx, move, move_lands)
                attacker.last_move_used = move.name
                attacker.volatiles.pop("focus_punch_pending", None)
                self._reset_protect_counter(attacker, move.name)
                continue

            if target is not attacker and target.volatiles.get("protect_active"):
                attacker.last_move_used = move.name
                attacker.volatiles.pop("focus_punch_pending", None)
                self._reset_protect_counter(attacker, move.name)
                continue

            if (
                move_lands
                and target is not attacker
                and self._apply_move_absorption(target, move)
            ):
                attacker.last_move_used = move.name
                attacker.volatiles.pop("focus_punch_pending", None)
                self._reset_protect_counter(attacker, move.name)
                continue

            force_crit = attacker.volatiles.pop("laser_focus", False)
            effectiveness = type_effectiveness(move.type, target.types, self.state.field)

            hits = 1
            if move.multihit != (1, 1):
                min_hits, max_hits = move.multihit
                hits = random.randint(min_hits, max_hits)
                if attacker.ability == "Skill Link":
                    hits = max_hits

            total_effective_damage = 0
            hp_damage = 0
            if not move_lands:
                hits = 0

            for _ in range(hits):
                crit = roll_crit(attacker, target, move, self.state.field, force_crit=force_crit)
                damage = compute_damage_for_hit(
                    attacker,
                    target,
                    move,
                    self.state.field,
                    attacker_side_idx=actor_idx,
                    crit=crit,
                )
                if damage <= 0:
                    continue
                if target.substitute_hp is not None:
                    applied = min(damage, target.substitute_hp)
                    target.substitute_hp -= applied
                    if target.substitute_hp <= 0:
                        target.substitute_hp = None
                    total_effective_damage += applied
                    continue

                applied = self._deal_damage(target, damage)
                total_effective_damage += applied
                hp_damage += applied
                if target.current_hp <= 0 or self.done:
                    break

            if hp_damage > 0:
                apply_effects_for_move(
                    self.state,
                    attacker,
                    target,
                    move.name,
                    actor_side_idx=actor_idx,
                    success=True,
                )
                self._handle_post_damage_effects(attacker, target, move, total_effective_damage)
                self._handle_defender_damage_items(
                    target,
                    attacker,
                    target_idx,
                    actor_idx,
                    effectiveness,
                    hp_damage,
                )
                if move.name in PARTIAL_TRAP_MOVES and target.current_hp > 0:
                    self._apply_partial_trap(target, actor_idx)

            self._handle_special_move_followups(
                attacker,
                target,
                move,
                actor_idx,
                target_idx,
                move_lands,
                total_effective_damage,
            )

            self._handle_eject_pack_trigger(actor_idx)
            self._handle_eject_pack_trigger(target_idx)
            self._handle_pivoting_move(actor_idx, move, move_lands)
            self._handle_phazing_move(target_idx, move, move_lands)

            if move.name in RAMPAGE_MOVES:
                if hp_damage > 0 or attacker.volatiles.get("locked_move"):
                    self._start_lock_in(attacker, move)

            attacker.last_move_used = move.name
            attacker.volatiles.pop("focus_punch_pending", None)
            self._reset_protect_counter(attacker, move.name)

        if not self.done:
            self._apply_end_of_turn_effects()

    def step(self, action: MoveData) -> Dict[str, Any]:
        self.apply_turn(action)
        reward = 0.0
        if self.done:
            reward = 1.0 if self.winner == 0 else -1.0
        obs = {
            "player_hp": self.state.sides[0].active[0].current_hp,
            "opponent_hp": self.state.sides[1].active[0].current_hp,
            "weather": self.state.field.weather,
            "terrain": self.state.field.terrain,
            "player_status": self.state.sides[0].active[0].status,
            "opponent_status": self.state.sides[1].active[0].status,
        }
        return {
            "observation": obs,
            "reward": reward,
            "done": self.done,
            "winner": self.winner,
        }
    def _on_switch_in(self, side_idx: int, mon: PokemonState) -> None:
        field = self.state.field

        # Weather abilities: permanent weather
        if mon.ability == "Drizzle":
            field.weather = "Rain"
            field.weather_turns = 0
        elif mon.ability == "Drought":
            field.weather = "Sun"
            field.weather_turns = 0
        elif mon.ability == "Sand Stream":
            field.weather = "Sandstorm"
            field.weather_turns = 0
        elif mon.ability == "Snow Warning":
            field.weather = "Hail"
            field.weather_turns = 0

        # Terrain abilities: permanent terrain
        if mon.ability == "Electric Surge":
            field.terrain = "Electric"
            field.terrain_turns = 0
        elif mon.ability == "Grassy Surge":
            field.terrain = "Grassy"
            field.terrain_turns = 0
        elif mon.ability == "Psychic Surge":
            field.terrain = "Psychic"
            field.terrain_turns = 0
        elif mon.ability == "Misty Surge":
            field.terrain = "Misty"
            field.terrain_turns = 0

        for key in (
            "leech_seed",
            "partial_trap",
            "infatuated_with",
            "confusion_turns",
            "flinch",
            "encore",
            "disable",
            "taunt_turns",
            "torment",
            "locked_move",
            "charging_move",
            "protect_active",
            "protect_streak",
            "focus_punch_pending",
            "focus_punch_failed",
            "focus_energy",
            "laser_focus",
        ):
            mon.volatiles.pop(key, None)
        mon.substitute_hp = None
        mon.last_move_used = None
        mon.is_salt_cure = False
        if mon.status == "slp":
            mon.volatiles["sleep_turns"] = random.randint(1, 3)
        if mon.status == "tox":
            mon.toxic_counter = max(1, mon.toxic_counter or 1)

        if mon.current_hp > 0:
            self._apply_entry_hazards(side_idx, mon)
        if mon.current_hp > 0 and mon.ability == "Intimidate":
            self._apply_intimidate(side_idx)

    def _apply_end_of_turn_effects(self) -> None:
        field = self.state.field
        for side in self.state.sides:
            mon = side.active[0]
            mon.volatiles.pop("protect_active", None)

        # Weather residual damage
        if field.weather in ("Sandstorm", "Hail", "Snow"):
            for side_idx, side in enumerate(self.state.sides):
                mon = side.active[0]
                if mon.current_hp <= 0:
                    continue

                if field.weather == "Sandstorm":
                    if "Rock" in mon.types or "Ground" in mon.types or "Steel" in mon.types:
                        continue
                else:  # Hail / Snow
                    if "Ice" in mon.types:
                        continue

                if mon.ability in ("Magic Guard", "Overcoat"):
                    continue
                if mon.item == "Safety Goggles":
                    continue

                dmg = max(1, mon.max_hp // 16)
                self._deal_damage(mon, dmg)
                if self.done:
                    return

        # Grassy Terrain healing
        if field.has_terrain("Grassy"):
            for side in self.state.sides:
                mon = side.active[0]
                if mon.current_hp <= 0:
                    continue
                if not mon.is_grounded(field):
                    continue
                heal = max(1, mon.max_hp // 16)
                mon.current_hp = min(mon.max_hp, mon.current_hp + heal)

        # Solar Power / Dry Skin weather HP effects
        for side_idx, side in enumerate(self.state.sides):
            mon = side.active[0]
            if mon.current_hp <= 0:
                continue

            if mon.ability == "Solar Power" and field.has_weather("Sun"):
                dmg = max(1, mon.max_hp // 8)
                self._deal_damage(mon, dmg)
            elif mon.ability == "Dry Skin":
                if field.has_weather("Rain"):
                    heal = max(1, mon.max_hp // 8)
                    mon.current_hp = min(mon.max_hp, mon.current_hp + heal)
                elif field.has_weather("Sun"):
                    dmg = max(1, mon.max_hp // 8)
                    self._deal_damage(mon, dmg)

            if self.done:
                return

        # Decrement weather / terrain durations (0 = permanent)
        self._apply_status_and_volatile_effects()
        if self.done:
            return

        self._apply_moody_boosts()
        if self.done:
            return

        self._tick_side_conditions()

        if field.weather_turns > 0:
            field.weather_turns -= 1
            if field.weather_turns == 0:
                field.weather = None

        if field.terrain_turns > 0:
            field.terrain_turns -= 1
            if field.terrain_turns == 0:
                field.terrain = None

        self.state.turn += 1

    def _tick_side_conditions(self) -> None:
        field = self.state.field
        pairs = [
            ("reflect", "reflect_turns"),
            ("light_screen", "light_screen_turns"),
            ("aurora_veil", "aurora_veil_turns"),
            ("tailwind", "tailwind_turns"),
        ]

        for bool_attr, turn_attr in pairs:
            active = getattr(field, bool_attr)
            turns = getattr(field, turn_attr)
            for idx in range(len(active)):
                if not active[idx]:
                    turns[idx] = 0
                    continue
                if turns[idx] <= 1:
                    active[idx] = False
                    turns[idx] = 0
                else:
                    turns[idx] -= 1

    def _apply_status_and_volatile_effects(self) -> None:
        for side_idx, side in enumerate(self.state.sides):
            mon = side.active[0]
            if mon.current_hp <= 0:
                continue
            self._apply_status_damage(mon, side_idx)
            if self.done:
                return
            self._apply_volatile_damage(mon, side_idx)
            if self.done:
                return
            self._apply_item_residuals(mon)
            if self.done:
                return
            self._apply_side_residuals(side_idx)
            if self.done:
                return
            self._tick_volatile_timers(mon)
            if self.done:
                return

    def _apply_moody_boosts(self) -> None:
        stats = ["Atk", "Def", "SpA", "SpD", "Spe", "Acc", "Eva"]
        for side_idx, side in enumerate(self.state.sides):
            mon = side.active[0]
            if mon.current_hp <= 0 or mon.ability != "Moody":
                continue

            up_candidates = [stat for stat in stats if mon.get_stage_value(stat) < 6]
            if not up_candidates:
                continue

            up_stat = random.choice(up_candidates)
            self._boost_stat_stage(mon, up_stat, 2)

            down_candidates = [
                stat for stat in stats if stat != up_stat and mon.get_stage_value(stat) > -6
            ]
            if down_candidates:
                down_stat = random.choice(down_candidates)
                self._boost_stat_stage(mon, down_stat, -1)

    def _apply_status_damage(self, mon: PokemonState, side_idx: int) -> None:
        if mon.current_hp <= 0:
            return

        if mon.status in ("psn", "tox") and mon.ability == "Poison Heal":
            heal = max(1, mon.max_hp // 8)
            mon.current_hp = min(mon.max_hp, mon.current_hp + heal)
            if mon.status == "tox":
                counter = mon.toxic_counter or 1
                mon.toxic_counter = min(15, counter + 1)
            return

        if mon.ability == "Magic Guard":
            return

        if mon.status == "brn":
            dmg = max(1, mon.max_hp // 16)
            if mon.ability == "Heatproof":
                dmg = max(1, dmg // 2)
            self._deal_damage(mon, dmg)
        elif mon.status == "psn":
            dmg = max(1, mon.max_hp // 8)
            self._deal_damage(mon, dmg)
        elif mon.status == "tox":
            counter = mon.toxic_counter or 1
            dmg = max(1, mon.max_hp * min(15, counter) // 16)
            self._deal_damage(mon, dmg)
            mon.toxic_counter = min(15, counter + 1)

    def _apply_volatile_damage(self, mon: PokemonState, side_idx: int) -> None:
        if mon.current_hp <= 0:
            return
        magic_guard = mon.ability == "Magic Guard"

        seed_owner = mon.volatiles.get("leech_seed")
        if seed_owner is not None:
            if "Grass" in mon.types:
                mon.volatiles.pop("leech_seed", None)
            elif not magic_guard and 0 <= seed_owner < len(self.state.sides):
                dmg = max(1, mon.max_hp // 8)
                healed = self._deal_damage(mon, dmg)
                if healed > 0 and not self.done:
                    source_mon = self.state.sides[seed_owner].active[0]
                    if source_mon.current_hp > 0:
                        source_mon.current_hp = min(source_mon.max_hp, source_mon.current_hp + healed)

        if mon.is_salt_cure and not magic_guard and mon.current_hp > 0:
            dmg = max(1, mon.max_hp // 8)
            if any(t in ("Water", "Steel") for t in mon.types):
                dmg = max(1, dmg * 2)
            self._deal_damage(mon, dmg)

        trap = mon.volatiles.get("partial_trap")
        if trap:
            if not magic_guard and mon.current_hp > 0:
                dmg = max(1, mon.max_hp // 8)
                self._deal_damage(mon, dmg)
            remaining = None
            if isinstance(trap, dict):
                remaining = trap.get("turns", 0) - 1
            elif isinstance(trap, int):
                remaining = trap - 1
            if remaining is not None:
                if remaining <= 0:
                    mon.volatiles.pop("partial_trap", None)
                else:
                    if isinstance(trap, dict):
                        trap["turns"] = remaining
                    else:
                        mon.volatiles["partial_trap"] = remaining

    def _tick_volatile_timers(self, mon: PokemonState) -> None:
        taunt = mon.volatiles.get("taunt_turns")
        if taunt:
            taunt -= 1
            if taunt <= 0:
                mon.volatiles.pop("taunt_turns", None)
            else:
                mon.volatiles["taunt_turns"] = taunt

        encore = mon.volatiles.get("encore")
        if encore:
            encore["turns"] = max(0, encore.get("turns", 0) - 1)
            if encore["turns"] <= 0:
                mon.volatiles.pop("encore", None)

        disable = mon.volatiles.get("disable")
        if disable:
            disable["turns"] = max(0, disable.get("turns", 0) - 1)
            if disable["turns"] <= 0:
                mon.volatiles.pop("disable", None)

    def _apply_item_residuals(self, mon: PokemonState) -> None:
        if mon.current_hp <= 0 or not mon.item:
            return

        if mon.item == "Leftovers":
            heal = max(1, mon.max_hp // 16)
            mon.current_hp = min(mon.max_hp, mon.current_hp + heal)
        elif mon.item == "Black Sludge":
            if "Poison" in mon.types:
                heal = max(1, mon.max_hp // 16)
                mon.current_hp = min(mon.max_hp, mon.current_hp + heal)
            elif mon.ability != "Magic Guard":
                dmg = max(1, mon.max_hp // 8)
                self._deal_damage(mon, dmg)