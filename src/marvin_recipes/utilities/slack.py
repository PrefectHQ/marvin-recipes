from datetime import datetime
from typing import Dict, Union

import httpx
import marvin
from marvin.utilities.strings import convert_md_links_to_slack


async def fetch_contributor_data(
    token: str, owner: str, repo: str, since: datetime, max: int = 100
) -> Dict[str, Dict[str, Union[str, list]]]:
    events_url = f"https://api.github.com/repos/{owner}/{repo}/events?per_page={max}"

    contributors_activity = {}

    async with httpx.AsyncClient(
        headers={
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {token}",
        }
    ) as client:
        events = (await client.get(events_url)).json()

        for event in events:
            created_at = datetime.fromisoformat(event["created_at"].rstrip("Z"))
            if created_at < since:
                continue

            contributor_username = event["actor"]["login"]

            if contributor_username not in contributors_activity:
                contributors_activity[contributor_username] = {
                    "created_issues": [],
                    "created_pull_requests": [],
                    "merged_commits": [],
                }

            if (
                event["type"] == "IssuesEvent"
                and event["payload"]["action"] == "opened"
            ):
                contributors_activity[contributor_username]["created_issues"].append(
                    event["payload"]["issue"]
                )

            elif (
                event["type"] == "PullRequestEvent"
                and event["payload"]["action"] == "opened"
            ):
                contributors_activity[contributor_username][
                    "created_pull_requests"
                ].append(event["payload"]["pull_request"])

            elif event["type"] == "PushEvent":
                for commit_data in event["payload"]["commits"]:
                    commit = (await client.get(commit_data["url"])).json()
                    commit_message = commit["commit"]["message"].split("\n")
                    cleaned_commit_message = "\n".join(
                        line
                        for line in commit_message
                        if not line.strip().lower().startswith("co-authored-by:")
                    )
                    commit_msg = commit["commit"]["message"] = cleaned_commit_message

                    if (
                        "Merge remote-tracking branch" not in commit_msg
                        and "Merge branch" not in commit_msg
                    ):
                        contributors_activity[contributor_username][
                            "merged_commits"
                        ].append(commit)

    return contributors_activity


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


async def get_thread_messages(channel: str, thread_ts: str) -> list[Dict]:
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
