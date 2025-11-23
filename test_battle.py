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
    charizard_stats = {"HP": 78, "Atk": 84, "Def": 78, "SpA": 109, "SpD": 85, "Spe": 100}
    venusaur_stats = {"HP": 80, "Atk": 82, "Def": 83, "SpA": 100, "SpD": 100, "Spe": 80}

    charizard_types = ["Fire", "Flying"]
    venusaur_types = ["Grass", "Poison"]

    flamethrower = MoveData("Flamethrower", "Fire", "Special", 90, 100, 15)
    air_slash = MoveData("Air Slash", "Flying", "Special", 75, 95, 15)
    giga_drain = MoveData("Giga Drain", "Grass", "Special", 75, 100, 10)
    scratch = MoveData("Scratch", "Normal", "Physical", 40, 100, 35)
    sludge_bomb = MoveData("Sludge Bomb", "Poison", "Special", 90, 100, 10)

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

    charizard.moves = [flamethrower, air_slash]
    venusaur.moves = [giga_drain, sludge_bomb, scratch]

    field = FieldState()
    player_side = SideState(active=[charizard], party=[charizard], is_player=True)
    ai_side = SideState(active=[venusaur], party=[venusaur], is_player=False)
    battle_state = BattleState(sides=[player_side, ai_side], field=field, turn=1)
    env = BattleEnv(battle_state)
    return env, flamethrower, air_slash


def build_env(player_active: PokemonState, opponent_active: PokemonState, *, player_bench=None, opponent_bench=None, field=None) -> BattleEnv:
    player_party = [player_active] + list(player_bench or [])
    opponent_party = [opponent_active] + list(opponent_bench or [])
    player_side = SideState(active=[player_active], party=player_party, is_player=True)
    opponent_side = SideState(active=[opponent_active], party=opponent_party, is_player=False)
    battle_state = BattleState(sides=[player_side, opponent_side], field=field or FieldState(), turn=1)
    return BattleEnv(battle_state)


def make_status_move(name: str, move_type: str = "Normal") -> MoveData:
    return MoveData(name, move_type, "Status", 0, 100, 20)


SPLASH_MOVE = make_status_move("Splash")
SCREECH_MOVE = make_status_move("Screech", "Normal")
BATON_PASS_MOVE = make_status_move("Baton Pass", "Normal")
BASIC_ATTACK = MoveData("Tackle", "Normal", "Physical", 40, 100, 35)


def test_basic_battle() -> None:
    random.seed(0)
    env, flamethrower, _ = make_test_battle()
    env.step(flamethrower)
    env.step(flamethrower)
    assert env.done and env.winner == 0


def test_intimidate_eject_pack() -> None:
    stats = {"HP": 80, "Atk": 90, "Def": 80, "SpA": 80, "SpD": 80, "Spe": 80}
    target = PokemonState("Hero", 50, stats, ["Normal"], "Blaze", item="Eject Pack")
    bench = PokemonState("Backup", 50, stats, ["Normal"], "Blaze")
    intimidator = PokemonState("Intimidator", 50, stats, ["Normal"], "Intimidate")
    target.moves = [SPLASH_MOVE]
    bench.moves = [SPLASH_MOVE]
    intimidator.moves = [SPLASH_MOVE]

    env = build_env(target, intimidator, player_bench=[bench])
    active_player = env.state.sides[0].active[0]
    assert active_player is bench, "Eject Pack should force the target out immediately"
    assert target.item is None
    assert target.get_stage_value("Atk") == -1


def test_white_herb_screech() -> None:
    stats = {"HP": 90, "Atk": 85, "Def": 90, "SpA": 80, "SpD": 80, "Spe": 80}
    victim = PokemonState("WhiteHerbMon", 50, stats, ["Normal"], "Blaze", item="White Herb")
    attacker = PokemonState("Screecher", 50, stats, ["Normal"], "Pressure")
    victim.moves = [SPLASH_MOVE]
    attacker.moves = [SCREECH_MOVE]

    env = build_env(victim, attacker)
    random.seed(0)
    env.apply_turn(SPLASH_MOVE)
    assert victim.item is None
    assert victim.get_stage_value("Def") == 0, "White Herb should reset the Screech drop"


def test_baton_pass_transfers_boosts() -> None:
    stats = {"HP": 100, "Atk": 80, "Def": 80, "SpA": 90, "SpD": 80, "Spe": 80}
    passer = PokemonState("Passer", 50, stats, ["Normal"], "Blaze")
    sweeper = PokemonState("Sweeper", 50, stats, ["Normal"], "Blaze")
    dummy = PokemonState("Dummy", 50, stats, ["Normal"], "Blaze")
    passer.moves = [BATON_PASS_MOVE]
    sweeper.moves = [SPLASH_MOVE]
    dummy.moves = [SPLASH_MOVE]

    env = build_env(passer, dummy, player_bench=[sweeper])
    passer = env.state.sides[0].active[0]
    sweeper = env.state.sides[0].party[1]
    passer.change_stat_stage("SpA", 2, source=passer)
    passer.accuracy_stage = 1
    passer.substitute_hp = passer.max_hp // 4
    passer.volatiles["aqua_ring"] = True

    env.apply_turn(BATON_PASS_MOVE)
    active = env.state.sides[0].active[0]
    assert active is sweeper
    assert active.get_stage_value("SpA") == 2
    assert active.accuracy_stage == 1
    assert active.substitute_hp == passer.max_hp // 4
    assert active.volatiles.get("aqua_ring") is True


def test_pinch_berry_heal() -> None:
    stats = {"HP": 120, "Atk": 80, "Def": 80, "SpA": 80, "SpD": 80, "Spe": 80}
    berrymon = PokemonState("Pinch", 50, stats, ["Normal"], "Blaze", item="Figy Berry")
    foe = PokemonState("Foe", 50, stats, ["Normal"], "Blaze")
    berrymon.moves = [SPLASH_MOVE]
    foe.moves = [BASIC_ATTACK]
    env = build_env(berrymon, foe)
    threshold = berrymon.max_hp // 4
    damage = berrymon.max_hp - threshold
    env._deal_damage(berrymon, damage)
    expected = min(berrymon.max_hp, threshold + berrymon.max_hp // 2)
    assert berrymon.current_hp == expected
    assert berrymon.item is None


def run_all_tests() -> None:
    test_basic_battle()
    test_intimidate_eject_pack()
    test_white_herb_screech()
    test_baton_pass_transfers_boosts()
    test_pinch_berry_heal()
    print("All battle tests passed.")


if __name__ == "__main__":
    run_all_tests()
