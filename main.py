import os
import json
import asyncio
import websockets
import random
from dotenv import load_dotenv
from twitchio.ext import commands
from generator import GridGenerator

load_dotenv()

TOKEN = os.getenv('TWITCH_TOKEN')
CHANNEL = os.getenv('TWITCH_CHANNEL')
WS_PORT = 8765
SCORES_FILE = 'scores.json'

current_filename = 'grille_exemple.json'
current_grid = {}
connected_clients = set()

def load_grid(filename):
    global current_grid, current_filename
    try:
        if not os.path.exists(filename):
            return False
        with open(filename, 'r', encoding='utf-8') as f:
            current_grid = json.load(f)
        current_filename = filename
        print(f"Grille chargée : {current_filename}")
        return True
    except Exception as e:
        print(f"❌ Erreur chargement : {e}")
        return False

def save_grid():
    try:
        with open(current_filename, 'w', encoding='utf-8') as f:
            json.dump(current_grid, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"❌ Erreur sauvegarde : {e}")

def update_score(user_name, points=10):
    scores = {}
    if os.path.exists(SCORES_FILE):
        with open(SCORES_FILE, 'r', encoding='utf-8') as f:
            try: scores = json.load(f)
            except: scores = {}

    user_name = user_name.lower()
    scores[user_name] = scores.get(user_name, 0) + points

    with open(SCORES_FILE, 'w', encoding='utf-8') as f:
        json.dump(scores, f, indent=2, ensure_ascii=False)
    return scores[user_name]

async def broadcast_update(data):
    if connected_clients:
        msg = json.dumps(data)
        await asyncio.gather(*[client.send(msg) for client in connected_clients], return_exceptions=True)

async def websocket_handler(websocket):
    connected_clients.add(websocket)
    try:
        await websocket.send(json.dumps({"type": "INIT", "grid": current_grid}))
        async for message in websocket: pass
    finally:
        connected_clients.remove(websocket)

def get_top_5():
    if not os.path.exists(SCORES_FILE):
        return []
    try:
        with open(SCORES_FILE, 'r', encoding='utf-8') as f:
            scores = json.load(f)
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_scores[:5]
    except:
        return []

class Bot(commands.Bot):
    def __init__(self):
        super().__init__(token=TOKEN, prefix='!', initial_channels=[CHANNEL])

    async def event_ready(self):
        print(f"✅ Bot Twitch connecté : {self.nick}")
        print(f"🚀 Serveur WebSocket sur le port {WS_PORT}")

    async def event_command_error(self, ctx: commands.Context, error):
        """Gestionnaire d'erreurs pour les commandes"""
        from twitchio.ext.commands.errors import MissingRequiredArgument, BadArgument
        if isinstance(error, MissingRequiredArgument):
            if ctx.command.name == 'mf':
                await ctx.send(f"❓ @{ctx.author.name}, utilise : !mf <numéro> <réponse> (ex: !mf 1 PYTHON)")
            else:
                await ctx.send(f"❓ @{ctx.author.name}, arguments manquants pour !{ctx.command.name}")
        elif isinstance(error, BadArgument):
            if ctx.command.name == 'mf':
                await ctx.send(f"❓ @{ctx.author.name}, le numéro doit être un chiffre (ex: !mf 1 PYTHON)")
        else:
            print(f"Erreur commande non gérée: {error}")

    @commands.command(name='mf')
    async def mot_fleche(self, ctx: commands.Context, num: int, guess: str):
        guess = guess.upper()
        for word in current_grid.get('words', []):
            if str(word['id']) == str(num):
                if word.get('solved', False): return
                if word['answer'].upper() == guess:
                    word['solved'] = True
                    save_grid()
                    new_total = update_score(ctx.author.name)
                    await ctx.send(f"✅ @{ctx.author.name} ! +10 pts (Total: {new_total})")

                    await broadcast_update({
                        "type": "WORD_SOLVED",
                        "word_id": num,
                        "answer": guess,
                        "user": ctx.author.name
                    })
                    if all(w.get('solved', False) for w in current_grid['words']):
                        await ctx.send("🏆 Grille terminée ! GG la team !")
                        await broadcast_update({"type": "VICTORY"})
                else:
                    await ctx.send(f"❌ Non @{ctx.author.name}, ce n'est pas ça.")
                return

    @commands.command(name='reset_grille')
    async def reset_grille(self, ctx: commands.Context):
        if ctx.author.name.lower() != CHANNEL.lower(): return
        await ctx.send("⚙️ Génération d'une nouvelle grille...")
        gen = GridGenerator(size=15)
        gen.generate(nb_words=8, min_words=5)

        if load_grid('grille_exemple.json'):
            await broadcast_update({"type": "INIT", "grid": current_grid})
            await ctx.send("✅ Nouvelle grille chargée !")

    @commands.command(name='classement')
    async def classement(self, ctx: commands.Context):
        top = get_top_5()
        if not top:
            await ctx.send("📊 Aucun score enregistré pour le moment.")
            return

        message = "🏆 TOP 5 CLASSEMENT : "
        entries = [f"{i+1}. {user} ({pts}pts)" for i, (user, pts) in enumerate(top)]
        await ctx.send(message + " | ".join(entries))

    @commands.command(name='score')
    async def score(self, ctx: commands.Context):
        """Affiche le score personnel de l'utilisateur"""
        user_name = ctx.author.name.lower()
        if os.path.exists(SCORES_FILE):
            with open(SCORES_FILE, 'r', encoding='utf-8') as f:
                scores = json.load(f)
                user_score = scores.get(user_name, 0)
            await ctx.send(f"📊 @{ctx.author.name}, tu as actuellement {user_score} points !")
        else:
            await ctx.send(f"📊 @{ctx.author.name}, tu n'as pas encore de points.")

async def main():
    if not load_grid('grille_exemple.json'):
        print("📝 Aucune grille trouvée, génération d'une nouvelle grille...")
        gen = GridGenerator(size=15)
        gen.generate(nb_words=8, min_words=5)
        load_grid('grille_exemple.json')
        print("✅ Grille par défaut générée et chargée")

    server = await websockets.serve(websocket_handler, "localhost", WS_PORT)
    bot = Bot()

    try:
        await asyncio.gather(
            server.wait_closed(),
            bot.start()
        )
    except asyncio.CancelledError:
        print("\nArrêt des tâches en cours...")
    finally:
        await bot.close()
        server.close()
        await server.wait_closed()
        print("👋 Bot et serveur arrêtés proprement.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass