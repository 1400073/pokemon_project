# ai_policy.py
import random
from typing import Tuple, List
from damage import calculate_damage
from state import BattleState, PokemonState
from data_loader import MoveData
from damage import type_effectiveness, TYPE_CHART
# AI scoring constants (from Run & Bun AI documentation)
# Base scores for moves:
NON_DAMAGE_MOVE_BASE = 6  # default score for non-attacking moves:contentReference[oaicite:118]{index=118}:contentReference[oaicite:119]{index=119}
# (The AI doc notes non-attacks tie with highest damage move at +6 by default.)

def score_move(attacker: PokemonState, defender: PokemonState, move: MoveData, state: BattleState) -> int:
    """Calculate the AI score for a given move used by attacker on defender."""
    # If move would have no effect (e.g., status on an already afflicted target, or immune damage), score very low
    if move.category != "Status":
        # Check immunity or uselessness
        eff = 1.0
        for t in defender.types:
            eff *= TYPE_CHART.get(move.type, {}).get(t, 1.0)
        if eff == 0:  # move does no damage
            return -10  # very low score (ineffective)
    else:
        # If status move is redundant (e.g., trying to paralyze an already paralyzed target)
        if move.name in ["Thunder Wave","Spore","Will-O-Wisp"]:
            if defender.status is not None:
                return -10  # don't use ineffective status
    # Calculate damage range
    min_dmg, max_dmg = calculate_damage(attacker, defender, move, state.field)
    # If this move can KO the target from current HP:
    will_KO = max_dmg >= defender.current_hp
    # Determine if attacker moves first (consider priority and speed)
    attacker_speed = attacker.calc_stat("Spe")
    defender_speed = defender.calc_stat("Spe")
    goes_first = False
    if move.priority != 0 or defender_speed == attacker_speed:
        # simplified: if move has priority or speeds equal, just decide by priority
        goes_first = (move.priority > 0) or (move.priority == 0 and attacker_speed >= defender_speed)
    else:
        goes_first = attacker_speed > defender_speed
    # Base score for damage or status
    score = 0
    if move.category == "Status":
        score = NON_DAMAGE_MOVE_BASE
    else:
        # Damage move base score: +6 for highest-damage move (we will determine relative ranking outside this func).
        # We tentatively set base damage score proportional to % of target HP dealt.
        # Run & Bun AI actually picks the highest damage move and assigns +6 or +8, and others lower.
        # Here, we return a raw value (like expected damage or something) for comparison.
        score = max_dmg * 100 // (defender.current_hp or 1)  # percent of HP
        # We'll adjust later to the discrete scoring scheme.
    # Additional scoring rules from the AI doc:
    # If move is the highest damaging move, AI gives +6 (80% chance) or +8 (20%):contentReference[oaicite:120]{index=120}.
    # To implement this, we might need to compare this move's damage to others. 
    # We'll handle that in the choose_move function by finding the max damage.
    # If the move will KO:
    if will_KO:
        if goes_first:
            # Fast kill scenario: +6 on top of base (80% chance) or +8 (20%):contentReference[oaicite:121]{index=121}:contentReference[oaicite:122]{index=122}.
            score += 12  # use the average of +12 (since base highest +6 plus additional +6 = +12 total)
        else:
            # Slow kill: +3 on top of base in AI doc (~half of fast kill bonus):contentReference[oaicite:123]{index=123}.
            score += 9  # highest base +6 plus +3 = +9 total
        # Additional +1 if attacker has a "Moxie-like" ability (Moxie, Beast Boost, etc.):contentReference[oaicite:124]{index=124}
        if attacker.ability in ["Moxie","Beast Boost","Chilling Neigh","Grim Neigh"]:
            score += 1
    # If move has high crit rate and is super-effective: AI sometimes gives +1:contentReference[oaicite:125]{index=125}.
    if move.name in ["Slash","Night Slash","Shadow Claw","Cross Chop","Poison Tail"] and will_KO is False:
        # Only if super-effective:
        eff = type_effectiveness(move.type, defender.types, state.field)
        if eff > 1:
            score += 1 if random.random() < 0.5 else 0
    # Priority moves: if AI is in danger of being KOed and slower, it values priority highly:contentReference[oaicite:126]{index=126}.
    # e.g., if attacker would be KOed by opponent next and this move is priority:
    # Check simple condition: if attacker HP < potential damage from opponent and attacker is slower:
    # (In practice, need to simulate opponent's best move; for brevity assume if attacker HP% is low and slower)
    if move.priority > 0:
        # If attacker is about to die (e.g., below 20% HP) and slower:
        if attacker.current_hp < (defender.current_hp * 0.5) and attacker.calc_stat("Spe") < defender.calc_stat("Spe"):
            score += 11  # big boost to use priority to get a hit in:contentReference[oaicite:127]{index=127}
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
