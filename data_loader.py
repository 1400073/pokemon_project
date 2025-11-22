# data_loader.py
from typing import Dict, List
import pandas as pd

# Define data structures for moves and Pokemon
class MoveData:
    __slots__ = ("name", "type", "category", "power", "accuracy", "pp", 
                 "effect_chance", "priority", "multihit", "target_def_halved")
    def __init__(self, name: str, type: str, category: str, power: int, accuracy: int, pp: int,
                 effect_chance: int = 0, priority: int = 0, multihit: tuple = (1, 1), target_def_halved: bool = False):
        self.name = name
        self.type = type            # e.g. "Fire", "Water"
        self.category = category    # "Physical", "Special", or "Status"
        self.power = power          # base power (0 for status moves)
        self.accuracy = accuracy    # accuracy percentage or None if can't miss
        self.pp = pp
        self.effect_chance = effect_chance  # chance (percentage) of secondary effect
        self.priority = priority    # priority bracket (e.g. +1, -1)
        self.multihit = multihit    # tuple (min_hits, max_hits)
        self.target_def_halved = target_def_halved  # True for Explosion/Self-Destruct

class PokemonData:
    __slots__ = ("name", "types", "base_stats", "abilities")
    def __init__(self, name: str, types: List[str], base_stats: Dict[str,int], abilities: List[str]):
        self.name = name
        self.types = types              # list of types (1 or 2 types)
        self.base_stats = base_stats    # dict with keys "HP","Atk","Def","SpA","SpD","Spe"
        self.abilities = abilities      # list of possible abilities

# Load move data from Run & Bun data files
def load_moves() -> Dict[str, MoveData]:
    moves: Dict[str, MoveData] = {}
    # Load base move data (from a Moves list or CSV – not provided directly in user files)
    # Here we assume we have a CSV or JSON of all move data to start with.
    base_moves_df = pd.DataFrame()  # placeholder for base move data
    # If we had 'Moves.txt', we would parse it. For now, assume base_moves_df is populated.
    # Apply the Move Changes from Move Changes.xlsx:
    changes_df = pd.read_excel("Move Changes.xlsx")
    # The sheet has two sections; we separate numeric changes and effect changes.
    # Process numeric changes (power, accuracy, PP, type changes):
    for idx, row in changes_df.iterrows():
        move_name = str(row["Move"]) if pd.notna(row["Move"]) else None
        move_name_2 = str(row["Move.1"]) if pd.notna(row["Move.1"]) else None
        if move_name and move_name != "None":
            # numeric change entry
            if move_name not in moves:
                # initialize from base data if not already set
                # For simplicity, fill with base data or defaults
                base = base_moves_df[base_moves_df["Name"] == move_name].iloc[0] if not base_moves_df.empty else None
                moves[move_name] = MoveData(
                    name=move_name,
                    type = base["Type"] if base is not None else "Normal",
                    category = base["Category"] if base is not None else "Physical",
                    power = int(base["Power"]) if base is not None else 0,
                    accuracy = int(base["Accuracy"]) if base is not None else 100,
                    pp = int(base["PP"]) if base is not None else 0
                )
            # Apply any changes present
            if pd.notna(row["BP"]):
                # format like "90 > 95"
                new_bp = row["BP"].split(">")[-1].strip()
                moves[move_name].power = int(new_bp)
            if pd.notna(row["Accuracy"]):
                new_acc = row["Accuracy"].split(">")[-1].strip().rstrip("%")
                moves[move_name].accuracy = int(new_acc)
            if pd.notna(row["PP"]):
                new_pp = row["PP"].split(">")[-1].strip()
                moves[move_name].pp = int(new_pp)
            if pd.notna(row["Type"]):
                # e.g. "Normal > Fairy"
                new_type = row["Type"].split(">")[-1].strip()
                moves[move_name].type = new_type
        if move_name_2 and move_name_2 != "None":
            # effect change entry
            change_desc = str(row["Change"])
            # We look for known phrases:
            if "Halves target's defense" in change_desc:
                # Mark this move to halve target defense
                mname = move_name_2
                if mname not in moves:
                    # initialize if not exists in base
                    moves[mname] = MoveData(name=mname, type="Normal", category="Physical", 
                                             power=0, accuracy=100, pp=0)
                moves[mname].target_def_halved = True
            # Other effect changes (Covet/Thief no item steal, etc.) 
            # can be noted if needed, but they don't affect damage directly.
    return moves

# Load Pokémon data (base stats, types, abilities) from provided text file
def load_pokemon() -> Dict[str, PokemonData]:
    pokemon: Dict[str, PokemonData] = {}
    with open("Learnset, Evolution Methods and Abilities.txt") as f:
        lines = [line.strip() for line in f.readlines()]
    i = 0
    while i < len(lines):
        name = lines[i]
        if not name:
            i += 1
            continue
        # Each Pokemon block: name, level-up moves, then "Ability 1: X", etc.
        types = []  # Not given in this file; we'd get from a different source (e.g. a base stats file).
        # For demonstration, we might derive type from context or assume base game types.
        # Here we skip actual type extraction due to missing data.
        # Instead, we could have a premade dict of types per name for Run & Bun.
        base_stats = {}  # The file doesn't list base stats, assume available via another source or Pokedex.
        abilities = []
        # Find lines for abilities
        while i < len(lines) and not lines[i].startswith("Ability"):
            i += 1
        while i < len(lines) and lines[i].startswith("Ability"):
            # e.g. "Ability 1: Overgrow"
            parts = lines[i].split(":")
            if len(parts) == 2:
                ability_name = parts[1].strip()
                if ability_name and ability_name != "None":
                    abilities.append(ability_name)
            i += 1
        # Hidden Ability line
        if i < len(lines) and lines[i].startswith("Hidden Ability"):
            hidden_parts = lines[i].split(":")
            if len(hidden_parts) == 2:
                hid_ability = hidden_parts[1].strip()
                if hid_ability and hid_ability != "None":
                    abilities.append(hid_ability)
            i += 1
        pokemon[name] = PokemonData(name=name, types=types, base_stats=base_stats, abilities=abilities)
        # Skip evolution line if present
        while i < len(lines) and lines[i] != "" and not lines[i].endswith(")"):
            # skip lines until blank or next Pokemon
            i += 1
        # Now i is at blank line or next Pokemon
    return pokemon

# Load trainer teams (for AI or environment) from the Trainer Battles.xlsx
def load_trainers():
    # We assume Trainer Battles.xlsx contains trainer name, and their party with species, level, moves, etc.
    trainers = {}
    try:
        df = pd.read_excel("Trainer Battles.xlsx")
    except FileNotFoundError:
        return trainers
    for _, row in df.iterrows():
        tname = row["Trainer"]
        mon_name = row["Pokemon"]
        level = row["Level"]
        # Possibly columns for Move1, Move2, Move3, Move4, etc.
        moves = [row[col] for col in ["Move1","Move2","Move3","Move4"] if col in row and pd.notna(row[col])]
        if tname not in trainers:
            trainers[tname] = []
        trainers[tname].append((mon_name, level, moves))
    return trainers
