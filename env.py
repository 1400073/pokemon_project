# env.py
from typing import Any, Dict, Optional
import random
from data_loader import MoveData
from state import BattleState, SideState, PokemonState
from damage import calculate_damage
from ai_policy import choose_move

class BattleEnv:
    def __init__(self, battle_state: BattleState):
        self.state = battle_state
        self.done = False
        self.winner: Optional[int] = None  # 0 = player, 1 = AI
    
    def apply_turn(self, player_move: MoveData, player_target_idx: int = 1):
        """Simulate one turn of both sides acting. `player_move` is the move chosen by the player."""
        # Determine opponent (AI) move via AI policy:
        ai_side = self.state.sides[1]  # opponent is index 1
        player_side = self.state.sides[0]
        ai_active = ai_side.active[0]
        player_active = player_side.active[0]
        ai_move, ai_target = choose_move(ai_active, player_active, self.state, [m for m in ai_active.moves])  # assume PokemonState has a .moves list of MoveData
        # Determine move order (consider priority and speed)
        # Compute priority values:
        p_priority = player_move.priority
        ai_priority = ai_move.priority
        if p_priority != ai_priority:
            # higher priority goes first
            first_actor = 0 if p_priority > ai_priority else 1
        else:
            # same priority: compare effective speed
            p_speed = player_active.calc_stat("Spe")
            ai_speed = ai_active.calc_stat("Spe")
            if p_speed == ai_speed:
                # tie-break: 50/50 random
                first_actor = 0 if random.random() < 0.5 else 1
            else:
                first_actor = 0 if p_speed > ai_speed else 1
        # Execute moves in order
        actions = [(0, player_active, player_move, ai_active), (1, ai_active, ai_move, player_active)]
        # Sort actions by the determined order
        if first_actor == 1:
            actions.reverse()
        # Process each action
        for actor_idx, attacker, move, target in actions:
            # Check if target is already fainted (could have been fainted by the first action)
            if target.current_hp <= 0:
                continue  # skip if fainted
            if move.category == "Status":
                # handle status moves
                if move.name == "Thunder Wave" and target.status is None and "Ground" not in target.types:
                    target.status = "par"  # paralyze target
                    target.stat_stages["Spe"] = target.stat_stages.get("Spe",0)  # ensure key exists
                    # In Gen7/8, paralysis is 50% speed; in Run & Bun it's 25% speed, we already handle by stat stage or directly in calc_stat.
                    target.stat_stages["Spe"] -= 6  # effectively quarter speed if we treat -6 as -75%
                    # (This is one way to implement the 75% speed drop)
                # ... other status moves like burn, sleep, etc.
            else:
                # It's a damaging move; calculate damage and apply to target
                hits = 1
                if move.multihit != (1, 1):
                    # Determine number of hits (for multi-hit moves)
                    min_hits, max_hits = move.multihit
                    # Simplest: assume average or random hits. We'll just randomize for simulation.
                    hits = random.randint(min_hits, max_hits)
                    # If Skill Link ability, set hits = max_hits
                    if attacker.ability == "Skill Link":
                        hits = max_hits
                total_damage = 0
                for h in range(hits):
                    # Determine if move hits (accuracy check)
                    if move.accuracy is not None:
                        # Check accuracy vs target evasion - for simplicity, assume no evasion modifiers implemented
                        if random.randint(1, 100) > move.accuracy:
                            # move missed
                            continue
                    # Determine critical hit
                    is_crit = False
                    # (We could roll for crit based on crit chance; not fully implemented for brevity)
                    dmg_range = calculate_damage(attacker, target, move, self.state.field)
                    dmg = dmg_range[1]  # take max roll for actual damage simulation or randomly within range
                    # Subtract HP from target
                    target.current_hp = max(0, target.current_hp - dmg)
                    total_damage += dmg
                    # If target faints, break out of multi-hit loop
                    if target.current_hp == 0:
                        break
                # Recoil or healing effects after full move hits:
                if move.name in ["Double-Edge","Flare Blitz","Brave Bird","Wood Hammer"]:
                    # recoil 33% of damage dealt
                    recoil = total_damage // 3
                    attacker.current_hp = max(0, attacker.current_hp - recoil)
                if move.name in ["Wild Charge","Head Smash"]:
                    # recoil 25%
                    recoil = total_damage // 4
                    attacker.current_hp = max(0, attacker.current_hp - recoil)
                if move.name in ["Flare Blitz","Blaze Kick","Fire Punch"] and attacker.ability == "Flash Fire":
                    # Actually, Flash Fire prevents damage and boosts power, but for brevity ignore.
                    pass
                if "Drain" in move.name or move.name in ["Giga Drain","Leech Life","Oblivion Wing"]:
                    # heal 50% of damage dealt
                    heal = total_damage // 2
                    attacker.current_hp = min(attacker.current_hp + heal, attacker.calc_stat("HP"))
            # Check for fainted Pokémon
            if target.current_hp <= 0:
                # Target fainted, handle switch in or battle end
                if target is player_active:
                    # Player's Pokémon fainted
                    # In a full game, prompt for switch or if no Pokemon left, game over.
                    self.done = True
                    self.winner = 1  # AI wins
                else:
                    # Opponent fainted
                    # If opponent has more Pokemon, send next; otherwise player wins.
                    opp_side = self.state.sides[1]
                    alive = [mon for mon in opp_side.party if mon.current_hp > 0 and mon not in opp_side.active]
                    if alive:
                        # switch in next Pokemon (simple strategy: next in list)
                        new_mon = alive[0]
                        opp_side.active[0] = new_mon
                    else:
                        self.done = True
                        self.winner = 0  # player wins
    def step(self, action: MoveData) -> Dict[str, Any]:
        """Step the battle one turn with the player's chosen move `action` (MoveData). 
        Returns observation (state info) and a reward if using RL."""
        # For simplicity, our observation could be the BattleState itself or a summary.
        # We'll execute the turn:
        self.apply_turn(action)
        # Compute reward if any (for RL: e.g. +1 for winning, -1 for losing, 0 otherwise)
        reward = 0.0
        if self.done:
            reward = 1.0 if self.winner == 0 else -1.0
        # Assemble observation (here we just provide a simplified dict of relevant info)
        obs = {
            "player_hp": self.state.sides[0].active[0].current_hp,
            "opponent_hp": self.state.sides[1].active[0].current_hp,
            "weather": self.state.field.weather,
            "terrain": self.state.field.terrain,
            "player_status": self.state.sides[0].active[0].status,
            "opp_status": self.state.sides[1].active[0].status,
        }
        return {"obs": obs, "reward": reward, "done": self.done}
