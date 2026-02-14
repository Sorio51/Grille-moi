import json
import random
import os
import copy

class GridGenerator:
    def __init__(self, size=15):
        self.size = size
        self.grid = [[' ' for _ in range(size)] for _ in range(size)]
        self.placed_words = []

    def reset(self):
        self.grid = [[' ' for _ in range(self.size)] for _ in range(self.size)]
        self.placed_words = []

    def load_json_file(self, filename, default):
        if os.path.exists(filename) and os.path.getsize(filename) > 0:
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    return json.loads(f.read())
            except: return default
        return default

    def is_in_bounds(self, x, y):
        return 0 <= x < self.size and 0 <= y < self.size

    def can_place(self, word, x, y, dr, force_no_overlap=False):
        if dr == 'horizontal':
            if x + len(word) > self.size: return False
        else:
            if y + len(word) > self.size: return False

        has_intersection = False

        for i in range(len(word)):
            curr_x = x + i if dr == 'horizontal' else x
            curr_y = y if dr == 'horizontal' else y + i
            char = word[i]

            if self.grid[curr_y][curr_x] != ' ' and self.grid[curr_y][curr_x] != char:
                return False

            if self.grid[curr_y][curr_x] == char:
                has_intersection = True

            for dx, dy in [(-1,0), (1,0), (0,-1), (0,1)]:
                nx, ny = curr_x + dx, curr_y + dy
                if self.is_in_bounds(nx, ny):
                    neighbor = self.grid[ny][nx]
                    if neighbor != ' ' and self.grid[curr_y][curr_x] == ' ':
                        return False

        if force_no_overlap:
            return True
        return has_intersection or len(self.placed_words) == 0

    def generate(self, nb_words=8, min_words=5):
        banque = self.load_json_file("banque.json", [])
        history = self.load_json_file("historique.json", [])

        available = [w for w in banque if w[0].upper() not in history]
        if len(available) < min_words:
            print("🔄 Reset historique (Banque vide)")
            available = list(banque)
            history = []

        self.reset()
        random.shuffle(available)
        available.sort(key=lambda x: len(x[0]), reverse=True)

        word_id = 1
        local_history = []

        for word_pair in available:
            if len(self.placed_words) >= nb_words: break
            word, clue = word_pair[0].upper(), word_pair[1]
            placed = False

            candidates = []
            if not self.placed_words:
                candidates.append((self.size//2 - len(word)//2, self.size//2, 'horizontal'))
            else:
                for pw in self.placed_words:
                    for i, char_p in enumerate(pw['answer']):
                        for j, char_n in enumerate(word):
                            if char_p == char_n:
                                dr = 'vertical' if pw['direction'] == 'horizontal' else 'horizontal'
                                sx = (pw['x'] + i) - (j if dr == 'horizontal' else 0)
                                sy = (pw['y'] + 0) - (0 if dr == 'horizontal' else j) if pw['direction'] == 'horizontal' else (pw['y'] + i) - (0 if dr == 'horizontal' else j)
                                if pw['direction'] == 'vertical':
                                    sx = pw['x'] - (j if dr == 'horizontal' else 0)
                                candidates.append((sx, sy, dr))

            random.shuffle(candidates)
            for (cx, cy, cdr) in candidates:
                if self.is_in_bounds(cx, cy) and self.can_place(word, cx, cy, cdr):
                    self.place_word(word, clue, cx, cy, cdr, word_id)
                    local_history.append(word)
                    word_id += 1
                    placed = True
                    break

            if not placed:
                for _ in range(100):
                    rx = random.randint(0, self.size-1)
                    ry = random.randint(0, self.size-1)
                    rdr = random.choice(['horizontal', 'vertical'])
                    if self.is_in_bounds(rx, ry) and self.can_place(word, rx, ry, rdr, force_no_overlap=True):
                        self.place_word(word, clue, rx, ry, rdr, word_id)
                        local_history.append(word)
                        word_id += 1
                        placed = True
                        break

        history_strings = [h for h in history if isinstance(h, str)]
        new_history = list(set(history_strings + local_history))
        with open("grille_exemple.json", "w", encoding="utf-8") as f:
            json.dump({"words": self.placed_words}, f, indent=2, ensure_ascii=False)
        with open("historique.json", "w", encoding="utf-8") as f:
            json.dump(new_history, f, indent=2, ensure_ascii=False)
        print(f"✅ Grille générée avec {len(self.placed_words)} mots.")

    def place_word(self, word, clue, x, y, dr, wid):
        for i in range(len(word)):
            if dr == 'horizontal': self.grid[y][x+i] = word[i]
            else: self.grid[y+i][x] = word[i]
        self.placed_words.append({
            "id": wid, "clue": clue, "answer": word,
            "x": x, "y": y, "direction": dr, "solved": False
        })

if __name__ == "__main__":
    GridGenerator(size=15).generate(nb_words=8, min_words=4)