import httpx
import marvin
from marvin.utilities.strings import convert_md_links_to_slack


async def post_slack_message(
    message: str, channel: str, thread_ts: str = None
) -> httpx.Response:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://slack.com/api/chat.postMessage",
            headers={
                "Authorization": (
                    f"Bearer {marvin.settings.slack_api_token.get_secret_value()}"
                )
            },
            json={
                "channel": channel,
                "text": convert_md_links_to_slack(message),
                "thread_ts": thread_ts,
            },
        )

    response.raise_for_status()
    return response


async def get_thread_messages(channel: str, thread_ts: str) -> list:
    """Get all messages from a slack thread."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://slack.com/api/conversations.replies",
            headers={
                "Authorization": (
                    f"Bearer {marvin.settings.slack_api_token.get_secret_value()}"
                )
            },
            params={"channel": channel, "ts": thread_ts},
        )
    response.raise_for_status()
    return response.json().get("messages", [])


async def get_user_name(user_id: str) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://slack.com/api/users.info",
            params={"user": user_id},
            headers={
                "Authorization": f"Bearer {marvin.settings.slack_api_token.get_secret_value()}"  # noqa: E501
            },
        )
    return response.json()["user"]["name"] if response.status_code == 200 else user_id


async def get_channel_name(channel_id: str) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://slack.com/api/conversations.info",
            params={"channel": channel_id},
            headers={
                "Authorization": f"Bearer {marvin.settings.slack_api_token.get_secret_value()}"  # noqa: E501
            },
        )
    return (
        response.json()["channel"]["name"]
        if response.status_code == 200
        else channel_id
    )
