from typing import Any


def normalize_messages(messages: list[dict[str, Any]]) -> list[dict[str, str]]:
    normalized = []
    for message in messages:
        role = str(message.get("role", "user"))
        content = message.get("content", "")
        if isinstance(content, list):
            text_parts = [
                str(part.get("text", ""))
                for part in content
                if isinstance(part, dict) and part.get("type") == "text"
            ]
            content = "\n".join(part for part in text_parts if part)
        normalized.append({"role": role, "content": str(content)})
    return normalized


def messages_to_prompt(messages: list[dict[str, Any]], tokenizer: Any = None) -> str:
    normalized = normalize_messages(messages)
    if tokenizer is not None and hasattr(tokenizer, "apply_chat_template"):
        try:
            return tokenizer.apply_chat_template(
                normalized,
                tokenize=False,
                add_generation_prompt=True,
            )
        except Exception:
            pass

    role_names = {
        "system": "System",
        "user": "User",
        "assistant": "Assistant",
    }
    lines = []
    for message in normalized:
        role = role_names.get(message["role"], message["role"].title())
        lines.append(f"{role}: {message['content']}")
    lines.append("Assistant:")
    return "\n\n".join(lines)


def extract_generated_text(result: Any) -> str:
    if isinstance(result, str):
        return result.strip()

    if isinstance(result, list) and result:
        return extract_generated_text(result[0])

    if isinstance(result, dict):
        text = result.get("generated_text")
        if isinstance(text, str):
            return text.strip()
        if isinstance(text, list) and text:
            last = text[-1]
            if isinstance(last, dict):
                return str(last.get("content", "")).strip()
            return str(last).strip()

        text = result.get("text")
        if text is not None:
            return str(text).strip()

    return str(result).strip()
