"""Portable Sol Reach rules. No editor/global state; callers own persistence and UI."""
from dataclasses import dataclass, field
from collections import Counter
import math

HERBS = {'dawnleaf': 'light', 'rillprism': 'cool', 'cinderbud': 'heat',
         'stillmoss': 'calm', 'stridefern': 'vigor', 'clearbell': 'purify'}

def quantity(value):
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value <= 0:
        raise ValueError('quantity must be finite and positive')
    return value

@dataclass
class Farm:
    clean_water: float = 20
    dirty_water: float = 0
    feed: float = 10
    eggs: int = 0
    milk: int = 0
    hunger: float = 80
    thirst: float = 80
    production_seconds: float = 0
    discoveries: set = field(default_factory=set)
    herbs: dict = field(default_factory=lambda: {herb: 3 for herb in HERBS})
    quest_facts: set = field(default_factory=set)

    def collect(self, source, amount=1):
        quantity(amount)
        if source not in ('spring', 'rain', 'well'):
            raise ValueError('unknown source')
        attr = 'dirty_water' if source == 'well' else 'clean_water'
        setattr(self, attr, getattr(self, attr) + amount)

    def filter(self, amount=1):
        quantity(amount)
        if self.dirty_water < amount:
            raise ValueError('not enough dirty water')
        self.dirty_water -= amount
        self.clean_water += amount
        self.quest_facts.add('filtered_well_water')

    def drink(self):
        if self.clean_water < 1:
            raise ValueError('clean water required')
        self.clean_water -= 1
        self.thirst = min(100, self.thirst + 35)  # data/survival/stats.json

    def brew(self, ordered_herbs, effects):
        """Same endpoints seal a ring; the centre chooses a shared essence effect.

        Requires three herbs and one clean water. Invalid recipes consume nothing.
        Unlike stacking/pitch-chord recipes, endpoint agreement determines duration.
        """
        if len(ordered_herbs) != 3 or any(h not in HERBS for h in ordered_herbs):
            raise ValueError('exactly three known herbs required')
        left, centre, right = (HERBS[h] for h in ordered_herbs)
        effect = effects.get(centre + '+' + centre)
        if left != right or not effect:
            raise ValueError('ring endpoints must agree and centre needs an effect')
        if self.clean_water < 1:
            raise ValueError('clean water required')
        needed = Counter(ordered_herbs)
        if any(self.herbs.get(herb, 0) < count for herb, count in needed.items()):
            raise ValueError('not enough herbs')
        result = dict(effect)
        if 'dur_s' in result:
            result['dur_s'] *= 2 if left != centre else 1
        self.clean_water -= 1
        for herb, count in needed.items():
            self.herbs[herb] -= count
        self.discoveries.add(result['id'])
        self.quest_facts.add('brewed_ring')
        return result

    def tick(self, seconds):
        quantity(seconds)
        self.hunger = max(0, self.hunger - .05 * seconds)
        self.thirst = max(0, self.thirst - .08 * seconds)
        # One flock/one goat: pauses when either resource is absent. No dry-time backlog.
        cycles = int((self.production_seconds + seconds) // 600)
        funded = min(cycles, int(self.feed), int(self.clean_water))
        self.feed -= funded
        self.clean_water -= funded
        self.eggs += funded
        self.milk += funded
        self.production_seconds = (self.production_seconds + seconds) % 600
        return funded

    def cook(self):
        if self.eggs < 1 or self.milk < 1 or self.clean_water < 1:
            raise ValueError('egg, milk and clean water required')
        self.eggs -= 1
        self.milk -= 1
        self.clean_water -= 1
        self.hunger = min(100, self.hunger + 30)
        self.quest_facts.add('cooked_custard')
        return 'sol_custard'

    def adventure_stage(self):
        for fact,stage in [('filtered_well_water','restore_waterworks'),
                           ('brewed_ring','discover_ring'),('cooked_custard','feed_the_keeper')]:
            if fact not in self.quest_facts: return stage
        return 'portal_ready'

    def save(self):
        return {**self.__dict__, 'herbs':dict(self.herbs), 'discoveries': sorted(self.discoveries),
                'quest_facts':sorted(self.quest_facts), 'schema': 1}

    @classmethod
    def restore(cls, data):
        data = dict(data)
        if data.pop('schema', None) != 1:
            raise ValueError('unsupported save schema')
        data['discoveries'] = set(data['discoveries'])
        data['quest_facts'] = set(data['quest_facts'])
        state = cls(**data)
        for key in ('clean_water', 'dirty_water', 'feed', 'eggs', 'milk', 'hunger', 'thirst', 'production_seconds'):
            value = getattr(state, key)
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value < 0:
                raise ValueError('invalid saved ' + key)
        if any(not isinstance(n,int) or isinstance(n,bool) or n<0 for n in (state.eggs,state.milk)):
            raise ValueError('product counts must be integers')
        if not isinstance(state.herbs,dict) or any(h not in HERBS or not isinstance(n,int) or isinstance(n,bool) or n<0 for h,n in state.herbs.items()):
            raise ValueError('invalid herb inventory')
        if state.hunger > 100 or state.thirst > 100 or state.production_seconds >= 600:
            raise ValueError('invalid saved range')
        return state
