from __future__ import annotations

import time
from collections import defaultdict
from typing import Dict, List, Set, Tuple, Optional

import requests
from bs4 import BeautifulSoup

from species_index import RUNANDBUN_SPECIES, MOVE_TO_SPECIES

POKEDEX_BASE_URL = "https://pokemondb.net/pokedex/"
CRAWL_DELAY_SECONDS = 4.0


def slug_for_species(name: str, base_species: Optional[str]) -> str:
    canonical = base_species or name
    s = canonical.lower()
    replacements = {
        "♀": "-f",
        "♂": "-m",
        "é": "e",
        "’": "",
        "'": "",
        ".": "",
        ":": "",
    }
    for k, v in replacements.items():
        s = s.replace(k, v)
    s = s.replace(" ", "-")
    return s


def extract_moves_from_table(table) -> Set[str]:
    moves: Set[str] = set()
    thead = table.find("thead")
    if not thead:
        return moves
    header_cells = thead.find_all("th")
    headers = [h.get_text(strip=True) for h in header_cells]
    if "Move" not in headers:
        return moves
    move_idx = headers.index("Move")
    body = table.find("tbody")
    if not body:
        return moves
    for row in body.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) <= move_idx:
            continue
        move_cell = cells[move_idx]
        link = move_cell.find("a")
        if link:
            move_name = link.get_text(strip=True)
            if move_name:
                moves.add(move_name)
    return moves


def fetch_pokemondb_moves(slug: str) -> Set[str]:
    url = POKEDEX_BASE_URL + slug
    print(f"Fetching moves from {url} ...")
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
    except Exception as exc:
        print(f"  ! Failed to fetch {url}: {exc}")
        return set()

    soup = BeautifulSoup(resp.text, "html.parser")
    all_moves: Set[str] = set()
    for table in soup.find_all("table"):
        all_moves |= extract_moves_from_table(table)
    print(f"  -> Found {len(all_moves)} moves on PokémonDB for slug '{slug}'")
    return all_moves


def build_pokemon_to_moves_from_runandbun() -> Dict[str, Set[str]]:
    pokemon_to_moves: Dict[str, Set[str]] = defaultdict(set)
    for move, species_tuple in MOVE_TO_SPECIES.items():
        for species_name in species_tuple:
            pokemon_to_moves[species_name].add(move)
    return pokemon_to_moves


def build_pokemondb_cache() -> Dict[str, Set[str]]:
    cache: Dict[str, Set[str]] = {}
    seen_slugs: Set[str] = set()

    for name, info in RUNANDBUN_SPECIES.items():
        base_name = info.base_species or info.name
        slug = slug_for_species(info.name, info.base_species)
        if slug in seen_slugs:
            continue
        seen_slugs.add(slug)
        if base_name in cache:
            continue
        cache[base_name] = fetch_pokemondb_moves(slug)
        time.sleep(CRAWL_DELAY_SECONDS)

    return cache


def build_pokemon_to_moves() -> Dict[str, List[str]]:
    runandbun_moves = build_pokemon_to_moves_from_runandbun()
    pokemondb_cache = build_pokemondb_cache()

    pokemon_to_moves: Dict[str, List[str]] = {}

    for name, info in RUNANDBUN_SPECIES.items():
        base_name = info.base_species or info.name

        combined: Set[str] = set()

        combined |= runandbun_moves.get(name, set())

        combined |= set(info.moves)

        combined |= pokemondb_cache.get(base_name, set())

        pokemon_to_moves[name] = sorted(combined)

    return pokemon_to_moves


def write_python_module(
    pokemon_to_moves: Dict[str, List[str]],
    path: str = "moves_index.py",
) -> None:
    with open(path, "w", encoding="utf8") as f:
        f.write("from __future__ import annotations\n\n")
        f.write("from typing import Dict, Tuple\n\n")
        f.write("POKEMON_TO_MOVES: Dict[str, Tuple[str, ...]] = {\n")
        for name in sorted(pokemon_to_moves.keys()):
            moves = pokemon_to_moves[name]
            move_list_literal = ", ".join(repr(m) for m in moves)
            f.write(f"    {name!r}: ({move_list_literal}),\n")
        f.write("}\n")


def main() -> None:
    pokemon_to_moves = build_pokemon_to_moves()
    write_python_module(pokemon_to_moves)
    print("Wrote pokemon_to_moves_index.py")


if __name__ == "__main__":
    main()
