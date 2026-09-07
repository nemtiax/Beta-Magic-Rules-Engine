"""Run from the project root with: python -m examples.sequential"""
from beta_draft import DraftBot, DraftContext

bot = DraftBot()
packs = [
    ["Fireball", "Grizzly Bears", "Healing Salve", "Island"],
    ["Lightning Bolt", "Hill Giant", "Purelace", "Forest"],
    ["Sedge Troll", "Gray Ogre", "Mons's Goblin Raiders"],
    ["Terror", "Dark Ritual", "Black Ward"],
    ["Badlands", "Wall of Wood", "Cursed Land"],
]
for number, pack in enumerate(packs, 1):
    choice = bot.pick_with_details(pack, context=DraftContext(1, number))
    print(f"Pick {number}: {choice.card} ({choice.score:.2f})")
    print("  " + choice.reasons[0])
print("Pool:", ", ".join(bot.pool))
print("Leading color plans:", [("".join(p.colors), round(p.weight, 3)) for p in bot.color_plans()[:3]])
