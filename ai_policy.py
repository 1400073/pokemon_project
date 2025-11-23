# ai_policy.py
import random
from typing import Tuple, List, Dict, Literal, Optional
from damage import calculate_damage
from state import BattleState, PokemonState, SideState, FieldState
from data_loader import MoveData
from damage import type_effectiveness, TYPE_CHART
# AI scoring constants (from Run & Bun AI documentation)
# Base scores for moves:
NON_DAMAGE_MOVE_BASE = 6  
ActionType = Literal["move", "switch"]


def _get_side_index(state: BattleState, mon: PokemonState) -> Optional[int]:
    for idx, side in enumerate(state.sides):
        if mon in side.active or mon in side.party:
            return idx
    return None

def score_move(attacker: PokemonState, defender: PokemonState, move: MoveData, state: BattleState) -> int:
    if move.category != "Status":
        eff = 1.0
        for t in defender.types:
            eff *= TYPE_CHART.get(move.type, {}).get(t, 1.0)
        if eff == 0:
            return -10
    else:
        if move.name in ["Thunder Wave", "Spore", "Will-O-Wisp"]:
            if defender.status is not None:
                return -10

    att_idx = _get_side_index(state, attacker)
    def_idx = _get_side_index(state, defender)

    min_dmg, max_dmg = calculate_damage(
        attacker,
        defender,
        move,
        state.field,
        attacker_side_idx=att_idx,
        defender_side_idx=def_idx,
    )
    will_ko = max_dmg >= defender.current_hp

    atk_spe = attacker.calc_stat("Spe")
    def_spe = defender.calc_stat("Spe")
    if move.priority != 0 or def_spe == atk_spe:
        goes_first = (move.priority > 0) or (move.priority == 0 and atk_spe >= def_spe)
    else:
        goes_first = atk_spe > def_spe

    if move.category == "Status":
        score = NON_DAMAGE_MOVE_BASE
    else:
        score = max_dmg * 100 // max(1, defender.current_hp)

    if will_ko:
        if goes_first:
            score += 12
        else:
            score += 9
        if attacker.ability in ["Moxie", "Beast Boost", "Chilling Neigh", "Grim Neigh"]:
            score += 1

    if move.name in ["Slash", "Night Slash", "Shadow Claw", "Cross Chop", "Poison Tail"] and not will_ko:
        eff = type_effectiveness(move.type, defender.types, state.field)
        if eff > 1 and random.random() < 0.5:
            score += 1

    if move.priority > 0:
        if attacker.current_hp < (defender.current_hp * 0.5) and atk_spe < def_spe:
            score += 11

    return score


def choose_move(ai_side: PokemonState, opp_side: PokemonState, state: BattleState, moves: List[MoveData]) -> Tuple[MoveData, PokemonState]:
    """Choose the best move and target (for singles) for the AI Pokémon."""
    best_score = -999
    best_move = moves[0]
    target = opp_side  # in singles, target is always the lone opponent
    # Calculate scores for each move
    move_scores = {}
    for move in moves:
        s = score_move(ai_side, opp_side, move, state)
        move_scores[move.name] = s
        if s > best_score:
            best_score = s
            best_move = move
    # Tie-breaking: if multiple moves have same score, choose one at random:contentReference[oaicite:128]{index=128}.
    top_moves = [m for m in moves if move_scores[m.name] == best_score]
    if len(top_moves) > 1:
        best_move = random.choice(top_moves)
    return best_move, target

def best_damage(attacker: PokemonState, defender: PokemonState, moves: List[MoveData], state: BattleState) -> Tuple[int, int]:
    best_min = 0
    best_max = 0
    if not moves:
        return 0, 0
    for mv in moves:
        if getattr(mv, "pp", 1) == 0:
            continue
        att_idx = _get_side_index(state, attacker)
        def_idx = _get_side_index(state, defender)
        mn, mx = calculate_damage(
            attacker,
            defender,
            mv,
            state.field,
            attacker_side_idx=att_idx,
            defender_side_idx=def_idx,
        )
        if mx > best_max:
            best_max = mx
            best_min = mn
    return best_min, best_max

def post_ko_switch_score(candidate: PokemonState, opp_mon: PokemonState, state: BattleState) -> int:
    cand_hp = max(1, candidate.current_hp)
    opp_hp = max(1, opp_mon.current_hp)

    _, cand_to_opp_max = best_damage(candidate, opp_mon, candidate.moves, state)
    _, opp_to_cand_max = best_damage(opp_mon, candidate, opp_mon.moves, state)

    cand_spe = candidate.calc_stat("Spe")
    opp_spe = opp_mon.calc_stat("Spe")
    cand_faster = cand_spe > opp_spe
    cand_slower = cand_spe < opp_spe

    cand_ohko = cand_to_opp_max >= opp_hp
    opp_ohko = opp_to_cand_max >= cand_hp

    cand_pct = cand_to_opp_max * 100 // opp_hp if opp_hp > 0 else 0
    opp_pct = opp_to_cand_max * 100 // cand_hp if cand_hp > 0 else 0

    score = 0

    # -1: slower and is OHKO’d
    if cand_slower and opp_ohko:
        score = -1
    else:
        # +5: faster and OHKO’s
        if cand_faster and cand_ohko:
            score = 5
        # +4: slower, OHKO’s, and is not OHKO’d
        elif cand_slower and cand_ohko and not opp_ohko:
            score = 4
        # +3 / +2: deals more % damage than it takes
        elif cand_faster and cand_pct > opp_pct:
            score = 3
        elif cand_slower and cand_pct > opp_pct:
            score = 2
        # +1: just faster
        elif cand_faster:
            score = 1
        else:
            score = 0

    # Ditto special case (+2)
    if candidate.species == "Ditto":
        score = max(score, 2)

    # Wynaut / Wobbuffet (+2 if not worse)
    if candidate.species in ["Wynaut", "Wobbuffet"] and not (cand_slower and opp_ohko):
        score = max(score, 2)

    return score

def choose_switch_in(side: SideState, opp_mon: PokemonState, state: BattleState, candidates: Optional[List[PokemonState]] = None) -> Optional[PokemonState]:
    if candidates is None:
        candidates = [m for m in side.party if m.current_hp > 0 and m not in side.active]
    if not candidates:
        return None
    best_score = -999
    best_list: List[PokemonState] = []
    for mon in candidates:
        s = post_ko_switch_score(mon, opp_mon, state)
        if s > best_score:
            best_score = s
            best_list = [mon]
        elif s == best_score:
            best_list.append(mon)
    if not best_list:
        return None
    return random.choice(best_list)


def should_consider_switch(ai_active: PokemonState, ai_side: SideState, opp_active: PokemonState, state: BattleState) -> Optional[PokemonState]:
    # Any bench mons available?
    if len([m for m in ai_side.party if m.current_hp > 0 and m not in ai_side.active]) == 0:
        return None

    # 1) All usable moves are "ineffective" (max score <= -5)
    best_move_score = -999
    for mv in ai_active.moves:
        s = score_move(ai_active, opp_active, mv, state)
        if s > best_move_score:
            best_move_score = s
    if best_move_score > -5:
        return None

    # 3) Active must be at least 50% HP
    if ai_active.current_hp < ai_active.calc_stat("HP") // 2:
        return None

    # 2) Find back mons that are either faster+not-OHKO'd or slower+not-2HKO'd.
    opp_speed = opp_active.calc_stat("Spe")
    found_faster = False  # bug: once one back mon is faster, all later mons are treated as faster
    viable_candidates: List[PokemonState] = []

    for mon in ai_side.party:
        if mon is ai_active or mon.current_hp <= 0:
            continue

        mon_speed = mon.calc_stat("Spe")
        raw_fast = mon_speed > opp_speed
        if raw_fast:
            found_faster = True
        considered_fast = raw_fast or found_faster

        _, opp_to_mon_max = best_damage(opp_active, mon, opp_active.moves, state)
        mon_hp = max(1, mon.current_hp)

        not_ohko = opp_to_mon_max < mon_hp
        not_two_hko = opp_to_mon_max * 2 < mon_hp

        cond2 = (considered_fast and not_ohko) or ((not considered_fast) and not_two_hko)
        if cond2:
            viable_candidates.append(mon)

    if not viable_candidates:
        return None

    # 50% chance to actually switch
    if random.random() >= 0.5:
        return None

    return choose_switch_in(ai_side, opp_active, state, viable_candidates)

def choose_ai_action(ai_side: SideState, opp_side: SideState, state: BattleState) -> Tuple[ActionType, Optional[MoveData], Optional[PokemonState]]:
    ai_active = ai_side.active[0]
    opp_active = opp_side.active[0]

    switch_target = None
    if state.field.game_type == "Singles":
        switch_target = should_consider_switch(ai_active, ai_side, opp_active, state)

    if switch_target is not None:
        return "switch", None, switch_target

    moves = ai_active.moves or []
    if not moves:
        return "move", None, opp_active

    best_move, target = choose_move(ai_active, opp_active, state, moves)
    return "move", best_move, target
