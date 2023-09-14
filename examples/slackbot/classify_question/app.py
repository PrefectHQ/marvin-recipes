from api import read_metrics, update_metrics
from classify import PrefectConcepts
from db import init_db
from fastapi import FastAPI
from models import MetricRecord

app = FastAPI()


@app.get("/metrics/")
async def read_all_metrics() -> list[MetricRecord]:
    return await read_metrics()


@app.post("/queries/")
async def update_metrics_for_query(query_text: str):
    result_set = await PrefectConcepts._extract_async(query_text)
    await update_metrics(concepts=result_set.concepts)


@app.on_event("startup")
async def startup_event():
    await init_db()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=4200)

"""
docker build . -f examples/slackbot/classify_question/Dockerfile.metrics -t metrics
docker run -p 4200:4200 metrics

curl -X 'POST' 'http://localhost:4200/queries/?query_text=howtodeployprefectflow'

curl -X 'GET' 'http://localhost:4200/metrics/'
"""
