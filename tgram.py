import io
import os
from telegram import Bot


async def enviar_notificacao(mensagem: str):
    """
    Envia uma mensagem para o grupo do Telegram.

    Args:
        mensagem (str): Mensagem a ser enviada ao Telegram.
    """
    token = os.getenv('TELEGRAM_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHATID')
    if not token or not chat_id:
        print("Telegram token ou chat ID não encontrado nas variáveis de ambiente")
        return

    bot = Bot(token=token)
    async with bot:
        try:
            await bot.send_message(chat_id=chat_id, text=f"YTMusicDL -\n{mensagem}")
        except Exception as e:
                print(f"Erro ao enviar mensagem para o Telegram: {e}")


async def enviar_stream(stream: io.BytesIO, nome_arquivo: str):
    """
    Envia o arquivo para o grupo do Telegram.

    Args:
        stream (io.BytesIO): Stream de dados do arquivo.
        nome_arquivo (str): Nome do arquivo a ser enviado ao Telegram.
    """
    token = os.getenv('TELEGRAM_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHATID')
    if not token or not chat_id:
        print("Telegram token ou chat ID não encontrado nas variáveis de ambiente")
        return

    bot = Bot(token=token)
    async with bot:
        try:
            await bot.send_document(
                chat_id=chat_id,
                document=stream,
                filename=nome_arquivo,
                disable_notification=True
            )
        except Exception as e:
            print(f"Erro ao enviar arquivo para o Telegram: {e}")
