from typing import Literal

import httpx
import marvin
from marvin.utilities.strings import convert_md_links_to_slack
from prefect.blocks.system import Secret


async def post_slack_message(
    message: str,
    channel_id: str,
    thread_ts: str | None = None,
    auth_token: str | None = None
) -> httpx.Response:
    
    if not auth_token:
        auth_token = marvin.settings.slack_api_token.get_secret_value()
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://slack.com/api/chat.postMessage",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "channel": channel_id,
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


async def fetch_current_message_text(channel: str, ts: str) -> str:
    """Fetch the current text of a specific Slack message using its timestamp."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://slack.com/api/conversations.replies",
            params={"channel": channel, "ts": ts},
            headers={
                "Authorization": f"Bearer {marvin.settings.slack_api_token.get_secret_value()}" # noqa: E501
            }
        )
    response.raise_for_status()
    messages = response.json().get("messages", [])
    if not messages:
        raise ValueError("Message not found")

    return messages[0]["text"]


async def edit_slack_message(
    channel: str, ts: str, new_text: str, mode: Literal['append', 'replace'] = 'append'
) -> httpx.Response:
    """Edit an existing Slack message by appending new text or replacing it.
    
    Args:
        channel (str): The Slack channel ID.
        ts (str): The timestamp of the message to edit.
        new_text (str): The new text to append or replace in the message.
        mode (Literal['append', 'replace']): The mode of text editing, 'append'
            (default) or 'replace'.
    
    Returns:
        httpx.Response: The response from the Slack API.
    """
    match mode:
        case 'append':
            # Fetch the current message text
            current_text = await fetch_current_message_text(channel, ts)
            # Append the new text
            updated_text = f"{current_text}\n{convert_md_links_to_slack(new_text)}"
        case 'replace':
            # Use the new text as is for replacement
            updated_text = convert_md_links_to_slack(new_text)
        case _:
            raise ValueError("Invalid mode. Use 'append' or 'replace'.")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://slack.com/api/chat.update",
            headers={
                "Authorization": f"Bearer {marvin.settings.slack_api_token.get_secret_value()}" # noqa: E501
            },
            json={"channel": channel, "ts": ts, "text": updated_text}
        )
    
    response.raise_for_status()
    return response

async def search_slack_messages(
    query: str,
    max_messages: int = 3,
    channel: str | None = None,
    user_auth_token: str | None = "community-bot-slack-user-token"
) -> list:
    """
    Search for messages in Slack workspace based on a query.

    Args:
        query (str): The search query.
        max_messages (int): The maximum number of messages to retrieve.
        channel (str, optional): The specific channel to search in. Defaults to None,
            which searches all channels.

    Returns:
        list: A list of message contents and permalinks matching the query.
    """
    all_messages = []
    next_cursor = None
    
    if user_auth_token and not user_auth_token.startswith("xoxb-"):
        user_auth_token = (await Secret.load(user_auth_token)).get()
    elif not user_auth_token:
        user_auth_token = marvin.settings.slack_api_token.get_secret_value()

    async with httpx.AsyncClient() as client:
        while len(all_messages) < max_messages:
            params = {
                "query": query, "limit": min(max_messages - len(all_messages), 10)
            }
            if channel:
                params["channel"] = channel
            if next_cursor:
                params["cursor"] = next_cursor

            response = await client.get(
                "https://slack.com/api/search.messages",
                headers={"Authorization": f"Bearer {user_auth_token}"},
                params=params
            )

            response.raise_for_status()
            data = response.json().get("messages", {}).get("matches", [])
            for message in data:
                all_messages.append(
                    {
                        "content": message.get("text", ""),
                        "permalink": message.get("permalink", "")
                    }
                )

            next_cursor = response.json().get(
                "response_metadata", {}
            ).get("next_cursor")

            if not next_cursor:
                break

    return all_messages[:max_messages]