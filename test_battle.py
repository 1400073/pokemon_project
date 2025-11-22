# test_battle.py

import random

from state import PokemonState, FieldState, SideState, BattleState
from data_loader import MoveData
from env import BattleEnv
import ai_policy
from damage import TYPE_CHART

# Wire the type chart into ai_policy (it references TYPE_CHART as a module-global)
ai_policy.TYPE_CHART = TYPE_CHART

def make_test_battle() -> BattleEnv:
    # Simple base stats (roughly Gen 3/8)
    charizard_stats = {"HP": 78, "Atk": 84, "Def": 78, "SpA": 109, "SpD": 85, "Spe": 100}
    venusaur_stats  = {"HP": 80, "Atk": 82, "Def": 83, "SpA": 100, "SpD": 100, "Spe": 80}
    abomasnow_stats  = {"HP": 90, "Atk": 92, "Def": 75, "SpA": 92, "SpD": 85, "Spe": 60}
    aggron_stats  = {"HP": 70, "Atk": 110, "Def": 80, "SpA": 92, "SpD": 80, "Spe": 87}

    # Minimal typing
    charizard_types = ["Fire", "Flying"]
    venusaur_types  = ["Grass", "Poison"]

    # Moves
    flamethrower = MoveData(
        name="Flamethrower",
        type="Fire",
        category="Special",
        power=90,
        accuracy=100,
        pp=15,
    )
    air_slash = MoveData(
        name="Air Slash",
        type="Flying",
        category="Special",
        power=75,
        accuracy=95,
        pp=15,
    )
    giga_drain = MoveData(
        name="Giga Drain",
        type="Grass",
        category="Special",
        power=75,
        accuracy=100,
        pp=10,
    )
    stupid_move = MoveData(
        name="Stupid Move",
        type="Normal",
        category="Physical",
        power=40,
        accuracy=100,
        pp=30,
    )
    op_move = MoveData(
        name="Bad Move",
        type="Grass",
        category="Physical",
        power=100,
        accuracy=100,
        pp=30,
    )
    sludge_bomb = MoveData(
        name="Sludge Bomb",
        type="Poison",
        category="Special",
        power=90,
        accuracy=100,
        pp=10,
    )

    # Pokémon
    charizard = PokemonState(
        species="Charizard",
        level=50,
        base_stats=charizard_stats,
        types=charizard_types,
        ability="Blaze",
        item=None,
        nature="Modest",
    )
    venusaur = PokemonState(
        species="Venusaur",
        level=50,
        base_stats=venusaur_stats,
        types=venusaur_types,
        ability="Overgrow",
        item=None,
        nature="Calm",
    )

    # Attach moves (PokemonState doesn't define .moves, so we just attach it here)
    charizard.moves = [flamethrower, air_slash]
    venusaur.moves = [giga_drain, sludge_bomb, stupid_move, op_move]

    # Field
    field = FieldState(weather=None, terrain=None)

    # Sides
    player_side = SideState(active=[charizard], party=[charizard], is_player=True)
    ai_side     = SideState(active=[venusaur], party=[venusaur], is_player=False)

    battle_state = BattleState(sides=[player_side, ai_side], field=field, turn=1)
    env = BattleEnv(battle_state)
    return env, flamethrower, air_slash

def main():
    random.seed(0)

    env, flamethrower, air_slash = make_test_battle()

    print("Initial state:")
    p = env.state.sides[0].active[0]
    o = env.state.sides[1].active[0]
    print(f"Player:   {p.species} HP={p.current_hp}/{p.calc_stat('HP')}")
    print(f"Opponent: {o.species} HP={o.current_hp}/{o.calc_stat('HP')}")
    print()

    for turn in range(1, 6):
        if env.done:
            break

        print(f"=== Turn {turn} ===")

        # Simple player policy: always use Flamethrower
        player_move = flamethrower

        # Peek at what the AI would choose before stepping (for debugging)
        ai_active = env.state.sides[1].active[0]
        player_active = env.state.sides[0].active[0]
        ai_move, _ = ai_policy.choose_move(ai_active, player_active, env.state, ai_active.moves)
        print(f"Player uses: {player_move.name}")
        print(f"AI plans to use: {ai_move.name}")

        result = env.step(player_move)

        p = env.state.sides[0].active[0]
        o = env.state.sides[1].active[0]
        print(f"After turn {turn}:")
        print(f"  Player   HP={p.current_hp}/{p.calc_stat('HP')}")
        print(f"  Opponent HP={o.current_hp}/{o.calc_stat('HP')}")
        print(f"  Reward={result['reward']} Done={result['done']}")
        print()

    if env.done:
        if env.winner == 0:
            print("Battle over: player won.")
        elif env.winner == 1:
            print("Battle over: AI won.")
        else:
            print("Battle over: unknown winner.")
    else:
        print("Battle not finished within 5 turns.")

if __name__ == "__main__":
    main()
