import random

# Curated word lists for generating friendly names
ADJECTIVES = [
    'swift', 'brave', 'mighty', 'golden', 'silver', 'crimson', 'azure', 'emerald',
    'fierce', 'noble', 'royal', 'epic', 'legendary', 'cosmic', 'stellar', 'radiant',
    'thunder', 'lightning', 'storm', 'frost', 'flame', 'shadow', 'mystic', 'ancient',
    'iron', 'steel', 'diamond', 'crystal', 'blazing', 'soaring', 'rising', 'eternal',
    'wild', 'savage', 'primal', 'vicious', 'cunning', 'clever', 'wise', 'bold',
    'daring', 'fearless', 'valiant', 'heroic', 'glorious', 'triumphant', 'victorious'
]

NOUNS = [
    'dragon', 'phoenix', 'griffin', 'titan', 'warrior', 'champion', 'gladiator', 'knight',
    'samurai', 'ninja', 'ronin', 'sentinel', 'guardian', 'defender', 'crusader', 'paladin',
    'ranger', 'hunter', 'scout', 'vanguard', 'legion', 'battalion', 'brigade', 'regiment',
    'falcon', 'eagle', 'hawk', 'raven', 'wolf', 'bear', 'lion', 'tiger', 'panther', 'cobra',
    'viper', 'scorpion', 'spider', 'mantis', 'shark', 'kraken', 'leviathan', 'behemoth',
    'colossus', 'juggernaut', 'tempest', 'cyclone', 'hurricane', 'typhoon', 'blizzard'
]

MATCH_DESCRIPTORS = [
    'clash', 'duel', 'battle', 'showdown', 'bout', 'match', 'contest',
    'encounter', 'skirmish', 'brawl', 'rumble', 'fight', 'conflict', 'struggle'
]

def generate_tournament_name() -> str:
    """Generate a friendly tournament name like 'crimson-phoenix-clash'"""
    adj = random.choice(ADJECTIVES)
    noun = random.choice(NOUNS)
    descriptor = random.choice(MATCH_DESCRIPTORS)
    return f"{adj}-{noun}-{descriptor}"

def generate_match_name(round_num: int, match_num: int) -> str:
    """Generate a friendly match name like 'r2-steel-dragon-duel'"""
    adj = random.choice(ADJECTIVES)
    noun = random.choice(NOUNS)
    descriptor = random.choice(MATCH_DESCRIPTORS)
    return f"r{round_num}-{adj}-{noun}-{descriptor}"

def generate_short_id(prefix: str = "") -> str:
    """Generate a short random ID for uniqueness (fallback)"""
    import uuid
    short = uuid.uuid4().hex[:8]
    return f"{prefix}{short}" if prefix else short
