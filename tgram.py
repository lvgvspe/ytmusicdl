import io
import tomli
from telegram import Bot



with open("telegram.toml", mode="rb") as fp:
    configs = tomli.load(fp)

async def enviar_notificacao(mensagem: str):
    """
    Envia uma mensagem para o grupo do Telegram.

    Args:
        mensagem (str): Mensagem a ser enviada ao Telegram.
    """
    bot = Bot(token=configs['telegram']['token'])
    async with bot:
        await bot.send_message(chat_id=configs['telegram']['chatid'], text=f"YTMusicDL -\n{mensagem}")

async def enviar_stream(stream: io.BytesIO, nome_arquivo: str):
    """
    Envia o arquivo para o grupo do Telegram.

    Args:
        stream (io.BytesIO): Stream de dados do arquivo.
        nome_arquivo (str): Nome do arquivo a ser enviado ao Telegram.
    """
    bot = Bot(token=configs['telegram']['token'])
    async with bot:
        await bot.send_document(chat_id=configs['telegram']['chatid'], document=stream, filename=nome_arquivo)
