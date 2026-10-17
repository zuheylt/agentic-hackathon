FROM python:3.11-slim

# Install Node.js 20.x
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# OKX Agent Trade Kit
RUN npm install -g @okx_ai/okx-trade-mcp @okx_ai/okx-trade-cli \
    --allow-scripts=@okx_ai/okx-trade-cli,@okx_ai/okx-trade-mcp

# Copy application
COPY . .

EXPOSE 10000

CMD ["sh", "-c", "python setup_railway.py && streamlit run app.py --server.port=${PORT:-10000} --server.address=0.0.0.0"]
