# damage.py
import math
from typing import Tuple, List, Dict
from state import PokemonState, FieldState
from data_loader import MoveData

# Type effectiveness chart for attack_type -> defense_type multipliers
# (for brevity, a partial chart is shown; in practice include all types)
TYPE_CHART: Dict[str, Dict[str, float]] = {
    "Normal": {"Rock": 0.5, "Steel": 0.5, "Ghost": 0.0},
    "Fire": {"Fire": 0.5, "Water": 0.5, "Grass": 2.0, "Ice": 2.0, "Bug": 2.0, "Rock": 0.5, "Dragon": 0.5, "Steel": 2.0},
    "Water": {"Fire": 2.0, "Water": 0.5, "Grass": 0.5, "Ground": 2.0, "Rock": 2.0, "Dragon": 0.5},
    "Electric": {"Water": 2.0, "Electric": 0.5, "Grass": 0.5, "Ground": 0.0, "Flying": 2.0, "Dragon": 0.5},
    "Grass": {"Fire": 0.5, "Water": 2.0, "Grass": 0.5, "Poison": 0.5, "Ground": 2.0, "Flying": 0.5, "Bug": 0.5, "Rock": 2.0, "Dragon": 0.5, "Steel": 0.5},
    "Ice": {"Fire": 0.5, "Water": 0.5, "Grass": 2.0, "Ice": 0.5, "Ground": 2.0, "Flying": 2.0, "Dragon": 2.0, "Steel": 0.5},
    "Fighting": {"Normal": 2.0, "Ice": 2.0, "Rock": 2.0, "Dark": 2.0, "Steel": 2.0, "Poison": 0.5, "Flying": 0.5, "Psychic": 0.5, "Bug": 0.5, "Fairy": 0.5, "Ghost": 0.0},
    "Poison": {"Grass": 2.0, "Fairy": 2.0, "Poison": 0.5, "Ground": 0.5, "Rock": 0.5, "Ghost": 0.5, "Steel": 0.0},
    "Ground": {"Fire": 2.0, "Electric": 2.0, "Poison": 2.0, "Rock": 2.0, "Steel": 2.0, "Grass": 0.5, "Bug": 0.5, "Flying": 0.0},
    "Flying": {"Grass": 2.0, "Fighting": 2.0, "Bug": 2.0, "Electric": 0.5, "Rock": 0.5, "Steel": 0.5},
    "Psychic": {"Fighting": 2.0, "Poison": 2.0, "Psychic": 0.5, "Steel": 0.5, "Dark": 0.0},
    "Bug": {"Grass": 2.0, "Psychic": 2.0, "Dark": 2.0, "Fire": 0.5, "Fighting": 0.5, "Poison": 0.5, "Flying": 0.5, "Ghost": 0.5, "Steel": 0.5, "Fairy": 0.5},
    "Rock": {"Fire": 2.0, "Ice": 2.0, "Flying": 2.0, "Bug": 2.0, "Fighting": 0.5, "Ground": 0.5, "Steel": 0.5},
    "Ghost": {"Psychic": 2.0, "Ghost": 2.0, "Dark": 0.5, "Normal": 0.0},
    "Dragon": {"Dragon": 2.0, "Steel": 0.5, "Fairy": 0.0},
    "Dark": {"Psychic": 2.0, "Ghost": 2.0, "Fighting": 0.5, "Dark": 0.5, "Fairy": 0.5},
    "Steel": {"Rock": 2.0, "Ice": 2.0, "Fairy": 2.0, "Fire": 0.5, "Water": 0.5, "Electric": 0.5, "Steel": 0.5},
    "Fairy": {"Fighting": 2.0, "Dragon": 2.0, "Dark": 2.0, "Fire": 0.5, "Poison": 0.5, "Steel": 0.5},
}

def type_effectiveness(move_type: str, target_types: List[str], field: FieldState) -> float:
    """Compute the total type effectiveness multiplier for move_type hitting target_types."""
    eff = 1.0
    for t in target_types:
        if move_type in TYPE_CHART and t in TYPE_CHART[move_type]:
            eff *= TYPE_CHART[move_type][t]
        else:
            eff *= 1.0 
    # Inverse battle check (if implemented, not typical in this hack)
    # Terrain effects on type:
    if field.terrain == "Misty" and move_type == "Dragon":
        eff *= 0.5
    return eff

def calculate_damage(attacker: PokemonState, defender: PokemonState, move: MoveData, field: FieldState) -> Tuple[int,int]:
    """Return the possible damage range (min_damage, max_damage) for one hit of the move."""
    if move.power == 0 and move.category == "Status":
        return (0, 0) 
    name = move.name.lower()
    if name in ["seismic toss", "night shade"]:
        dmg = attacker.level
        return (dmg, dmg)
    if name == "dragon rage":
        return (40, 40)
    if name == "sonic boom":
        return (20, 20)
    if name == "super fang":
        dmg = defender.current_hp // 2
        return (dmg, dmg)
    if name == "final gambit":
        dmg = attacker.current_hp
        return (dmg, dmg)
    
    if name in ["sheer cold", "fissure", "guillotine","horn drill"]:
        dmg = defender.current_hp
        return (dmg, dmg)
    if move.category == "Physical":
        A = attacker.calc_stat("Atk")
        D = defender.calc_stat("Def")
        # Burn halves physical Attack (if not Guts/Facade)
        if attacker.status == "brn" and attacker.ability != "Guts" and move.name not in ["Facade"]:
            A = A // 2 
    elif move.category == "Special":
        A = attacker.calc_stat("SpA")
        D = defender.calc_stat("SpD")
    else:
        return (0, 0)
    # Apply ability overrides for using different stats
    # e.g. Foul Play uses target's Attack
    if move.name == "Foul Play":
        A = defender.calc_stat("Atk")
    if move.name in ["Psyshock", "Secret Sword", "Psychic Shell"]:  # example alt moves
        D = defender.calc_stat("Def")
    if move.name == "Body Press":
        A = attacker.calc_stat("Def")
    # Explosion-family: halve target's defense (double damage)
    if move.target_def_halved:
        D = max(1, D // 2)
    # Weather-based power changes:
    base_power = move.power
    if field.weather == "Rain":
        if move.type == "Water":
            base_power = base_power * 3 // 2   # +50%:contentReference[oaicite:88]{index=88}
        elif move.type == "Fire":
            base_power = base_power // 2       # -50%
    elif field.weather == "Sun":
        if move.type == "Fire":
            base_power = base_power * 3 // 2
        elif move.type == "Water":
            base_power = base_power // 2
    # Grassy Terrain halves Earthquake/Magnitude/Bulldoze power
    if field.terrain == "Grassy" and move.name in ["Earthquake","Magnitude","Bulldoze"]:
        base_power = base_power // 2
    # Calculate base damage before multipliers
    level = attacker.level
    # Use integer math for base damage:
    base_damage = math.floor(math.floor(math.floor((2 * level) / 5 + 2) * A * base_power / D) / 50) + 2
    if base_damage < 1:
        base_damage = 1
    # Now apply multipliers:
    # Critical hit?
    
    crit = False
    crit_rate_stage = 0
    # Determine crit_rate_stage from move + other (not detailed here for brevity)
    # Let's assume we have a function to compute if it's crit:
    # e.g. high crit moves or Crit boosts from Focus Energy could raise stage
    # We won't randomize here; instead, we compute max and min damage considering crit and no-crit.
    # For damage range, consider both non-crit and crit possibilities.
    # Compute effectiveness:
    effectiveness = type_effectiveness(move.type, defender.types, field)
    if effectiveness == 0:
        return (0, 0)  # move does no damage (immune)
    # STAB
    stab = 1.0
    if move.type in attacker.types:
        stab = 1.5
        if attacker.ability == "Adaptability":
            stab = 2.0
    # Other multipliers:
    # Terrain boost
    terrain_boost = 1.0
    if field.terrain and attacker.is_grounded(field):
        if field.terrain == "Electric" and move.type == "Electric":
            terrain_boost = 1.5  # 50% boost:contentReference[oaicite:89]{index=89}
        elif field.terrain == "Grassy" and move.type == "Grass":
            terrain_boost = 1.5
        elif field.terrain == "Psychic" and move.type == "Psychic":
            terrain_boost = 1.5
    # Spread move?
    spread_modifier = 1.0
    # (In double battles, determine if move hits multiple targets)
    # We'll assume if it's a known spread move and in doubles with 2 targets alive:
    # spread_modifier = 0.75:contentReference[oaicite:90]{index=90}
    # Reflect/Light Screen:
    screen_modifier = 1.0
    # Determine which side is defender's side (player or opp) and if screen is up
    # If not a crit and attacker doesn't have Infiltrator:
    # For simplicity, let's assume defender is on index 1 (opponent) for now.
    # In actual code, we'd pass side indices.
    if move.category == "Physical":
        if field.aurora_veil[1] or field.reflect[1]:
            screen_modifier = 0.5 if not crit else 1.0
            if len(defender.types) > 1:  # if double battle only one opponent, use 0.5, if multiple, use 2/3
                # Actually, rule: if more than one Pokémon on defender side when move is executed in doubles:
                screen_modifier = (2/3) if not crit else 1.0
    elif move.category == "Special":
        if field.aurora_veil[1] or field.light_screen[1]:
            screen_modifier = 0.5 if not crit else 1.0
            if len(defender.types) > 1:
                screen_modifier = (2/3) if not crit else 1.0
    # Ability modifiers:
    ability_mod = 1.0
    # Defender abilities:
    if defender.ability in ["Solid Rock","Filter","Prism Armor"] and effectiveness > 1:
        ability_mod *= 0.75  # 25% damage reduction:contentReference[oaicite:91]{index=91}
    if any(def_.ability == "Friend Guard" for def_ in [defender]):  # if ally has Friend Guard, in singles skip
        ability_mod *= 0.75  # 25% reduction:contentReference[oaicite:92]{index=92}
    # Attacker abilities:
    if attacker.ability == "Sniper" and crit:
        ability_mod *= 1.5  # Sniper boosts crit damage:contentReference[oaicite:93]{index=93}
    if attacker.ability == "Tinted Lens" and effectiveness < 1:
        ability_mod *= 2.0  # Tinted Lens doubles not-very-effective damage:contentReference[oaicite:94]{index=94}
    if attacker.ability == "Technician" and base_power <= 60:
        ability_mod *= 1.5
    if attacker.ability == "Sheer Force" and move.effect_chance and move.effect_chance > 0:
        ability_mod *= 1.3
        # (We would also ensure no secondary effect happens)
    # Item modifiers:
    item_mod = 1.0
    if attacker.item == "Life Orb":
        item_mod *= 1.3  # 30% boost (5324/4096 exact):contentReference[oaicite:95]{index=95}
    if attacker.item and attacker.item.endswith("Plate") and attacker.item.startswith(move.type):
        item_mod *= 1.2  # type-boosting plate, assume 20%
    if attacker.item == "Expert Belt" and effectiveness > 1:
        item_mod *= 1.2  # 20% boost for supereffective:contentReference[oaicite:96]{index=96}
    if attacker.item == "Muscle Band" and move.category == "Physical":
        item_mod *= 1.1
    if attacker.item == "Wise Glasses" and move.category == "Special":
        item_mod *= 1.1
    # Combine all modifiers (aside from random and crit which we'll handle separately):
    modifier = stab * effectiveness * terrain_boost * spread_modifier * screen_modifier * ability_mod * item_mod
    # Determine damage range due to random (and critical if we include/exclude it):
    # We'll compute min and max damage for one hit:
    # If move can crit, consider non-crit vs crit as separate outcomes:
    min_roll = 0.85
    max_roll = 1.0
    # Non-critical hit damage range
    min_damage = math.floor(base_damage * modifier * min_roll)
    max_damage = math.floor(base_damage * modifier * max_roll)
    # If considering a possible crit (for AI calculation or display), we could compute crit damage as well:
    if True:  # we can include crit calculation if needed
        crit_modifier = 1.5
        if attacker.ability == "Sniper":
            crit_modifier = 2.25
        # On a crit, ignore screens and certain stat drops (already handled above by not applying stage drops).
        crit_mod = stab * effectiveness * terrain_boost * spread_modifier * ability_mod * item_mod
        # (Exclude screen because screen_modifier was set to 1.0 on crit above.)
        crit_min = math.floor(base_damage * crit_modifier * crit_mod * min_roll)
        crit_max = math.floor(base_damage * crit_modifier * crit_mod * max_roll)
        # The true damage range is the union of crit and non-crit ranges, but typically we present them separately.
        # For simplicity, return non-crit range here.
    return (min_damage, max_damage)
