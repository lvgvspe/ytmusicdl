# Usa a imagem base do Ubuntu
FROM ubuntu:22.04

# Define o diretório de trabalho
WORKDIR /app

# Instala dependências básicas do sistema
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    ffmpeg \
    procps \
    && rm -rf /var/lib/apt/lists/*

COPY ./requirements.txt .

# Cria e ativa um ambiente virtual Python
RUN python3 -m venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Instala as dependências do Python
RUN pip install --no-cache-dir -r requirements.txt

# Copia os arquivos necessários
COPY . .

# Cria um usuário não-root para segurança
RUN useradd -m ytuser && chown -R ytuser:ytuser /app
USER ytuser

# Expõe a porta que o Flask usa
EXPOSE 5000

# Comando para iniciar a aplicação
CMD ["bash", "start.sh"]