import uuid

from prefect import flow, serve
from prefect.events import emit_event
from prefect.events.schemas import DeploymentTrigger

random_data = str(uuid.uuid4())


@flow(log_prints=True)
def downstream():
    print("i was triggered!")

trigger_on_event = DeploymentTrigger(
    name="Wait for N upstream deployments",
    enabled=True,
    match={
        "prefect.resource.id": "some-unique-id",
        "prefect.resource.whatever": random_data,
    },
    expect={"some-event"}
)
    

if __name__ == '__main__':
    emit_event(
        event="some-event",
        resource={
            "prefect.resource.id": "some-unique-id",
            "prefect.resource.whatever": random_data,
        }
    )
    serve(
        downstream.to_deployment(
            __file__, triggers=[trigger_on_event]
        )
    )