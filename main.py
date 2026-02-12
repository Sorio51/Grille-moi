import asyncio
import json
import websockets
from twitchio.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('TWITCH_TOKEN')
CHANNEL = os.getenv('TWITCH_CHANNEL')
WS_PORT = 8765

# On garde trace du fichier actuel pour les sauvegardes
current_filename = 'grille_exemple.json'
current_grid = {}
connected_clients = set()

def load_grid(filename):
    global current_grid, current_filename
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            current_grid = json.load(f)
        current_filename = filename
        print(f"Grille chargée : {current_grid['title']} ({filename})")
        return True
    except Exception as e:
        print(f"Erreur lors du chargement de {filename}: {e}")
        return False

def save_grid():
    """Sauvegarde l'état actuel (mots résolus) dans le fichier JSON"""
    with open(current_filename, 'w', encoding='utf-8') as f:
        json.dump(current_grid, f, indent=2, ensure_ascii=False)
    print(f"Progression sauvegardée dans {current_filename}")

async def websocket_handler(websocket):
    connected_clients.add(websocket)
    try:
        # Envoi de la grille au chargement de l'overlay
        await websocket.send(json.dumps({"type": "INIT", "grid": current_grid}))
        async for message in websocket:
            pass
    finally:
        connected_clients.remove(websocket)

async def broadcast_update(data):
    if connected_clients:
        message = json.dumps(data)
        await asyncio.gather(*[client.send(message) for client in connected_clients])

class Bot(commands.Bot):
    def __init__(self):
        super().__init__(token=TOKEN, prefix='!', initial_channels=[CHANNEL])

    async def event_ready(self):
        print(f"Bot en ligne | Salon: {CHANNEL}")

    async def event_message(self, message):
        if message.echo: return
        await self.handle_commands(message)

    @commands.command(name='mf')
    async def mot_fleche(self, ctx: commands.Context, num: int, guess: str):
        guess = guess.upper()
        for word in current_grid['words']:
            if str(word['id']) == str(num):
                if word.get('solved', False):
                    await ctx.send(f"@{ctx.author.name}, le n°{num} est déjà trouvé !")
                    return

                if word['answer'].upper() == guess:
                    word['solved'] = True
                    save_grid()
                    await ctx.send(f"Bravo @{ctx.author.name} ! '{guess}' est correct !")
                    
                    # Update Overlay
                    await broadcast_update({"type": "WORD_SOLVED", "word_id": num, "answer": guess})
                    
                    # Vérifier si c'est la fin de la grille
                    if all(w.get('solved', False) for w in current_grid['words']):
                        await ctx.send(f"🏆 GRILLE TERMINÉE ! Bien joué tout le monde !")
                        await broadcast_update({"type": "VICTORY"})
                else:
                    await ctx.send(f"Non @{ctx.author.name}, ce n'est pas ça.")
                return

    @commands.command(name='grille')
    async def change_grid(self, ctx: commands.Context, filename: str):
        # Seul le streamer peut changer de grille
        if ctx.author.name.lower() != CHANNEL.lower():
            return

        if not filename.endswith('.json'):
            filename += '.json'
            
        if load_grid(filename):
            await broadcast_update({"type": "INIT", "grid": current_grid})
            await ctx.send(f"Nouvelle grille chargée : {current_grid['title']}")
        else:
            await ctx.send(f"Fichier {filename} introuvable.")

async def main():
    load_grid('grille_exemple.json')
    server = await websockets.serve(websocket_handler, "localhost", WS_PORT)
    bot = Bot()
    await asyncio.gather(server.wait_closed(), bot.start())

if __name__ == "__main__":
    asyncio.run(main())