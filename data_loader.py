# data_loader.py
from pathlib import Path
from typing import Dict, List, Optional
import json
import pandas as pd
from trainer_data import TrainerDex, Trainer
# Define data structures for moves and Pokemon
class MoveData:
    __slots__ = (
        "name", "type", "category", "power", "accuracy", "pp",
        "effect_chance", "priority", "multihit", "target_def_halved",
        "has_secondary",
    )

    def __init__(
        self,
        name: str,
        type: str,
        category: str,
        power: int,
        accuracy: int,
        pp: int,
        effect_chance: int = 0,
        priority: int = 0,
        multihit: tuple = (1, 1),
        target_def_halved: bool = False,
        has_secondary: bool = False,
    ):
        self.name = name
        self.type = type
        self.category = category
        self.power = power
        self.accuracy = accuracy
        self.pp = pp
        self.effect_chance = effect_chance
        self.priority = priority
        self.multihit = multihit
        self.target_def_halved = target_def_halved
        self.has_secondary = has_secondary

class PokemonData:
    __slots__ = ("name", "types", "base_stats", "abilities")
    def __init__(self, name: str, types: List[str], base_stats: Dict[str,int], abilities: List[str]):
        self.name = name
        self.types = types              # list of types (1 or 2 types)
        self.base_stats = base_stats    # dict with keys "HP","Atk","Def","SpA","SpD","Spe"
        self.abilities = abilities      # list of possible abilities

MOVES_BASE_PATH = Path(__file__).with_name("moves_base.json")


def load_moves() -> Dict[str, MoveData]:
    moves: Dict[str, MoveData] = {}

    try:
        base_raw = json.loads(MOVES_BASE_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        base_raw = {}

    for name, m in base_raw.items():
        moves[name] = MoveData(
            name=name,
            type=m["type"],
            category=m["category"],
            power=int(m["power"]),
            accuracy=int(m["accuracy"]),
            pp=int(m["pp"]),
            has_secondary=bool(m.get("has_secondary", False)),
        )

    base_rows = []
    for name, m in base_raw.items():
        base_rows.append(
            {
                "Name": name,
                "Type": m["type"],
                "Category": m["category"],
                "Power": int(m["power"]),
                "Accuracy": f'{m["accuracy"]}',
                "PP": int(m["pp"]),
            }
        )
    base_moves_df = pd.DataFrame(base_rows)

    try:
        changes_df = pd.read_excel("Move Changes.xlsx")
    except FileNotFoundError:
        return moves

    for _, row in changes_df.iterrows():
        move_name = str(row["Move"]) if pd.notna(row["Move"]) else None
        move_name_2 = str(row["Move.1"]) if pd.notna(row["Move.1"]) else None

        if move_name and move_name != "None":
            if move_name not in moves:
                base_row_df = base_moves_df[base_moves_df["Name"] == move_name]
                base = base_row_df.iloc[0] if not base_row_df.empty else None

                if base is not None:
                    moves[move_name] = MoveData(
                        name=move_name,
                        type=base["Type"],
                        category=base["Category"],
                        power=int(base["Power"]),
                        accuracy=int(str(base["Accuracy"]).rstrip("%")),
                        pp=int(base["PP"]),
                    )
                else:
                    moves[move_name] = MoveData(
                        name=move_name,
                        type="Normal",
                        category="Physical",
                        power=0,
                        accuracy=100,
                        pp=0,
                    )

            if pd.notna(row["BP"]):
                new_bp = str(row["BP"]).split(">")[-1].strip()
                moves[move_name].power = int(new_bp)

            if pd.notna(row["Accuracy"]):
                new_acc = str(row["Accuracy"]).split(">")[-1].strip().rstrip("%")
                moves[move_name].accuracy = int(new_acc)

            if pd.notna(row["PP"]):
                new_pp = str(row["PP"]).split(">")[-1].strip()
                moves[move_name].pp = int(new_pp)

            if pd.notna(row["Type"]):
                new_type = str(row["Type"]).split(">")[-1].strip()
                moves[move_name].type = new_type

        if move_name_2 and move_name_2 != "None":
            change_desc = str(row["Change"])
            if "Halves target's defense" in change_desc:
                mname = move_name_2
                if mname not in moves:
                    moves[mname] = MoveData(
                        name=mname,
                        type="Normal",
                        category="Physical",
                        power=0,
                        accuracy=100,
                        pp=0,
                    )
                moves[mname].target_def_halved = True

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

_TRAINER_DEX: Optional[TrainerDex] = None
TRAINER_DATA_JSON_PATH = "trainer_data.json"


def get_trainer_dex(path: str = TRAINER_DATA_JSON_PATH) -> TrainerDex:
    global _TRAINER_DEX
    if _TRAINER_DEX is None:
        _TRAINER_DEX = TrainerDex.from_json(path)
    return _TRAINER_DEX


def get_trainer_by_id(trainer_id: str, path: str = TRAINER_DATA_JSON_PATH) -> Trainer:
    dex = get_trainer_dex(path)
    return dex.get(trainer_id)


def get_trainers_by_name(name: str, path: str = TRAINER_DATA_JSON_PATH):
    dex = get_trainer_dex(path)
    return dex.find_by_name(name)