# Usa uma imagem oficial do Python (leve)
FROM python:3.10-slim

# Define o diretório de trabalho dentro do contêiner
WORKDIR /app

# Instala as dependências do sistema operacional (Tesseract OCR e pacotes básicos)
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-por \
    libgl1-mesa-glx \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Copia os arquivos de dependências e instala os pacotes Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instala os navegadores e dependências de sistema do Playwright
RUN playwright install --with-deps chromium

# Copia todo o restante do projeto para dentro do contêiner
COPY . .

# Expõe a porta padrão do Streamlit
EXPOSE 8501

# Comando para iniciar a aplicação
CMD ["streamlit", "run", "app_central.py", "--server.port=8501", "--server.address=0.0.0.0"]