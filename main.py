import nest_asyncio
nest_asyncio.apply()

import asyncio
from fastapi import FastAPI, Request, HTTPException
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, ContextTypes
from espn_api.basketball import League
import logging
import os
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from asyncio import Lock

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

telegram_app = None
telegram_app_lock = Lock()
loop = asyncio.get_event_loop()

async def compare(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        if not context.args:
            await update.message.reply_text("❌ Informe o nome do time. Exemplo: /stats Fulano 1;Fulano 2")
            return

        jogador_names = [name.strip().lower() for name in " ".join(context.args).split(";")]
        jogadores_encontrados = [
            rt
            for team in league.teams
            for rt in team.roster
            if any(name in rt.name.lower() for name in jogador_names)
        ]

        if not jogadores_encontrados:
            await update.message.reply_text("❌ Nenhum jogador encontrado.")
            return

        jogadores_lista = f'Stats {YEAR} Antas\n\n' + "\n".join(
            f"{jogador.name}\n📋 AVG: {jogador.avg_points}\n📋 Total Points: {jogador.total_points}"
            for jogador in jogadores_encontrados
        )

        await update.message.reply_text(jogadores_lista)
    except Exception as e:
        logger.error(f"Erro ao processar webhook de jogador: {e}", exc_info=True)
        try:
            await update.message.reply_text(f"❌ Erro ao buscar informações do jogador: {str(e)}")
        except Exception as reply_error:
            logger.error(f"Erro ao enviar mensagem de erro: {reply_error}", exc_info=True)

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
            return await update.message.reply_text(response)
        else:
            return await update.message.reply_text("❌ Time não encontrado.")
    except Exception as e:
        logger.error(f"Erro ao processar webhook de time: {e}")
        return await update.message.reply_text(f"❌ Erro ao buscar informações do time: {str(e)}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    return await update.message.reply_text("Olá, meus comandos são: \n\n"
                                           "/stats jogador1;jogador2;jogador3;jogador4\n\n"
                                           "/teaminfo time_aqui\n\n"
                                           "/criterio entenda como mensuramos os critérios.\n\n"
                                           "/trade Valor total media A Valor total media B")


async def criterio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    return await update.message.reply_text("Então, para avaliar se uma trade é honesta, usamos os seguintes critérios:\n\n"
                                           "1. Se a média for entre 10-20, a diferença deve ser igual ou menor a 5.\n"
                                           "2. Se a média for entre 20-30, a diferença deve ser igual ou menor a 8.\n"
                                           "3. Se a média for 40 ou mais, a diferença deve ser igual ou menor a 10.\n\n"
                                           "Se as duas médias forem iguais, é uma trade aceitável. Lembrando que ainda "
                                           "assim o regulamento e a comissão vão avaliar outros fatores além da média.")

async def trade(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    if len(context.args) < 2:
        await update.message.reply_text("❌ Informe Valor total media A Valor total media B")
        return

    valor1 = int(context.args[0])
    valor2 = int(context.args[1])
    media = (valor1 + valor2) / 2
    diferenca = abs(valor1 - valor2)
    
    if valor1 == valor2:
        return await update.message.reply_text(f"TRADE APROVADA: Médias iguais ({valor1}).")
    elif 10 <= media < 20 and diferenca <= 5:
        return await update.message.reply_text(f"TRADE APROVADA: diferença de {diferenca:.1f}. Critério atendido!")
    elif 20 <= media < 30 and diferenca <= 8:
        return await update.message.reply_text(f"TRADE APROVADA: diferença de {diferenca:.1f}. Critério atendido!")
    elif media >= 40 and diferenca <= 10:
        return await update.message.reply_text(f"TRADE APROVADA: diferença de {diferenca:.1f}. Critério atendido!")
    else:
        return await update.message.reply_text(f"TRADE REPROVADA: diferença de {diferenca:.1f}. Melhor ajustar as médias!")

async def error_handler(update, context):
    print(f"Erro: {context.error}")
    logger.error(f"Erro ao processar webhook: {context.error}")
    return None

async def get_telegram_app(loop=None):
    global telegram_app
    if loop is None:
        loop = asyncio.get_event_loop()
    
    async with telegram_app_lock:
        if telegram_app is None:
            telegram_app = (
                Application.builder()
                .token(TOKEN)
                .updater(None)
                .build()
            )
            await telegram_app.bot.set_my_commands([
                BotCommand("start", "mostrar comando e iniciar bot"),
                BotCommand("stats", "Exibir AVG e TotalPoints do jogador ou varios jogadores ( /stats maxey;embiid ). Separe os jogadores por ; sem espaçamento entre eles."),
                BotCommand("teaminfo", "Mostrar informações do time"),
                BotCommand("criterio", "Critério para avaliar a troca."),
                BotCommand("trade", "Avaliar a média, se está reprovada ou não."),
            ])
            telegram_app.add_handler(CommandHandler("stats", compare))
            telegram_app.add_handler(CommandHandler("teaminfo", team_info))
            telegram_app.add_handler(CommandHandler("start", start))
            telegram_app.add_handler(CommandHandler("criterio", criterio))
            telegram_app.add_handler(CommandHandler("trade", trade))
            telegram_app.add_error_handler(error_handler)
            await telegram_app.initialize()
        return telegram_app

@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()

        # Usar o loop de eventos atual
        tg_app = await get_telegram_app(loop)
        
        update = Update.de_json(data, tg_app.bot)

        if update:
            await tg_app.process_update(update)
        
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Erro ao processar webhook: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail="Erro ao processar webhook")

@app.on_event("startup")
async def startup():
    try:
        tg_app = await get_telegram_app(loop)
        await tg_app.bot.delete_webhook(drop_pending_updates=True)
        await tg_app.bot.set_webhook(
            url=WEBHOOK_URL,
            allowed_updates=Update.ALL_TYPES
        )
        logger.info(f"Webhook set to {WEBHOOK_URL}")
    except Exception as e:
        logger.error(f"Startup error: {e}", exc_info=True)

@app.get("/")
async def health_check():
    return {"status": "running"}

async def main():
    application = await get_telegram_app(loop)
    try:
        await application.run_polling()
    finally:
        await application.stop()

if __name__ == "__main__":
    asyncio.run(main())