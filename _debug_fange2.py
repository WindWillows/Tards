import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tards import Game, Player, MinionCard, Cost, target_friendly_positions, CardType
from tards.card_db import DEFAULT_REGISTRY
import card_pools.underworld

# Monkey-patch register_conspiracy to trace
orig_register = Game.register_conspiracy
def traced_register(self, conspiracy, player):
    owner_id = id(conspiracy)
    conspiracy._listener_owner_id = owner_id
    def listener(event):
        if conspiracy not in player.active_conspiracies:
            return
        if not conspiracy.condition_fn:
            return
        event_data = dict(event.data)
        event_data["event_type"] = event.type
        result = conspiracy.condition_fn(self, event_data, player)
        print(f'  [TRACE CONSPIRACY] {conspiracy.name} checking {event.type} -> {result}')
        if result:
            player.active_conspiracies.remove(conspiracy)
            self.unregister_listeners_by_owner(owner_id)
            def make_trigger(c=conspiracy, p=player, ev=event):
                def trigger():
                    c.effect_fn(self, ev.data, p)
                    p.card_dis.append(c)
                return trigger
            self.effect_queue.queue(f"阴谋 [{c.name}]", make_trigger())
    self.event_bus.register("*", listener, priority=50, owner_id=owner_id)
    return owner_id
Game.register_conspiracy = traced_register

p1 = Player(side=0, name='P1', diver='test', card_deck=[])
p2 = Player(side=1, name='P2', diver='test', card_deck=[])

for _ in range(20):
    p1.card_deck.append(MinionCard(name='Dummy', owner=p1, cost=Cost(t=0), targets=target_friendly_positions, attack=0, health=1))
    p2.card_deck.append(MinionCard(name='Dummy', owner=p2, cost=Cost(t=0), targets=target_friendly_positions, attack=0, health=1))

defs = [d for d in DEFAULT_REGISTRY.all_cards() if d.name == '反戈' and d.card_type == CardType.CONSPIRACY]
fan_ge = defs[0].to_game_card(p1)

p1.card_hand = [fan_ge, MinionCard(name='TestMinion', owner=p1, cost=Cost(t=1), targets=target_friendly_positions, attack=1, health=1)]
p2.card_hand = [MinionCard(name='EnemyMinion', owner=p2, cost=Cost(t=3), targets=target_friendly_positions, attack=2, health=2)]
p1.sacrifice_chooser = lambda req: None
p2.sacrifice_chooser = lambda req: None

state = {'step': 0}
def actor(game, active, opponent):
    if game.current_turn == 1 and active.name == 'P1' and state['step'] == 0:
        state['step'] = 1
        return {'type': 'play', 'serial': 1}
    if game.current_turn == 1 and active.name == 'P1' and state['step'] == 1:
        state['step'] = 2
        return {'type': 'brake'}
    if game.current_turn == 2 and active.name == 'P2' and state['step'] == 2:
        state['step'] = 3
        return {'type': 'brake'}
    if game.current_turn == 3 and active.name == 'P1' and state['step'] == 3:
        state['step'] = 4
        return {'type': 'brake'}
    if game.current_turn == 4 and active.name == 'P2' and state['step'] == 4:
        state['step'] = 5
        return {'type': 'play', 'serial': 1, 'target': (0, 0)}
    if game.current_turn == 4 and active.name == 'P2' and state['step'] == 5:
        state['step'] = 6
        return {'type': 'brake'}
    return {'type': 'brake'}

game = Game(p1, p2, action_provider=actor)
game.start_game()
