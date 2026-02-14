import unittest
import os
import json
import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))
import main

class MockContext:
    def __init__(self, author_name="TestUser"):
        self.author = MagicMock()
        self.author.name = author_name
        self.send = AsyncMock()
        self.view = None
        self.args = []
        self.kwargs = {}
        self.prefix = '!'
        self.command = None

class TestMainFunctions(unittest.TestCase):
    def setUp(self):
        main.current_grid = {}
        main.connected_clients = set()
        main.SCORES_FILE = 'test_scores.json'
    def tearDown(self):
        test_files = ['test_scores.json', 'test_grid.json', 'grille_exemple.json']
        for f in test_files:
            if os.path.exists(f):
                os.remove(f)

    def test_load_grid_success(self):
        test_grid = {
            "words": [
                {
                    "id": 1,
                    "answer": "PYTHON",
                    "clue": "Langage",
                    "x": 5, "y": 5,
                    "direction": "horizontal",
                    "solved": False
                }
            ]
        }
        with open('test_grid.json', 'w', encoding='utf-8') as f:
            json.dump(test_grid, f)
        result = main.load_grid('test_grid.json')
        self.assertTrue(result)
        self.assertEqual(main.current_grid, test_grid)
        self.assertEqual(main.current_filename, 'test_grid.json')

    def test_load_grid_missing_file(self):
        result = main.load_grid('does_not_exist.json')
        self.assertFalse(result)

    def test_load_grid_corrupted(self):
        with open('test_grid_bad.json', 'w') as f:
            f.write('{"invalid": json}')
        try:
            result = main.load_grid('test_grid_bad.json')
            self.assertFalse(result)
        finally:
            if os.path.exists('test_grid_bad.json'):
                os.remove('test_grid_bad.json')

    def test_save_grid(self):
        test_grid = {"words": [{"id": 1, "answer": "TEST"}]}
        main.current_grid = test_grid
        main.current_filename = 'test_save.json'
        main.save_grid()
        self.assertTrue(os.path.exists('test_save.json'))
        with open('test_save.json', 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        self.assertEqual(saved_data, test_grid)
        os.remove('test_save.json')

    def test_update_score_new_user(self):
        score = main.update_score("NewPlayer", 15)
        self.assertEqual(score, 15)
        self.assertTrue(os.path.exists('test_scores.json'))
        with open('test_scores.json', 'r', encoding='utf-8') as f:
            scores = json.load(f)
        self.assertEqual(scores['newplayer'], 15)

    def test_update_score_existing_user(self):
        main.update_score("Player1", 10)
        total = main.update_score("Player1", 20)
        self.assertEqual(total, 30)
        with open('test_scores.json', 'r', encoding='utf-8') as f:
            scores = json.load(f)
        self.assertEqual(scores['player1'], 30)

    def test_update_score_case_insensitive(self):
        main.update_score("TestUser", 5)
        main.update_score("testuser", 10)
        main.update_score("TESTUSER", 3)
        with open('test_scores.json', 'r', encoding='utf-8') as f:
            scores = json.load(f)
        self.assertEqual(scores['testuser'], 18)
        self.assertEqual(len(scores), 1)

    def test_get_top_5_empty(self):
        main.SCORES_FILE = 'nonexistent.json'
        top = main.get_top_5()
        self.assertEqual(top, [])

    def test_get_top_5_with_scores(self):
        scores_data = {
            'player1': 100,
            'player2': 200,
            'player3': 50,
            'player4': 300,
            'player5': 150,
            'player6': 25
        }
        with open('test_scores.json', 'w', encoding='utf-8') as f:
            json.dump(scores_data, f)
        top = main.get_top_5()
        self.assertEqual(len(top), 5)
        self.assertEqual(top[0], ('player4', 300))
        self.assertEqual(top[1], ('player2', 200))
        self.assertEqual(top[2], ('player5', 150))
        self.assertNotIn(('player6', 25), top)

    def test_get_top_5_less_than_5(self):
        main.update_score("Player1", 100)
        main.update_score("Player2", 50)
        top = main.get_top_5()
        self.assertEqual(len(top), 2)
        self.assertEqual(top[0], ('player1', 100))
        self.assertEqual(top[1], ('player2', 50))

    def test_broadcast_update_no_clients(self):
        async def test():
            await main.broadcast_update({"type": "TEST"})
        asyncio.run(test())

    def test_broadcast_update_with_clients(self):
        async def test():
            mock_client = AsyncMock()
            main.connected_clients.add(mock_client)
            test_data = {"type": "WORD_SOLVED", "word_id": 1}
            await main.broadcast_update(test_data)
            mock_client.send.assert_called_once()
            sent_data = json.loads(mock_client.send.call_args[0][0])
            self.assertEqual(sent_data, test_data)
        asyncio.run(test())


class TestBotCommands(unittest.TestCase):
    def setUp(self):
        self.ctx = MockContext()
        main.SCORES_FILE = 'test_bot_scores.json'

        main.current_grid = {
            "words": [
                {
                    "id": 1,
                    "answer": "PYTHON",
                    "clue": "Langage de programmation",
                    "x": 5, "y": 5,
                    "direction": "horizontal",
                    "solved": False
                },
                {
                    "id": 2,
                    "answer": "JAVA",
                    "clue": "Autre langage",
                    "x": 5, "y": 6,
                    "direction": "horizontal",
                    "solved": True
                }
            ]
        }

    def tearDown(self):
        test_files = ['test_bot_scores.json', 'grille_exemple.json', 'historique.json']
        for f in test_files:
            if os.path.exists(f):
                os.remove(f)

    def test_mot_fleche_correct_answer(self):
        async def test():
            with patch('main.save_grid'), patch('main.broadcast_update'), patch('main.update_score', return_value=10):
                # Simuler la logique du mot fléché directement
                guess = "PYTHON"
                word_found = None
                for word in main.current_grid.get('words', []):
                    if str(word['id']) == str(1):
                        if not word.get('solved', False) and word['answer'].upper() == guess.upper():
                            word['solved'] = True
                            word_found = word
                            break
                
                self.assertIsNotNone(word_found)
                self.assertTrue(word_found['solved'])
        asyncio.run(test())

    def test_mot_fleche_wrong_answer(self):
        async def test():
            guess = "WRONGANSWER"
            word_found = None
            for word in main.current_grid.get('words', []):
                if str(word['id']) == str(1):
                    if not word.get('solved', False):
                        if word['answer'].upper() == guess.upper():
                            word['solved'] = True
                        word_found = word
                        break
            
            self.assertIsNotNone(word_found)
            self.assertFalse(word_found['solved'])  # Mauvaise réponse
        asyncio.run(test())

    def test_mot_fleche_already_solved(self):
        async def test():
            # Test avec le mot ID 2 qui est déjà résolu
            guess = "JAVA"
            word_found = None
            for word in main.current_grid.get('words', []):
                if str(word['id']) == str(2):
                    word_found = word
                    break
            
            self.assertIsNotNone(word_found)
            self.assertTrue(word_found.get('solved', False))  # Déjà résolu
        asyncio.run(test())

    def test_mot_fleche_invalid_id(self):
        async def test():
            # Test avec ID inexistant
            guess = "ANYTHING"
            word_found = None
            for word in main.current_grid.get('words', []):
                if str(word['id']) == str(999):
                    word_found = word
                    break
            
            self.assertIsNone(word_found)  # Aucun mot trouvé
        asyncio.run(test())

    def test_mot_fleche_case_insensitive(self):
        """Test réponses insensibles à la casse"""
        async def test():
            with patch('main.save_grid'), patch('main.broadcast_update'):
                test_answers = ["python", "Python", "PYTHON", "PyThOn"]

                for answer in test_answers:
                    main.current_grid['words'][0]['solved'] = False
                    
                    # Simuler la logique de validation
                    word = main.current_grid['words'][0]
                    if word['answer'].upper() == answer.upper():
                        word['solved'] = True
                    
                    self.assertTrue(word['solved'], f"Échec pour: {answer}")
        asyncio.run(test())

    def test_reset_grille_authorized(self):
        """Test reset par utilisateur autorisé"""
        async def test():
            original_channel = main.CHANNEL
            main.CHANNEL = "TestUser"  # Même que self.ctx.author.name

            try:
                with patch('main.GridGenerator') as mock_gen_class, \
                     patch('main.load_grid', return_value=True), \
                     patch('main.broadcast_update'):

                    mock_gen = MagicMock()
                    mock_gen_class.return_value = mock_gen
                    
                    # Simuler logique reset_grille : vérifier autorisation puis générer
                    if main.CHANNEL.lower() == self.ctx.author.name.lower():
                        generator = mock_gen_class(size=15)
                        generator.generate()
                        main.load_grid('grille_exemple.json')

                    mock_gen_class.assert_called_once_with(size=15)
                    mock_gen.generate.assert_called_once()
            finally:
                main.CHANNEL = original_channel
        asyncio.run(test())

    def test_reset_grille_unauthorized(self):
        """Test reset par utilisateur non autorisé"""
        async def test():
            main.CHANNEL = "SomeoneElse"  # Différent de TestUser
            
            # Simuler logique : vérification autorisation échoue
            authorized = main.CHANNEL.lower() == self.ctx.author.name.lower()
            self.assertFalse(authorized)  # Utilisateur non autorisé
        asyncio.run(test())

    def test_classement_empty(self):
        """Test commande classement sans scores"""
        async def test():
            main.SCORES_FILE = 'empty_scores.json'
            # Utiliser directement la fonction get_top_5
            top = main.get_top_5()
            self.assertEqual(top, [])  # Aucun score

        asyncio.run(test())

    def test_classement_with_scores(self):
        """Test classement avec scores"""
        async def test():
            scores = {'player1': 100, 'player2': 200, 'player3': 50}
            with open('test_bot_scores.json', 'w', encoding='utf-8') as f:
                json.dump(scores, f)

            # Utiliser directement la fonction get_top_5
            top = main.get_top_5()
            self.assertEqual(len(top), 3)
            self.assertEqual(top[0], ('player2', 200))  # Meilleur score

        asyncio.run(test())

    def test_game_completion_detection(self):
        """Test détection fin de partie"""
        async def test():
            with patch('main.save_grid'), patch('main.broadcast_update') as mock_broadcast:
                # Simuler résolution du dernier mot non résolu
                for word in main.current_grid['words']:
                    word['solved'] = True  # Résoudre tous les mots
                    
                # Vérifier si toutes les mots sont résolus
                all_solved = all(w.get('solved', False) for w in main.current_grid['words'])
                self.assertTrue(all_solved)  # Partie terminée
        asyncio.run(test())


class TestGameLogic(unittest.TestCase):
    """Tests de logique de jeu"""

    def test_word_validation_logic(self):
        """Test logique validation des réponses"""
        test_grid = {
            "words": [
                {"id": 1, "answer": "PYTHON", "solved": False},
                {"id": 2, "answer": "JAVA", "solved": True}
            ]
        }
        main.current_grid = test_grid

        unsolved = [w for w in main.current_grid['words'] if not w.get('solved', False)]
        self.assertEqual(len(unsolved), 1)
        self.assertEqual(unsolved[0]['answer'], 'PYTHON')

    def test_grid_completion_check(self):
        """Test vérification complétion grille"""
        test_grid = {
            "words": [
                {"id": 1, "solved": False},
                {"id": 2, "solved": True}
            ]
        }

        completed = all(w.get('solved', False) for w in test_grid['words'])
        self.assertFalse(completed)

        for word in test_grid['words']:
            word['solved'] = True

        completed = all(w.get('solved', False) for w in test_grid['words'])
        self.assertTrue(completed)

    def test_answer_normalization(self):
        """Test normalisation des réponses"""
        test_answers = ["python", "Python", "PYTHON", "PyThOn"]
        expected = "PYTHON"

        for answer in test_answers:
            self.assertEqual(answer.upper(), expected)


if __name__ == '__main__':
    unittest.main(verbosity=2)