from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Literal
import json
import re

import pandas as pd

STAT_NAMES = ("HP", "Atk", "Def", "SpA", "SpD", "Spe")
BattleFormat = Literal["single", "double", "multi", "unknown"]


def canonical_trainer_name(raw: str) -> str:
    if raw is None:
        return ""
    s = re.sub(r"\s*\[.*?\]\s*", " ", str(raw))
    return " ".join(s.split())


def detect_battle_format(raw_name: str) -> BattleFormat:
    if not raw_name:
        return "single"
    lower = raw_name.lower()
    if "[double]" in lower or " double" in lower or " & " in raw_name:
        return "double"
    return "single"


def load_iv_overrides_from_setdex_js(
    path: str,
) -> Dict[Tuple[str, str], Dict[str, int]]:
    short_to_full = {
        "hp": "HP",
        "at": "Atk",
        "df": "Def",
        "sa": "SpA",
        "sd": "SpD",
        "sp": "Spe",
    }
    overrides: Dict[Tuple[str, str], Dict[str, int]] = {}

    text = open(path, "r", encoding="utf-8").read()

    pattern = re.compile(r'"(?P<species>[^"]+)":\{"(?P<trainer>[^"]+)":\{', re.DOTALL)

    for m in pattern.finditer(text):
        species = m.group("species")
        trainer_raw = m.group("trainer")
        trainer = canonical_trainer_name(trainer_raw)

        body_start = m.end() - 1
        depth = 0
        i = body_start
        while i < len(text):
            ch = text[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        if depth != 0:
            continue
        body = text[body_start : i + 1]

        m_ivs = re.search(r'"ivs"\s*:\s*\{([^}]*)\}', body)
        if not m_ivs:
            continue
        ivs_body = m_ivs.group(1)

        raw_pairs: Dict[str, int] = {}
        for chunk in ivs_body.split(","):
            chunk = chunk.strip()
            if not chunk or ":" not in chunk:
                continue
            key, val = chunk.split(":", 1)
            key = key.strip().strip('"')
            val = val.strip()
            if not val:
                continue
            try:
                raw_pairs[key] = int(val)
            except ValueError:
                continue

        if not raw_pairs:
            continue

        ivs_full: Dict[str, int] = {}
        for short, full in short_to_full.items():
            if short in raw_pairs:
                ivs_full[full] = raw_pairs[short]

        if ivs_full:
            overrides[(trainer, species)] = ivs_full

    return overrides


@dataclass
class TrainerPokemon:
    species: str
    level: int
    item: Optional[str]
    ability: Optional[str]
    nature: Optional[str]
    moves: List[str]
    ivs: Dict[str, int]


@dataclass
class Trainer:
    id: str
    name: str
    raw_name: str
    location: Optional[str]
    group: str
    battle_format: BattleFormat
    team: List[TrainerPokemon]


def _parse_trainer_block(
    df: pd.DataFrame,
    sheet_name: str,
    start_row: int,
    end_row: int,
    iv_overrides: Dict[Tuple[str, str], Dict[str, int]],
    pre_block_name: Optional[str] = None,
) -> Optional[Trainer]:
    key_col = df.columns[0]
    sub = df.iloc[start_row:end_row].copy().reset_index(drop=True)
    labels = sub[key_col]

    if pre_block_name is not None:
        raw_name = str(pre_block_name).strip()
    else:
        first_label = labels.iloc[0]
        if str(first_label) != "Name":
            return None
        raw_name_cell = sub.iloc[0, 1]
        if pd.isna(raw_name_cell):
            return None
        raw_name = str(raw_name_cell).strip()

    pokemon_rows = labels[labels == "Pokémon"].index.tolist()
    if not pokemon_rows:
        return None
    pok_idx = pokemon_rows[0]
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
    canon_name = canonical_trainer_name(raw_name)

    for col in team_cols:
        species_val = species_row[col]
        if isinstance(species_val, float) and pd.isna(species_val):
            continue
        species = str(species_val).strip()
        if not species:
            continue

        raw_level = sub.iloc[level_idx][col]
        if isinstance(raw_level, float) and pd.isna(raw_level):
            continue
        level = int(str(raw_level).strip())

        def clean_opt(row_idx: int) -> Optional[str]:
            v = sub.iloc[row_idx].get(col)
            if isinstance(v, float) and pd.isna(v):
                return None
            if v is None:
                return None
            s = str(v).strip()
            return s or None

        item = clean_opt(item_idx)
        ability = clean_opt(ability_idx)
        nature = clean_opt(nature_idx)

        moves: List[str] = []
        for _, row in moves_rows.iterrows():
            mv = row.get(col)
            if isinstance(mv, float) and pd.isna(mv):
                continue
            if mv is None:
                continue
            s = str(mv).strip()
            if s:
                moves.append(s)

        ivs = {stat: 31 for stat in STAT_NAMES}
        override = iv_overrides.get((canon_name, species))
        if override:
            ivs.update(override)

        team.append(
            TrainerPokemon(
                species=species,
                level=level,
                item=item,
                ability=ability,
                nature=nature,
                moves=moves,
                ivs=ivs,
            )
        )

    if not team:
        return None

    fmt = detect_battle_format(raw_name)

    if sheet_name == "Pokémon League":
        location = sheet_name
    else:
        location = str(df.columns[1])

    trainer_id = f"{canon_name}@{sheet_name}@{fmt}"

    return Trainer(
        id=trainer_id,
        name=canon_name,
        raw_name=raw_name,
        location=location,
        group=sheet_name,
        battle_format=fmt,
        team=team,
    )


def parse_trainer_sheet(
    df: pd.DataFrame,
    sheet_name: str,
    iv_overrides: Dict[Tuple[str, str], Dict[str, int]],
) -> List[Trainer]:
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
        t = _parse_trainer_block(
            df,
            sheet_name,
            0,
            pre_end,
            iv_overrides=iv_overrides,
            pre_block_name=pre_name,
        )
        if t is not None:
            trainers.append(t)

    name_rows = df.index[df[key_col] == "Name"].tolist()
    for i, start_row in enumerate(name_rows):
        end_row = name_rows[i + 1] if i + 1 < len(name_rows) else n_rows
        t = _parse_trainer_block(
            df,
            sheet_name,
            start_row,
            end_row,
            iv_overrides=iv_overrides,
        )
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
    def from_workbook(
        cls,
        workbook_path: str,
        setdex_js_path: Optional[str] = None,
    ) -> "TrainerDex":
        if setdex_js_path is not None:
            iv_overrides = load_iv_overrides_from_setdex_js(setdex_js_path)
        else:
            iv_overrides = {}

        xls = pd.ExcelFile(workbook_path)
        trainers: List[Trainer] = []
        for sheet in xls.sheet_names:
            if sheet in ("Dex", "Sprites"):
                continue
            df = xls.parse(sheet)
            trainers.extend(parse_trainer_sheet(df, sheet, iv_overrides))
        return cls(trainers)

    @classmethod
    def from_json(cls, path: str) -> "TrainerDex":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        trainers: List[Trainer] = []
        for t_data in data.get("trainers", []):
            team: List[TrainerPokemon] = []
            for p_data in t_data["team"]:
                team.append(
                    TrainerPokemon(
                        species=p_data["species"],
                        level=int(p_data["level"]),
                        item=p_data.get("item"),
                        ability=p_data.get("ability"),
                        nature=p_data.get("nature"),
                        moves=list(p_data.get("moves", [])),
                        ivs=dict(p_data.get("ivs", {})),
                    )
                )
            trainers.append(
                Trainer(
                    id=t_data["id"],
                    name=t_data["name"],
                    raw_name=t_data.get("raw_name", t_data["name"]),
                    location=t_data.get("location"),
                    group=t_data.get("group", ""),
                    battle_format=t_data.get("battle_format", "single"),
                    team=team,
                )
            )
        return cls(trainers)

    def to_dict(self) -> Dict[str, object]:
        trainers_data = []
        for t in self.all_trainers():
            trainers_data.append(
                {
                    "id": t.id,
                    "name": t.name,
                    "raw_name": t.raw_name,
                    "location": t.location,
                    "group": t.group,
                    "battle_format": t.battle_format,
                    "team": [
                        {
                            "species": p.species,
                            "level": p.level,
                            "item": p.item,
                            "ability": p.ability,
                            "nature": p.nature,
                            "moves": list(p.moves),
                            "ivs": dict(p.ivs),
                        }
                        for p in t.team
                    ],
                }
            )
        return {"trainers": trainers_data}

    def to_json(self, path: str) -> None:
        data = self.to_dict()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def all_trainers(self) -> List[Trainer]:
        return list(self.trainers_by_id.values())

    def get(self, trainer_id: str) -> Trainer:
        return self.trainers_by_id[trainer_id]

    def find_by_name(self, name: str) -> List[Trainer]:
        canon = canonical_trainer_name(name)
        return self.trainers_by_name.get(canon, [])


def build_trainer_json(
    workbook_path: str,
    setdex_js_path: Optional[str],
    out_path: str,
) -> None:
    dex = TrainerDex.from_workbook(workbook_path, setdex_js_path=setdex_js_path)
    dex.to_json(out_path)

build_trainer_json(
    "Trainer Battles.xlsx",
    "gen8.js",
    "trainer_data.json",
)