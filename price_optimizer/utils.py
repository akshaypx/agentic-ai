import re


def clean_json(text: str):
    # remove markdown code blocks if present
    text = re.sub(r"```json|```", "", text).strip()
    return text