# Dynamic-Calc Copilot Guide

## Project Snapshot
- Focus: simplified Pokémon battle simulator that mirrors Run & Bun balance changes.
- Core modules: `state.py` defines Pokémon/field/battle dataclasses, `damage.py` implements damage math, `ai_policy.py` encodes move scoring, `env.py` runs turn resolution, `data_loader.py` sketches data ingestion.
- The project currently targets single battles; doubles scaffolding exists via arrays but is mostly unimplemented.

## Core Models
- `PokemonState` auto-fills `current_hp` to full using `calc_stat`; EVs are treated as zero and natures are applied via a small lookup.
- `PokemonState.moves` is not part of the dataclass—attach a list of `MoveData` instances manually after instantiation (see `test_battle.py`).
- Stat stages live in `stat_stages` with keys `Atk`..`Spe`; adjust via integer stage math before calling `calc_stat`.
- `FieldState` tracks weather/terrain plus simple screen and hazard flags; indices `[0]` = player, `[1]` = opponent.
- `BattleState` wraps two `SideState`s (`active` + `party`) and a shared `FieldState`; use `get_opponent(idx)` helper when extending AI logic.

## Damage Engine
- Always call `damage.calculate_damage(attacker, defender, move, field)` to stay aligned with terrain, weather, ability, and item handling.
- Type chart is intentionally partial; extend `TYPE_CHART` before relying on uncovered interactions.
- Burn halves physical damage unless the attacker has `Guts` or uses `Facade`; OHKO and fixed-damage moves short-circuit early.
- Terrain and weather adjustments use integer math (e.g. Rain boosts Water 150% via `* 3 // 2`), so preserve integer operations when tweaking formulas.
- Multi-hit resolution and accuracy checks live in `env.apply_turn`; damage calculation itself only returns a `(min,max)` tuple.

## AI Behaviour
- `ai_policy.score_move` relies on `TYPE_CHART`; ensure `ai_policy.TYPE_CHART = damage.TYPE_CHART` when customizing charts (see `test_battle.py`).
- Scoring is percent-of-HP based with Run & Bun bonuses for KO scenarios, priority, and certain abilities; replicate that structure when adding heuristics.
- `choose_move` expects each active Pokémon to expose a `moves` list of `MoveData` objects and returns `(move, target)`.

## Data & Assets
- `data_loader.load_moves()` expects `Move Changes.xlsx` plus a base move dataset; missing files currently create placeholder `pandas.DataFrame()` rows—supply real data before enabling automated imports.
- `load_pokemon()` parses "Learnset, Evolution Methods and Abilities.txt" but leaves types and base stats empty; fill these from an external Pokédex source or inject via preprocessing.
- `load_trainers()` consumes "Trainer Battles.xlsx" if present and produces dictionaries of parties for AI scripting.

## Running & Debugging
- Primary sanity script: `python test_battle.py` prints a five-turn Charizard vs. Venusaur scenario using deterministic `random.seed(0)`.
- To probe damage outputs directly, spin up an interactive REPL and instantiate `PokemonState` + `MoveData`, then call `calculate_damage` for expected ranges.
- When integrating with RL, use `BattleEnv.step(move)`; it returns a dict with `obs`, `reward`, and `done` keys and sets `env.winner` when the battle ends.

## Coding Patterns
- Stick to lowercase status codes (`"brn"`, `"par"`) and let `env.apply_turn` manage multi-hit loops, recoil, and drains.
- Extend abilities or field effects by editing the dedicated sections in `damage.calculate_damage` and `env.apply_turn`, keeping modifiers grouped (abilities, items, terrain) for clarity.
- Screens and aurora veil currently assume singles; doubles adjustments depend on defender type-count heuristics—update both physical and special branches together.
- Follow the integer math style (`math.floor`, `//`) to match in-game damage rounding; mixing floats can skew results.
- Random elements (move choice, speed ties, multihits) use `random`; seed explicitly in tests to stabilize expectations.
