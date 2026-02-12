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

current_filename = 'grille_exemple.json'
current_grid = {}
connected_clients = set()

def load_grid(filename):
    global current_grid, current_filename
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            current_grid = json.load(f)
        current_filename = filename
        print(f"Grille chargée : {current_grid['title']}")
        return True
    except Exception as e:
        print(f"Erreur : {e}")
        return False

def save_grid():
    with open(current_filename, 'w', encoding='utf-8') as f:
        json.dump(current_grid, f, indent=2, ensure_ascii=False)

async def websocket_handler(websocket):
    connected_clients.add(websocket)
    try:
        await websocket.send(json.dumps({"type": "INIT", "grid": current_grid}))
        async for message in websocket: pass
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
        print(f"Bot connecté sur {CHANNEL}")

    @commands.command(name='mf')
    async def mot_fleche(self, ctx: commands.Context, num: int, guess: str):
        guess = guess.upper()
        for word in current_grid['words']:
            if str(word['id']) == str(num):
                if word.get('solved', False):
                    await ctx.send(f"Déjà trouvé !")
                    return
                if word['answer'].upper() == guess:
                    word['solved'] = True
                    save_grid()
                    await ctx.send(f"Bravo @{ctx.author.name} ! '{guess}' est correct !")
                    await broadcast_update({"type": "WORD_SOLVED", "word_id": num, "answer": guess})
                    if all(w.get('solved', False) for w in current_grid['words']):
                        await ctx.send("🏆 GRILLE TERMINÉE !")
                        await broadcast_update({"type": "VICTORY"})
                else:
                    await ctx.send(f"Faux @{ctx.author.name} !")
                return

    @commands.command(name='grille')
    async def change_grid(self, ctx: commands.Context, filename: str):
        if ctx.author.name.lower() != CHANNEL.lower(): return
        if not filename.endswith('.json'): filename += '.json'
        if load_grid(filename):
            await broadcast_update({"type": "INIT", "grid": current_grid})
            await ctx.send(f"Nouvelle grille : {current_grid['title']}")

async def main():
    load_grid('grille_exemple.json')
    server = await websockets.serve(websocket_handler, "localhost", WS_PORT)
    bot = Bot()
    await asyncio.gather(server.wait_closed(), bot.start())

if __name__ == "__main__":
    asyncio.run(main())