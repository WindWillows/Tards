import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tards import Game, Player, MinionCard, Cost, target_friendly_positions
from tards.card_db import DEFAULT_REGISTRY
import card_pools.underworld

p1 = Player(side=0, name='P1', diver='test', card_deck=[])
p2 = Player(side=1, name='P2', diver='test', card_deck=[])

for _ in range(20):
    p1.card_deck.append(MinionCard(name='Dummy', owner=p1, cost=Cost(t=0), targets=target_friendly_positions, attack=0, health=1))
    p2.card_deck.append(MinionCard(name='Dummy', owner=p2, cost=Cost(t=0), targets=target_friendly_positions, attack=0, health=1))

defs = [d for d in DEFAULT_REGISTRY.all_cards() if d.name == '反戈' and d.card_type == card_pools.underworld.CardType.CONSPIRACY]
fan_ge = defs[0].to_game_card(p1)

p1.card_hand = [fan_ge, MinionCard(name='TestMinion', owner=p1, cost=Cost(t=1), targets=target_friendly_positions, attack=1, health=1)]
p2.card_hand = [MinionCard(name='EnemyMinion', owner=p2, cost=Cost(t=3), targets=target_friendly_positions, attack=2, health=2)]
p1.sacrifice_chooser = lambda req: None
p2.sacrifice_chooser = lambda req: None

state = {'step': 0}
def actor(game, active, opponent):
    if game.current_turn == 1 and active.name == 'P1' and state['step'] == 0:
        state['step'] = 1
        return {'type': 'play', 'serial': 5}
    if game.current_turn == 1 and active.name == 'P1' and state['step'] == 1:
        state['step'] = 2
        return {'type': 'brake'}
    if game.current_turn == 2 and active.name == 'P2' and state['step'] == 2:
        state['step'] = 3
        ok1, reason1 = active.card_can_play(1, (0, 0))
        print(f'DEBUG1 card_can_play(1, (0,0)) = {ok1}, reason="{reason1}"')
        print(f'Hand serials: {[(i+1, c.name, c.cost.t if c.cost else None) for i,c in enumerate(active.card_hand)]}')
        return {'type': 'play', 'serial': 1, 'target': (0, 0)}
    if game.current_turn == 2 and active.name == 'P2' and state['step'] == 3:
        state['step'] = 4
        return {'type': 'brake'}
    return {'type': 'brake'}

game = Game(p1, p2, action_provider=actor)
game.start_game()
