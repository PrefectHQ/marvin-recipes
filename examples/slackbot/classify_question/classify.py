import json
from pathlib import Path

from marvin import ai_model
from marvin.utilities.strings import jinja_env
from pydantic import BaseModel, root_validator

ENCODING = "utf-8"
background_dir = Path(__file__).parent / "background"

listed_concepts = set(
    concept
    for concepts in json.loads(
        (background_dir / "concepts.json").read_text(encoding=ENCODING)
    ).values()
    for concept in concepts
)

PREFECT_CONCEPT_BACKGROUND = None
if txt_files := list(background_dir.glob("*.txt")):
    PREFECT_CONCEPT_BACKGROUND = "\n\n".join(
        Path(file).read_text(encoding=ENCODING) for file in txt_files
    )

INSTRUCTIONS = jinja_env.from_string("""{%- if background %}
    Here's some background on modern Prefect concepts:
    {{ background }}
    {%- endif %}
    
    {%- if concepts %}
    Here is the known list of concepts
    {%- for concept in concepts %}
    - {{ concept }}
    {%- endfor %}
    {%- endif %}
    """).render(background=PREFECT_CONCEPT_BACKGROUND, concepts=listed_concepts)


@ai_model(instructions=INSTRUCTIONS)
class PrefectConcepts(BaseModel):
    """Classify a question as one or many (slugified) Prefect concepts"""

    concepts: set[str]

    @root_validator
    def validate_concepts(cls, values):
        return {
            "concepts": {
                concept.lower().replace(" ", "-")
                for concept in values["concepts"]
                if concept.lower().replace(" ", "-") in listed_concepts
            }
        }


# if __name__ == "__main__":
#     N_ITERATIONS = 3
#     query = """
#     how can i trigger a deployment after 10 certain flow runs have completed?
#     """

#     resulting_concept_sets = PrefectConcepts.map([query] * N_ITERATIONS)
#     combined_concepts = set.union(*(result.concepts for result in resulting_concept_sets)) # noqa
#     print(combined_concepts)
