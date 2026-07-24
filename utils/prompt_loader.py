from pathlib import Path


def load_prompt(filename):
    """
    Load a prompt file from the prompts directory.
    """

    prompt_path = Path("prompts") / filename

    with open(prompt_path, "r", encoding="utf-8") as file:
        return file.read()