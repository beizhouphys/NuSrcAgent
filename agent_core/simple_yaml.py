from __future__ import annotations

from typing import Any


class SimpleYamlError(ValueError):
    pass


def load_simple_yaml(text: str) -> dict[str, Any]:
    parsed_lines: list[tuple[int, str, int]] = []
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = strip_comment(raw_line).rstrip()
        if line.strip() == "":
            continue
        indent = len(line) - len(line.lstrip(" "))
        if indent % 2 != 0:
            raise SimpleYamlError(f"line {line_number}: use two-space indentation")
        parsed_lines.append((indent, line.strip(), line_number))
    if len(parsed_lines) == 0:
        return {}
    payload, next_index = parse_block(parsed_lines, 0, parsed_lines[0][0])
    if next_index != len(parsed_lines) or not isinstance(payload, dict):
        raise SimpleYamlError("top level must be a mapping")
    return payload


def parse_block(lines: list[tuple[int, str, int]], start: int, indent: int) -> tuple[Any, int]:
    if lines[start][1] == "[]":
        return [], start + 1
    if lines[start][1] == "{}":
        return {}, start + 1
    is_list = lines[start][1] == "-" or lines[start][1].startswith("- ")
    container: Any = [] if is_list else {}
    index = start
    while index < len(lines):
        line_indent, content, line_number = lines[index]
        if line_indent < indent:
            break
        if line_indent > indent:
            raise SimpleYamlError(f"line {line_number}: invalid indentation")
        if is_list:
            if not (content == "-" or content.startswith("- ")):
                raise SimpleYamlError(f"line {line_number}: mixed list and mapping entries")
            item_text = content[1:].strip()
            if item_text == "":
                if index + 1 >= len(lines) or lines[index + 1][0] <= indent:
                    raise SimpleYamlError(f"line {line_number}: empty list item")
                item, index = parse_block(lines, index + 1, lines[index + 1][0])
                container.append(item)
                continue
            if ":" in item_text:
                key, raw_value = split_mapping_entry(item_text, line_number)
                item = {key: parse_scalar(raw_value)} if raw_value != "" else {key: {}}
                index += 1
                if index < len(lines) and lines[index][0] > indent:
                    extra, index = parse_block(lines, index, lines[index][0])
                    if not isinstance(extra, dict):
                        raise SimpleYamlError(f"line {line_number}: list mapping item must contain mappings")
                    item.update(extra)
                container.append(item)
                continue
            container.append(parse_scalar(item_text))
            index += 1
            continue
        key, raw_value = split_mapping_entry(content, line_number)
        index += 1
        if raw_value == "":
            if index >= len(lines) or lines[index][0] <= indent:
                container[key] = {}
            else:
                container[key], index = parse_block(lines, index, lines[index][0])
        else:
            container[key] = parse_scalar(raw_value)
    return container, index


def split_mapping_entry(content: str, line_number: int) -> tuple[str, str]:
    if ":" not in content:
        raise SimpleYamlError(f"line {line_number}: expected 'key: value'")
    key, raw_value = content.split(":", 1)
    key = key.strip()
    if key == "":
        raise SimpleYamlError(f"line {line_number}: empty key")
    return key, raw_value.strip()


def dump_simple_yaml(payload: Any, indent: int = 0) -> str:
    return "\n".join(dump_lines(payload, indent)) + "\n"


def dump_lines(payload: Any, indent: int) -> list[str]:
    pad = " " * indent
    if isinstance(payload, dict):
        lines: list[str] = []
        for key, value in payload.items():
            if isinstance(value, (dict, list)) and len(value) == 0:
                lines.append(f"{pad}{key}: {format_scalar(value)}")
            elif isinstance(value, (dict, list)):
                lines.append(f"{pad}{key}:")
                lines.extend(dump_lines(value, indent + 2))
            else:
                lines.append(f"{pad}{key}: {format_scalar(value)}")
        return lines
    if isinstance(payload, list):
        if len(payload) == 0:
            return [f"{pad}[]"]
        lines = []
        for item in payload:
            if isinstance(item, dict):
                lines.append(f"{pad}-")
                lines.extend(dump_lines(item, indent + 2))
            else:
                lines.append(f"{pad}- {format_scalar(item)}")
        return lines
    return [f"{pad}{format_scalar(payload)}"]


def strip_comment(line: str) -> str:
    quote: str | None = None
    for index, char in enumerate(line):
        if char in {"'", '"'}:
            quote = None if quote == char else char if quote is None else quote
        elif char == "#" and quote is None:
            return line[:index]
    return line


def parse_scalar(value: str) -> Any:
    if value == "[]":
        return []
    if value == "{}":
        return {}
    lowered = value.lower()
    if lowered in {"null", "none", "~"}:
        return None
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    try:
        if any(marker in value for marker in [".", "e", "E"]):
            return float(value)
        return int(value)
    except ValueError:
        return value


def format_scalar(value: Any) -> str:
    if value == []:
        return "[]"
    if value == {}:
        return "{}"
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        text = str(value)
        if isinstance(value, float) and "e" in text and "." not in text.split("e")[0]:
            text = text.replace("e", ".0e")
        return text
    text = str(value)
    if text == "" or needs_quotes(text):
        return '"' + text.replace('"', '\\"') + '"'
    return text


def needs_quotes(text: str) -> bool:
    if text.startswith((">", "|")):
        return True
    if any(char in text for char in [":", "#", "{", "}", "[", "]", ","]):
        return True
    if text.lower() in {"true", "false", "null", "none", "~"}:
        return True
    try:
        float(text)
        return True
    except ValueError:
        return False
