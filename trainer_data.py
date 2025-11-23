from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Optional, Literal

import pandas as pd

BattleFormat = Literal["single", "double", "multi", "unknown"]


@dataclass
class TrainerPokemon:
    species: str
    level: int
    item: Optional[str]
    ability: Optional[str]
    nature: Optional[str]
    moves: List[str]


@dataclass
class Trainer:
    id: str
    name: str
    location: Optional[str]
    group: str
    battle_format: BattleFormat
    team: List[TrainerPokemon]


def _parse_trainer_block(
    df: pd.DataFrame,
    sheet_name: str,
    start_row: int,
    end_row: int,
    pre_block_name: Optional[str] = None,
) -> Optional[Trainer]:
    key_col = df.columns[0]
    sub = df.iloc[start_row:end_row].copy().reset_index(drop=True)
    labels = sub[key_col]

    if pre_block_name is not None:
        name = pre_block_name
    else:
        first_label = labels.iloc[0]
        if str(first_label) != "Name":
            return None
        name_cell = sub.iloc[0, 1]
        if pd.isna(name_cell):
            return None
        name = str(name_cell).strip()

    pok_rows = labels[labels == "Pokémon"].index.tolist()
    if not pok_rows:
        return None
    pok_idx = pok_rows[0]
    if pok_idx + 1 >= len(sub):
        return None
    species_row = sub.iloc[pok_idx + 1]

    def find_row(label: str) -> Optional[int]:
        idxs = labels[labels == label].index.tolist()
        return idxs[0] if idxs else None

    level_idx = find_row("Level")
    item_idx = find_row("Held Item")
    ability_idx = find_row("Ability")
    nature_idx = find_row("Nature")
    moves_start_idx = find_row("Moves")

    if None in (level_idx, item_idx, ability_idx, nature_idx, moves_start_idx):
        return None

    moves_rows = sub.iloc[moves_start_idx:]
    team_cols: List[str] = []
    for col in df.columns[1:]:
        val = species_row.get(col)
        if isinstance(val, str) and val.strip():
            team_cols.append(col)

    team: List[TrainerPokemon] = []
    for col in team_cols:
        species = str(species_row[col]).strip()

        raw_level = sub.iloc[level_idx][col]
        if pd.isna(raw_level):
            continue
        level = int(str(raw_level).strip())

        raw_item = sub.iloc[item_idx].get(col)
        item: Optional[str] = None
        if isinstance(raw_item, str):
            s = raw_item.strip()
            if s and s.lower() not in ("none", "nan"):
                item = s

        raw_ability = sub.iloc[ability_idx].get(col)
        ability: Optional[str] = None
        if isinstance(raw_ability, str):
            s = raw_ability.strip()
            if s and s.lower() not in ("none", "nan"):
                ability = s

        raw_nature = sub.iloc[nature_idx].get(col)
        nature: Optional[str] = None
        if isinstance(raw_nature, str):
            s = raw_nature.strip()
            if s and s.lower() not in ("none", "nan"):
                nature = s

        moves: List[str] = []
        for _, row in moves_rows.iterrows():
            mv = row.get(col)
            if isinstance(mv, str):
                m = mv.strip()
                if m and m.lower() not in ("none", "nan"):
                    moves.append(m)

        team.append(
            TrainerPokemon(
                species=species,
                level=level,
                item=item,
                ability=ability,
                nature=nature,
                moves=moves,
            )
        )

    name_lower = name.lower()
    if "double" in name_lower:
        fmt: BattleFormat = "double"
    else:
        fmt = "single"

    clean_name = name.replace("[Double]", "").strip()

    if sheet_name == "Pokémon League":
        location = sheet_name
    else:
        location = str(df.columns[1])

    trainer_id = f"{clean_name}@{location}@{fmt}"

    return Trainer(
        id=trainer_id,
        name=clean_name,
        location=location,
        group=sheet_name,
        battle_format=fmt,
        team=team,
    )


def parse_trainer_sheet(df: pd.DataFrame, sheet_name: str) -> List[Trainer]:
    key_col = df.columns[0]
    trainers: List[Trainer] = []
    n_rows = len(df)

    if n_rows == 0:
        return trainers

    name_rows = df.index[df[key_col] == "Name"].tolist()
    first_label = df.iloc[0][key_col]

    if isinstance(first_label, str) and first_label == "Pokémon":
        pre_end = name_rows[0] if name_rows else n_rows
        pre_name = str(df.columns[1])
        t = _parse_trainer_block(df, sheet_name, 0, pre_end, pre_block_name=pre_name)
        if t is not None:
            trainers.append(t)

    name_rows = df.index[df[key_col] == "Name"].tolist()
    for i, start_row in enumerate(name_rows):
        end_row = name_rows[i + 1] if i + 1 < len(name_rows) else n_rows
        t = _parse_trainer_block(df, sheet_name, start_row, end_row)
        if t is not None:
            trainers.append(t)

    return trainers


class TrainerDex:
    def __init__(self, trainers: List[Trainer]):
        self.trainers_by_id: Dict[str, Trainer] = {t.id: t for t in trainers}
        self.trainers_by_name: Dict[str, List[Trainer]] = {}
        for t in trainers:
            self.trainers_by_name.setdefault(t.name, []).append(t)

    @classmethod
    def from_workbook(cls, path: str) -> "TrainerDex":
        xls = pd.ExcelFile(path)
        trainers: List[Trainer] = []
        for sheet in xls.sheet_names:
            if sheet in ("Dex", "Sprites"):
                continue
            df = xls.parse(sheet)
            trainers.extend(parse_trainer_sheet(df, sheet))
        return cls(trainers)

    @classmethod
    def from_csv(cls, path: str, sheet_name: str = "Trainer Battles") -> "TrainerDex":
        df = pd.read_csv(path)
        trainers = parse_trainer_sheet(df, sheet_name)
        return cls(trainers)

    def all_trainers(self) -> List[Trainer]:
        return list(self.trainers_by_id.values())

    def get(self, trainer_id: str) -> Trainer:
        return self.trainers_by_id[trainer_id]

    def find_by_name(self, name: str) -> List[Trainer]:
        return self.trainers_by_name.get(name, [])
