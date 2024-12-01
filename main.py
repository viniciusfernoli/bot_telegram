from typing import Optional
from fastapi import FastAPI, Request, HTTPException
from telegram import Update,Bot
from telegram.ext import Application, CommandHandler, ContextTypes,Dispatcher
from espn_api.basketball import League
import logging
import os
from pydantic import BaseModel

# Configurações de log
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configurações da liga e do bot
LEAGUE_ID = os.getenv("LEAGUE_ID", "438866")
YEAR = os.getenv("YEAR", "2025")
ESPN_S2 = os.getenv("ESPN_S2", "AEBiL%2F4MN0OVO6Zb%2Bt2vetoNRBgVWmzgP8zEbt7i6%2Fh9lmA0SfHNRm3kpKN%2BmgNzbIqihzk7yS%2Byx7aHzht3J7CzLp%2F9XpMYtIrXllr2hnabouU0aOIk4grniKnNKa4taHZDI13WAsew430Yw90I5m%2BM%2BVuyQ0lb0q6%2Bbs89f2E5ydl9sOim8%2Buh4NE%2FUYy%2FlEFj5AZk62fyP1w8u0OxFwe5o2knGtXAdKwwAyRARyAC1wDlq5wN%2FUwZOIqTLdtfT1Xgepxty%2FmCMgs%2BD7%2FTLhtqDPbZUB6%2BqpY92FX8u08kQaC8jNZDWKiGoX1kjAsINTo%3D")
SWID = os.getenv("SWID", "{0D2052B4-FEB7-43C7-8200-BF8D96BEED2E}")
TOKEN = os.getenv("TELEGRAM_TOKEN", "7734107392:AAF4_oniWP8k-1dCk4D0j2-vv2CcmnpSfG4")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://daef-179-104-25-151.ngrok-free.app/webhook")  # Ex: https://seuapp.vercel.app/webhook
# WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://bot-telegram-vert-sigma.vercel.app/webhook")  # Ex: https://seuapp.vercel.app/webhook

# Inicializa a liga ESPN
league = League(league_id=int(LEAGUE_ID), year=int(YEAR), espn_s2=ESPN_S2, swid=SWID)

# Inicializa o bot do Telegram
telegram_app = Application.builder().token(TOKEN).build()

# Inicializa a aplicação FastAPI
app = FastAPI()
class TelegramWebhook(BaseModel):
    '''
    Telegram Webhook Model using Pydantic for request body validation
    '''
    update_id: int
    message: Optional[dict]
    edited_message: Optional[dict]
    channel_post: Optional[dict]
    edited_channel_post: Optional[dict]
    inline_query: Optional[dict]
    chosen_inline_result: Optional[dict]
    callback_query: Optional[dict]
    shipping_query: Optional[dict]
    pre_checkout_query: Optional[dict]
    poll: Optional[dict]
    poll_answer: Optional[dict]

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
    await update.message.reply_text("Olá, meus comandos são: \n\n/stats maxey;embiid!\n\n/teaminfo time_aqui")


def register_handlers(dispatcher):
    start_handler = CommandHandler('start', start)
    stats_handler = CommandHandler("stats", compare)
    teaminfo_handler = CommandHandler("teaminfo", team_info)
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(stats_handler)
    dispatcher.add_handler(teaminfo_handler)
    

# Endpoint do Webhook
@app.post("/webhook")
async def webhook(webhook_data: TelegramWebhook):
    try:
        bot = Bot(token=TOKEN)
        update = Update.de_json(webhook_data.__dict__, bot)
        dispatcher = Dispatcher(bot, None, workers=4)
        register_handlers(dispatcher)
        dispatcher.process_update(update)

        return {"message": "ok"}
    
    except Exception as e:
        logger.error(f"Erro ao processar webhook: {e}")
        raise HTTPException(status_code=400, detail="Erro ao processar webhook")

# Endpoint para testar a saúde da aplicação
@app.get("/")
async def health_check():
    return {"status": "running"}