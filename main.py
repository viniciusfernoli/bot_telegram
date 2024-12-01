from fastapi import FastAPI, Request, HTTPException
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from espn_api.basketball import League
import logging
import os
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

origins = [
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Permitir origens específicas
    allow_credentials=True, # Permitir envio de cookies/sessões
    allow_methods=["*"],    # Permitir todos os métodos HTTP (GET, POST, etc.)
    allow_headers=["*"],    # Permitir todos os headers
)


# Configurações de log
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()

# Configurações da liga e do bot
LEAGUE_ID = os.environ.get("LEAGUE_ID")
YEAR = os.environ.get("YEAR")
ESPN_S2 = os.environ.get("ESPN_S2")
TOKEN = os.environ.get("TELEGRAM_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
SWID = os.environ.get("SWID")


# Inicializa a liga ESPN
league = League(league_id=int(LEAGUE_ID), year=int(YEAR), espn_s2=ESPN_S2, swid=SWID)

# Inicializa o bot do Telegram
telegram_app = Application.builder().token(TOKEN).build()

# Comando para comparar jogadores
async def compare(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        if len(context.args) < 1:
            await update.message.reply_text("❌ Informe o nome do time. Exemplo: /compare Fulano 1;Fulano 2")
            return

        jogador_name = " ".join(context.args).split(";")
        jogadores_lista = f'Stats {YEAR} Antas\n\n'
        jogadores_encontrados = []

        for team in league.teams:
            for name in jogador_name:
                for rt in team.roster:
                    if name.strip().lower() in rt.name.lower():
                        jogadores_encontrados.append(rt)

        if not jogadores_encontrados:
            await update.message.reply_text("❌ Nenhum jogador encontrado.")
            return

        for jogador in jogadores_encontrados:
            jogadores_lista += f"{jogador.name}\n"
            jogadores_lista += f"📋 AVG: {jogador.avg_points}\n"
            jogadores_lista += f"📋 Total Points: {jogador.total_points}\n\n"

        await update.message.reply_text(jogadores_lista if jogadores_lista else "❌ Não foi possível encontrar os dados dos jogadores.")
    except Exception as e:
        await update.message.reply_text(f"❌ Erro ao buscar informações do time: {str(e)}")

# Comando para informações de um time
async def team_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        if len(context.args) < 1:
            await update.message.reply_text("❌ Informe o nome do time. Exemplo: /teaminfo Lakers")
            return

        team_name = " ".join(context.args)
        team = next((t for t in league.teams if team_name.lower() in t.team_name.lower()), None)

        if team:
            owner = team.owners[0]
            response = (f"📋 Informações do Time: {team.team_name}\n"
                        f"Proprietário: {owner['firstName']} {owner['lastName']}\n"
                        f"Vitórias: {team.wins}, Derrotas: {team.losses}\nJogadores:\n")
            response += "".join(f"- {player.name} ({player.position})\n" for player in team.roster)
            await update.message.reply_text(response)
        else:
            await update.message.reply_text("❌ Time não encontrado.")
    except Exception as e:
        await update.message.reply_text(f"❌ Erro ao buscar informações do time: {str(e)}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Olá, meus comandos são: \n\n/stats maxey;embiid\n\n/teaminfo time_aqui")


telegram_app.add_handler(CommandHandler("stats", compare))
telegram_app.add_handler(CommandHandler("teaminfo", team_info))
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.initialize()

# Endpoint do Webhook
@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        update = Update.de_json(data, telegram_app.bot)
        if update:
            await telegram_app.process_update(update)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Erro ao processar webhook: {e}")
        print(f"Erro ao processar webhook: {e}")
        raise HTTPException(status_code=400, detail="Erro ao processar webhook")

# Endpoint para configuração do Webhook
@app.on_event("startup")
async def startup():
    try:
        await telegram_app.bot.delete_webhook(drop_pending_updates=True)
        await telegram_app.bot.set_webhook(
            url=WEBHOOK_URL, 
            allowed_updates=Update.ALL_TYPES
        )
        logger.info(f"Webhook set to {WEBHOOK_URL}")
    except Exception as e:
        print(f"Startup error: {e}")
        logger.error(f"Startup error: {e}", exc_info=True)

# Endpoint para testar a saúde da aplicação
@app.get("/")
async def health_check():
    return {"status": "running"}