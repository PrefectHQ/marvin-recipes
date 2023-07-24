from marvin.deployment import Deployment

from chatbot import Chatbot, handle_message

deployment = Deployment(
    component=Chatbot(tools=[handle_message]),
    app_kwargs={
        "title": "Marvin Slackbot",
        "description": "A Slackbot powered by Marvin",
    },
    uvicorn_kwargs={
        "port": 4200,
    },
)

deployment.serve()