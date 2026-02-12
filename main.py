import asyncio
import json
import websockets
from twitchio.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('TWITCH_TOKEN')
CHANNEL = os.getenv('TWITCH_CHANNEL')
CLIENT_ID = os.getenv('TWITCH_CLIENT_ID')
CLIENT_SECRET = os.getenv('TWITCH_CLIENT_SECRET')
BOT_ID = os.getenv('TWITCH_BOT_ID')
WS_PORT = 8765

current_grid = {}
connected_clients = set()

def load_grid():
    global current_grid
    with open('grille_exemple.json', 'r', encoding='utf-8') as f:
        current_grid = json.load(f)
    print(f"Grille chargée : {current_grid['title']}")

async def websocket_handler(websocket):
    """Gère la connexion avec l'Overlay OBS"""
    connected_clients.add(websocket)
    try:
        await websocket.send(json.dumps({"type": "INIT", "grid": current_grid}))
        await websocket.wait_closed()
    finally:
        connected_clients.remove(websocket)

async def broadcast_update(data):
    """Envoie des mises à jour à tous les overlays connectés"""
    if connected_clients:
        message = json.dumps(data)
        await asyncio.gather(*[client.send(message) for client in connected_clients])

class Bot(commands.Bot):
    def __init__(self):
        super().__init__(
            token=TOKEN,
            prefix='!',
            initial_channels=[CHANNEL]
        )

    async def event_ready(self):
        print('-----------------------------------')
        print(f"Connecté en tant que {self.nick}")
        print(f"Channels: {self.connected_channels}")
        print('-----------------------------------')

    async def event_message(self, message):
        if message.echo:
            return

        print(f"CHAT [{message.author.name}]: {message.content}")
        await self.handle_commands(message)


    @commands.command(name='mf')
    async def mot_fleche(self, ctx: commands.Context, num: int, guess: str):
        print(f"COMMANDE REÇUE : !mf {num} {guess}")
        guess = guess.upper()
        
        for word in current_grid['words']:
            # On compare en texte pour éviter les erreurs de type (1 vs "1")
            if str(word['id']) == str(num):
                if word['answer'].upper() == guess:
                    word['solved'] = True
                    await ctx.send(f"Bravo @{ctx.author.name} ! {guess} est correct !")
                    await broadcast_update({
                        "type": "WORD_SOLVED",
                        "word_id": num,
                        "answer": guess
                    })
                else:
                    await ctx.send(f"@{ctx.author.name}, ce n'est pas ça.")
                return

async def main():
    load_grid()
    print(f"Serveur Overlay démarré sur le port {WS_PORT}")
    server = await websockets.serve(websocket_handler, "localhost", WS_PORT)

    bot = Bot()
    print("Démarrage du Bot Twitch...")

    await asyncio.gather(server.wait_closed(), bot.start())

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Arrêt du programme.")