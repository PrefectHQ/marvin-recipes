import inspect
from datetime import date, datetime, timedelta

import httpx
from marvin import ai_fn
from marvin.utilities.strings import jinja_env
from prefect import flow, task
from prefect.artifacts import create_markdown_artifact
from prefect.blocks.system import Secret
from prefect.tasks import task_input_hash

REPO_DIGEST_TEMPLATE = jinja_env.from_string(inspect.cleandoc("""
    # GitHub Digest: {{ today }}
    
    Here's what's been happening in [{{ owner }}/{{ repo }}](https://github.com/{{ owner }}/{{ repo }}) today:
    
    {% for contributor, activities in contributors_activity.items() %}
    {% if activities.created_issues|length > 0 or activities.created_pull_requests|length > 0 or activities.merged_commits|length > 0 %}
    ## {{ contributor }}:
    {% if activities.created_issues|length > 0 %}
    - Created {{ activities.created_issues|length }} issue(s)
    {% for issue in activities.created_issues %}
        - [{{ issue.title }}]({{ issue.html_url }})
    {% endfor %}
    {% endif %}
    
    {% if activities.created_pull_requests|length > 0 %}
    - Opened {{ activities.created_pull_requests|length }} PR(s)
    {% for pr in activities.created_pull_requests %}
        - [{{ pr.title }}]({{ pr.html_url }})
    {% endfor %}
    {% endif %}
    
    {% if activities.merged_commits|length > 0 %}
    - Merged {{ activities.merged_commits|length }} commit(s)
    {% for commit in activities.merged_commits %}
        - [{{ commit.commit.message }}]({{ commit.html_url }})
    {% endfor %}
    {% endif %}
    {% endif %}
    {% endfor %}
    """))  # noqa: E501


@task(timeout_seconds=90, retries=1)
@ai_fn
def summarize_digest(markdown_digest: str) -> str:
    """
    Given a markdown digest of GitHub activity, create an epic story in markdown.

    The story should capture collective efforts of the project.
    Each contributor plays a role in this story, their actions (issues raised, PRs opened, commits merged)
    shaping the events of the day.

    The narrative should highlight key contributors and their deeds, drawing upon the details in the digest
    to create a compelling and engaging tale of the day's events. A dry pun or 2 are encouraged.

    Usernames should be bolded markdown links to the contributor's GitHub profile.
    """  # noqa: E501


@task(cache_key_fn=task_input_hash, cache_expiration=timedelta(days=1))
async def get_repo_activity_data(owner, repo, gh_token_secret_name, since, max=100):
    events_url = f"https://api.github.com/repos/{owner}/{repo}/events?per_page={max}"

    token = await Secret.load(gh_token_secret_name)

    contributors_activity = {}

    async with httpx.AsyncClient(
        headers={
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {token.get()}",
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
            ):  # noqa: E501
                contributors_activity[contributor_username]["created_issues"].append(
                    event["payload"]["issue"]
                )

            elif (
                event["type"] == "PullRequestEvent"
                and event["payload"]["action"] == "opened"
            ):  # noqa: E501
                contributors_activity[contributor_username][
                    "created_pull_requests"
                ].append(event["payload"]["pull_request"])

            elif event["type"] == "PushEvent":
                for commit_data in event["payload"]["commits"]:
                    commit = (await client.get(commit_data["url"])).json()
                    # Remove the co-authored-by lines from the commit message
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
                    ):  # noqa: E501
                        contributors_activity[contributor_username][
                            "merged_commits"
                        ].append(commit)

    return contributors_activity


@flow
async def daily_github_digest(
    owner: str = "PrefectHQ",
    repo: str = "prefect",
    gh_token_secret_name: str = "github-token",
):
    """A flow that creates a daily digest of GitHub activity for a
        given repository.

    Args:
        owner: The owner of the repository.
        repo: The name of the repository.
        gh_token_secret_name: Secret Block containing the GitHub token.
    """
    since = datetime.utcnow() - timedelta(days=1)

    data = await get_repo_activity_data(
        owner=owner,
        repo=repo,
        gh_token_secret_name=gh_token_secret_name,
        since=since,
    )

    markdown_digest = REPO_DIGEST_TEMPLATE.render(
        today=date.today(),
        owner=owner,
        repo=repo,
        contributors_activity=data,
    )

    tldr = summarize_digest(markdown_digest)

    await create_markdown_artifact(
        key="github-digest",
        markdown=markdown_digest,
        description=tldr,
    )


if __name__ == "__main__":
    import asyncio

    asyncio.run(daily_github_digest())
