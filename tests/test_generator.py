import unittest
import os
import json
import tempfile
import sys
from pathlib import Path
from unittest.mock import patch
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))
from generator import GridGenerator

class TestGridGenerator(unittest.TestCase):
    def setUp(self):
        self.gen = GridGenerator(size=10)
    def tearDown(self):
        test_files = ['grille_exemple.json', 'historique.json']
        for f in test_files:
            if os.path.exists(f):
                os.remove(f)

    def test_init(self):
        gen = GridGenerator(size=8)
        self.assertEqual(gen.size, 8)
        self.assertEqual(len(gen.grid), 8)
        self.assertEqual(len(gen.grid[0]), 8)
        self.assertEqual(gen.placed_words, [])
        for row in gen.grid:
            for cell in row:
                self.assertEqual(cell, ' ')

    def test_reset(self):
        self.gen.grid[5][5] = 'A'
        self.gen.placed_words = [{'test': 'data'}]
        self.gen.reset()
        self.assertEqual(self.gen.grid[5][5], ' ')
        self.assertEqual(self.gen.placed_words, [])

    def test_is_in_bounds(self):
        self.assertTrue(self.gen.is_in_bounds(0, 0))
        self.assertTrue(self.gen.is_in_bounds(9, 9))
        self.assertTrue(self.gen.is_in_bounds(5, 5))
        self.assertFalse(self.gen.is_in_bounds(-1, 0))
        self.assertFalse(self.gen.is_in_bounds(0, -1))
        self.assertFalse(self.gen.is_in_bounds(10, 0))
        self.assertFalse(self.gen.is_in_bounds(0, 10))

    def test_place_word_horizontal(self):
        """Test placement horizontal"""
        self.gen.place_word("TEST", "Un test", 1, 2, "horizontal", 1)

        self.assertEqual(self.gen.grid[2][1], 'T')
        self.assertEqual(self.gen.grid[2][2], 'E')
        self.assertEqual(self.gen.grid[2][3], 'S')
        self.assertEqual(self.gen.grid[2][4], 'T')

        self.assertEqual(len(self.gen.placed_words), 1)
        word = self.gen.placed_words[0]
        self.assertEqual(word['answer'], 'TEST')
        self.assertEqual(word['clue'], 'Un test')
        self.assertEqual(word['x'], 1)
        self.assertEqual(word['y'], 2)
        self.assertEqual(word['direction'], 'horizontal')
        self.assertEqual(word['id'], 1)
        self.assertFalse(word['solved'])

    def test_place_word_vertical(self):
        """Test placement vertical"""
        self.gen.place_word("HI", "Salut", 3, 1, "vertical", 2)

        self.assertEqual(self.gen.grid[1][3], 'H')
        self.assertEqual(self.gen.grid[2][3], 'I')

        word = self.gen.placed_words[0]
        self.assertEqual(word['direction'], 'vertical')

    def test_can_place_boundaries(self):
        """Test limites de placement"""
        self.assertFalse(self.gen.can_place("TOOLONG", 8, 5, "horizontal"))

        self.assertFalse(self.gen.can_place("TOOLONG", 5, 8, "vertical"))

        self.assertTrue(self.gen.can_place("LIMIT", 5, 5, "horizontal"))

    def test_can_place_empty_grid(self):
        """Test placement sur grille vide"""
        self.assertTrue(self.gen.can_place("PYTHON", 2, 2, "horizontal"))
        self.assertTrue(self.gen.can_place("JAVA", 5, 1, "vertical"))

    def test_can_place_with_intersections(self):
        """Test placement avec intersections"""
        self.gen.place_word("PYTHON", "Langage", 2, 2, "horizontal", 1)

        can_place = self.gen.can_place("PROG", 2, 0, "vertical")
        self.assertTrue(self.gen.can_place("OTHER", 0, 0, "horizontal", force_no_overlap=True))

    def test_load_json_file_valid(self):
        """Test chargement fichier JSON valide"""
        test_data = [["PYTHON", "Langage"], ["TEST", "Essai"]]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_data, f)
            temp_file = f.name

        try:
            result = self.gen.load_json_file(temp_file, [])
            self.assertEqual(result, test_data)
        finally:
            os.unlink(temp_file)

    def test_load_json_file_missing(self):
        """Test fichier inexistant"""
        result = self.gen.load_json_file("does_not_exist.json", ["default"])
        self.assertEqual(result, ["default"])

    def test_load_json_file_empty(self):
        """Test fichier vide"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name

        try:
            result = self.gen.load_json_file(temp_file, ["default"])
            self.assertEqual(result, ["default"])
        finally:
            os.unlink(temp_file)

    def test_load_json_file_corrupted(self):
        """Test fichier JSON corrompu"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"invalid": json}')
            temp_file = f.name

        try:
            result = self.gen.load_json_file(temp_file, ["default"])
            self.assertEqual(result, ["default"])
        finally:
            os.unlink(temp_file)

    def test_generate_basic(self):
        """Test génération basique"""
        test_words = [
            ["PYTHON", "Langage de programmation"],
            ["TEST", "Vérification"],
            ["CODE", "Instructions"]
        ]

        with patch.object(self.gen, 'load_json_file') as mock_load:
            mock_load.return_value = test_words
            self.gen.generate(nb_words=2)

        self.assertGreaterEqual(len(self.gen.placed_words), 1)

        for word in self.gen.placed_words:
            if word['direction'] == 'horizontal':
                self.assertLessEqual(word['x'] + len(word['answer']), self.gen.size)
            else:
                self.assertLessEqual(word['y'] + len(word['answer']), self.gen.size)

            self.assertGreaterEqual(word['x'], 0)
            self.assertGreaterEqual(word['y'], 0)

    def test_generate_empty_bank(self):
        """Test génération avec banque vide"""
        with patch.object(self.gen, 'load_json_file') as mock_load:
            mock_load.return_value = []
            self.gen.generate(nb_words=5)

        self.assertEqual(len(self.gen.placed_words), 0)

    def test_generate_creates_files(self):
        """Test que la génération crée les fichiers"""
        test_words = [["WORD", "Definition"]]

        with patch.object(self.gen, 'load_json_file') as mock_load:
            mock_load.return_value = test_words
            self.gen.generate(nb_words=1)

        self.assertTrue(os.path.exists('grille_exemple.json'))
        self.assertTrue(os.path.exists('historique.json'))

        with open('grille_exemple.json', 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.assertIn('words', data)
        self.assertIsInstance(data['words'], list)

    def test_single_letter_word(self):
        """Test mot d'une seule lettre"""
        self.gen.place_word("A", "Une lettre", 5, 5, "horizontal", 1)

        self.assertEqual(self.gen.grid[5][5], 'A')
        self.assertEqual(len(self.gen.placed_words), 1)

    def test_word_at_edge(self):
        """Test placement en bordure"""
        self.gen.place_word("A", "Bord", 9, 9, "horizontal", 1)
        self.assertEqual(self.gen.grid[9][9], 'A')

    def test_multiple_words_placement(self):
        """Test placement de plusieurs mots"""
        words = [
            ("FIRST", "Premier", 1, 1, "horizontal"),
            ("SECOND", "Deuxième", 1, 3, "horizontal"),
            ("THIRD", "Troisième", 3, 1, "vertical")
        ]

        for i, (word, clue, x, y, direction) in enumerate(words, 1):
            self.gen.place_word(word, clue, x, y, direction, i)

        self.assertEqual(len(self.gen.placed_words), 3)

        ids = [w['id'] for w in self.gen.placed_words]
        self.assertEqual(ids, [1, 2, 3])

    def test_performance_large_grid(self):
        """Test performance sur grande grille"""
        import time

        large_gen = GridGenerator(size=20)
        test_words = [["WORD" + str(i), f"Clue {i}"] for i in range(20)]

        start_time = time.time()

        with patch.object(large_gen, 'load_json_file') as mock_load:
            mock_load.return_value = test_words
            large_gen.generate(nb_words=10)

        duration = time.time() - start_time

        self.assertLess(duration, 5.0)


if __name__ == '__main__':
    unittest.main(verbosity=2)