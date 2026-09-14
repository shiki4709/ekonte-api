FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir '.[api,gemini]' \
    && useradd --create-home ekonte && mkdir /data && chown ekonte /data
USER ekonte
ENV EKONTE_DATA_DIR=/data
VOLUME /data
EXPOSE 8421
CMD ["ekonte", "serve", "--host", "0.0.0.0", "--port", "8421"]
