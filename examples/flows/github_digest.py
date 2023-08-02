import inspect
from datetime import date, datetime, timedelta

from marvin import ai_fn
from marvin.utilities.strings import jinja_env
from marvin_recipes.utilities.slack import (
    fetch_contributor_data,
    post_slack_message,
)
from prefect import flow, task
from prefect.artifacts import create_markdown_artifact
from prefect.blocks.system import Secret
from prefect.tasks import task_input_hash

REPO_DIGEST_TEMPLATE = jinja_env.from_string(inspect.cleandoc("""
    # [{{ owner }}/{{ repo }}](https://github.com/{{ owner }}/{{ repo }}) GitHub Event Digest: {{ today }}
        
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
@ai_fn(
    instructions="You are a witty and subtle orator. Speak to us of the day's events."
)
def summarize_digest(markdown_digest: str) -> str:
    """Given a markdown digest of GitHub activity, create a story that is
    informative, entertaining, and epic in proportion to the day's events -
    an empty day should be handled with a short sarcastic quip about humans
    and their laziness.

    The story should capture collective efforts of the project.
    Each contributor plays a role in this story, their actions
    (issues raised, PRs opened, commits merged) shaping the events of the day.

    The narrative should highlight key contributors and their deeds, drawing upon the
    details in the digest to create a compelling and engaging tale of the day's events.
    A dry pun or 2 are encouraged.

    Usernames should be markdown links to the contributor's GitHub profile.

    The story should begin with a short pithy welcome to the reader.
    """  # noqa: E501


@task(
    task_run_name="Fetch GitHub Activity for {owner}/{repo}",
    cache_key_fn=task_input_hash,
    cache_expiration=timedelta(days=1),
)
async def get_repo_activity_data(
    owner: str,
    repo: str,
    gh_token_secret_name: str,
    since: datetime,
):
    """Get the activity data for a given repository."""
    return await fetch_contributor_data(
        token=(await Secret.load(gh_token_secret_name)).get(),
        owner=owner,
        repo=repo,
        since=since,
    )


@flow(name="Daily GitHub Digest", flow_run_name="Digest {owner}/{repo}")
async def daily_github_digest(
    owner: str = "PrefectHQ",
    repo: str = "prefect",
    slack_channel: str = "testing-slackbots",
    gh_token_secret_name: str = "github-token",
):
    """A flow that creates a daily digest of GitHub activity for a
        given repository.

    Args:
        owner: The owner of the repository.
        repo: The name of the repository.
        slack_channel: The name of the Slack channel to post the digest to.
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

    tldr = summarize_digest.with_options(
        task_run_name=f"Creating story from digest of {owner}/{repo}"
    )(markdown_digest)

    await create_markdown_artifact(
        key=f"{repo}-github-digest",
        markdown=markdown_digest,
        description=tldr,
    )

    await post_slack_message(
        message=f"{tldr}\n\nFull Digest:\n\n{markdown_digest}",
        channel=slack_channel,
    )


if __name__ == "__main__":
    import asyncio

    asyncio.run(daily_github_digest(owner="PrefectHQ", repo="marvin"))
