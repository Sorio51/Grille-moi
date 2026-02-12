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

current_grid = {}
connected_clients = set()

def load_grid():
    global current_grid
    try:
        with open('grille_exemple.json', 'r', encoding='utf-8') as f:
            current_grid = json.load(f)
        print(f"Grille chargée : {current_grid['title']}")
    except FileNotFoundError:
        print("Erreur : Fichier grille_exemple.json introuvable.")

def save_grid():
    """Sauvegarde l'état actuel de la grille dans le fichier JSON"""
    with open('grille_exemple.json', 'w', encoding='utf-8') as f:
        json.dump(current_grid, f, indent=2, ensure_ascii=False)
    print("Progression sauvegardée dans le JSON.")

async def websocket_handler(websocket):
    """Gère la connexion avec l'Overlay OBS"""
    connected_clients.add(websocket)
    try:
        # Envoie la grille actuelle dès la connexion
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
        print(f"Bot connecté : {self.nick}")
        print(f"Salon actif : {CHANNEL}")
        print('-----------------------------------')

    async def event_message(self, message):
        if message.echo:
            return
        print(f"CHAT [{message.author.name}]: {message.content}")
        await self.handle_commands(message)

    @commands.command(name='mf')
    async def mot_fleche(self, ctx: commands.Context, num: int, guess: str):
        guess = guess.upper()
        found = False
        
        for word in current_grid['words']:
            if str(word['id']) == str(num):
                found = True
                # Vérifier si déjà résolu
                if word.get('solved', False):
                    await ctx.send(f"@{ctx.author.name}, le mot n°{num} est déjà validé !")
                    return

                # Vérifier la réponse
                if word['answer'].upper() == guess:
                    word['solved'] = True
                    save_grid() # Sauvegarde immédiate
                    
                    await ctx.send(f"Bravo @{ctx.author.name} ! {guess} est correct !")
                    await broadcast_update({
                        "type": "WORD_SOLVED",
                        "word_id": num,
                        "answer": guess
                    })
                else:
                    await ctx.send(f"@{ctx.author.name}, ce n'est pas ça pour le n°{num}.")
                return
        
        if not found:
            await ctx.send(f"@{ctx.author.name}, le numéro {num} n'existe pas sur cette grille.")

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