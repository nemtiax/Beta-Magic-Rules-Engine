import json

data = json.load(open("cards/LEB.json","r", encoding="utf-8"))

cards = data['data']['cards']

with open("cards/card_reference.txt", "w", encoding="utf-8") as f:
    for card in cards:
        name = card['name']
        text = card['originalText'] if 'originalText' in card else None
        mana = card['manaCost'] if 'manaCost' in card else None
        type = card['originalType']
        power = card['power'] if 'power' in card else None
        toughness = card['toughness'] if 'toughness' in card else None

        f.write(f" - [ ] {name}\n")
        continue
        if mana is not None:
            f.write(f"Mana: {mana}\n")
        f.write(f"Type: {type}\n")
        if text is not None:
            f.write(f"Text: {text}\n")
        if power is not None:
            f.write(f"{power}/{toughness}\n")
        f.write("\n")


