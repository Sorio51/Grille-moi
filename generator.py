import json
import random

class GridGenerator:
    def __init__(self, size=10):
        self.size = size
        self.grid = [['' for _ in range(size)] for _ in range(size)]
        self.placed_words = []

    def can_place(self, word, x, y, direction):
        if direction == 'horizontal':
            if x + len(word) > self.size: return False
            for i in range(len(word)):
                if self.grid[y][x+i] != '' and self.grid[y][x+i] != word[i]:
                    return False
        else:
            if y + len(word) > self.size: return False
            for i in range(len(word)):
                if self.grid[y+i][x] != '' and self.grid[y+i][x] != word[i]:
                    return False
        return True

    def place(self, word, clue, x, y, direction, word_id):
        if direction == 'horizontal':
            for i in range(len(word)):
                self.grid[y][x+i] = word[i]
        else:
            for i in range(len(word)):
                self.grid[y+i][x] = word[i]
        
        self.placed_words.append({
            "id": word_id,
            "clue": clue,
            "answer": word.upper(),
            "x": x,
            "y": y,
            "direction": direction,
            "solved": False
        })

    def generate(self, word_list):
        # Trier les mots du plus long au plus court pour faciliter le placement
        word_list.sort(key=lambda x: len(x[0]), reverse=True)
        
        word_id = 1
        for word, clue in word_list:
            placed = False
            # Pour le premier mot, on le place un peu au hasard au centre
            if not self.placed_words:
                self.place(word, clue, 2, 2, 'horizontal', word_id)
                word_id += 1
                continue

            # Tentative de placement avec intersection
            attempts = 0
            while not placed and attempts < 100:
                direction = random.choice(['horizontal', 'vertical'])
                x = random.randint(0, self.size - 1)
                y = random.randint(0, self.size - 1)
                
                if self.can_place(word, x, y, direction):
                    # Bonus : on vérifie s'il y a au moins une intersection avec l'existant
                    has_intersection = False
                    for i in range(len(word)):
                        curr_x = x + i if direction == 'horizontal' else x
                        curr_y = y if direction == 'horizontal' else y + i
                        if self.grid[curr_y][curr_x] == word[i]:
                            has_intersection = True
                    
                    if has_intersection or attempts > 50: # On finit par forcer si besoin
                        self.place(word, clue, x, y, direction, word_id)
                        word_id += 1
                        placed = True
                attempts += 1

    def export_json(self, filename="grille_generee.json"):
        data = {
            "id": "gen_" + str(random.randint(100, 999)),
            "title": "Grille Aléatoire",
            "width": self.size,
            "height": self.size,
            "words": self.placed_words
        }
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Succès ! {len(self.placed_words)} mots placés dans {filename}")

# --- CONFIGURATION ET LANCEMENT ---
if __name__ == "__main__":
    # Liste de tes mots et indices
    mes_mots = [
        ("PYTHON", "Langage de programmation"),
        ("TWITCH", "Plateforme de streaming"),
        ("BOT", "Assistant automatisé"),
        ("CHAT", "Il miaule ou on y écrit"),
        ("CODE", "Série d'instructions"),
        ("STREAM", "Diffusion en direct"),
        ("CLAVIER", "Pour taper du texte"),
        ("SOURIS", "Petit rongeur ou accessoire PC")
    ]

    gen = GridGenerator(size=12)
    gen.generate(mes_mots)
    gen.export_json("grille_exemple.json") # On écrase l'ancienne pour tester