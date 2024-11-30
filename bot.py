from espn_api.basketball import League
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, Application

# Substitua pelos valores da sua liga
LEAGUE_ID = 438866  # ID da liga (número)
YEAR = 2025         # Ano da temporada
ESPN_S2 = "AEBiL%2F4MN0OVO6Zb%2Bt2vetoNRBgVWmzgP8zEbt7i6%2Fh9lmA0SfHNRm3kpKN%2BmgNzbIqihzk7yS%2Byx7aHzht3J7CzLp%2F9XpMYtIrXllr2hnabouU0aOIk4grniKnNKa4taHZDI13WAsew430Yw90I5m%2BM%2BVuyQ0lb0q6%2Bbs89f2E5ydl9sOim8%2Buh4NE%2FUYy%2FlEFj5AZk62fyP1w8u0OxFwe5o2knGtXAdKwwAyRARyAC1wDlq5wN%2FUwZOIqTLdtfT1Xgepxty%2FmCMgs%2BD7%2FTLhtqDPbZUB6%2BqpY92FX8u08kQaC8jNZDWKiGoX1kjAsINTo%3D"
SWID = "{0D2052B4-FEB7-43C7-8200-BF8D96BEED2E}"  # Inclua as chaves {}
TOKEN = "7734107392:AAF4_oniWP8k-1dCk4D0j2-vv2CcmnpSfG4"

# Inicializa a liga ESPN
league = League(league_id=LEAGUE_ID, year=YEAR, espn_s2=ESPN_S2, swid=SWID)

async def compare(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        if len(context.args) < 1:
            await update.message.reply_text("❌ Informe o nome do time. Exemplo: /compare Fulano 1;Fulano 2")
            return

        jogador_name = " ".join(context.args)
        jogador_name = jogador_name.split(";")

        if len(jogador_name) > 1:
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

            if jogadores_lista:
                await update.message.reply_text(jogadores_lista)
            else:
                await update.message.reply_text("❌ Não foi possível encontrar os dados dos jogadores.")
        else:
            await update.message.reply_text("❌ Por favor, informe mais de um jogador usando `;` como separador.")
    except Exception as e:
        await update.message.reply_text(f"❌ Erro ao buscar informações do time: {str(e)}")

# Comando para buscar informações de um time específico
async def team_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        if len(context.args) < 1:
            await update.message.reply_text("❌ Informe o nome do time. Exemplo: /teaminfo Lakers")
            return

        team_name = " ".join(context.args)
        team = next((t for t in league.teams if team_name.lower() in t.team_name.lower()), None)

        if team:
            owner = team.owners[0]
            response = f"📋 Informações do Time: {team.team_name}\n"
            response += f"Proprietário: {owner['firstName'] + " " + owner['lastName']}\n"
            response += f"Vitórias: {team.wins}, Derrotas: {team.losses}\n"
            response += "Jogadores:\n"
            for player in team.roster:
                response += f"- {player.name} ({player.position})\n"
            await update.message.reply_text(response)
        else:
            await update.message.reply_text("❌ Time não encontrado.")
    except Exception as e:
        await update.message.reply_text(f"❌ Erro ao buscar informações do time: {str(e)}")

# Função para iniciar o bot
def main():
    # Cria a aplicação do Telegram
    application = ApplicationBuilder().token(TOKEN).build()

    # Configura os comandos do bot
    application.add_handler(CommandHandler("teaminfo", team_info))
    application.add_handler(CommandHandler("stats", compare))

    # Inicia o bot
    print("Bot iniciado. Pressione Ctrl+C para parar.")
    application.run_polling(stop_signals=None)

if __name__ == "__main__":
    main()