# You can run this as a service someplace like Cloud Run, or just run it locally
# with ngrok while testing (e.g. `ngrok http 4200`, set your slack event subscription to
# the ngrok url + your endpoint).

FROM python:3.11-slim

WORKDIR /app

COPY . /app

RUN python -m venv venv
ENV VIRTUAL_ENV=/app/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN apt-get update && \
    apt-get install -y git build-essential && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN pip install ".[chroma, prefect, serpapi, slackbot]"

EXPOSE 4200

CMD ["python", "examples/slackbot/start.py"]
