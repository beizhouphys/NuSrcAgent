from __future__ import annotations # Codex

from typing import Any # Codex


class SimpleYamlError(ValueError): # Codex
    pass # Codex


def load_simple_yaml(text: str) -> dict[str, Any]: # Codex
    parsed_lines: list[tuple[int, str, int]] = [] # Codex
    for line_number, raw_line in enumerate(text.splitlines(), start=1): # Codex
        line = strip_comment(raw_line).rstrip() # Codex
        if line.strip() == "": # Codex
            continue # Codex
        indent = len(line) - len(line.lstrip(" ")) # Codex
        if indent % 2 != 0: # Codex
            raise SimpleYamlError(f"line {line_number}: use two-space indentation") # Codex
        parsed_lines.append((indent, line.strip(), line_number)) # Codex
    if len(parsed_lines) == 0: # Codex
        return {} # Codex
    payload, next_index = parse_block(parsed_lines, 0, parsed_lines[0][0]) # Codex
    if next_index != len(parsed_lines) or not isinstance(payload, dict): # Codex
        raise SimpleYamlError("top level must be a mapping") # Codex
    return payload # Codex


def parse_block(lines: list[tuple[int, str, int]], start: int, indent: int) -> tuple[Any, int]: # Codex
    if lines[start][1] == "[]": # cdx
        return [], start + 1 # cdx
    if lines[start][1] == "{}": # cdx
        return {}, start + 1 # cdx
    is_list = lines[start][1] == "-" or lines[start][1].startswith("- ") # Codex
    container: Any = [] if is_list else {} # Codex
    index = start # Codex
    while index < len(lines): # Codex
        line_indent, content, line_number = lines[index] # Codex
        if line_indent < indent: # Codex
            break # Codex
        if line_indent > indent: # Codex
            raise SimpleYamlError(f"line {line_number}: invalid indentation") # Codex
        if is_list: # Codex
            if not (content == "-" or content.startswith("- ")): # Codex
                raise SimpleYamlError(f"line {line_number}: mixed list and mapping entries") # Codex
            item_text = content[1:].strip() # Codex
            if item_text == "": # Codex
                if index + 1 >= len(lines) or lines[index + 1][0] <= indent: # Codex
                    raise SimpleYamlError(f"line {line_number}: empty list item") # Codex
                item, index = parse_block(lines, index + 1, lines[index + 1][0]) # Codex
                container.append(item) # Codex
                continue # Codex
            if ":" in item_text: # Codex
                key, raw_value = split_mapping_entry(item_text, line_number) # Codex
                item = {key: parse_scalar(raw_value)} if raw_value != "" else {key: {}} # Codex
                index += 1 # Codex
                if index < len(lines) and lines[index][0] > indent: # Codex
                    extra, index = parse_block(lines, index, lines[index][0]) # Codex
                    if not isinstance(extra, dict): # Codex
                        raise SimpleYamlError(f"line {line_number}: list mapping item must contain mappings") # Codex
                    item.update(extra) # Codex
                container.append(item) # Codex
                continue # Codex
            container.append(parse_scalar(item_text)) # Codex
            index += 1 # Codex
            continue # Codex
        key, raw_value = split_mapping_entry(content, line_number) # Codex
        index += 1 # Codex
        if raw_value == "": # Codex
            if index >= len(lines) or lines[index][0] <= indent: # Codex
                container[key] = {} # Codex
            else: # Codex
                container[key], index = parse_block(lines, index, lines[index][0]) # Codex
        else: # Codex
            container[key] = parse_scalar(raw_value) # Codex
    return container, index # Codex


def split_mapping_entry(content: str, line_number: int) -> tuple[str, str]: # Codex
    if ":" not in content: # Codex
        raise SimpleYamlError(f"line {line_number}: expected 'key: value'") # Codex
    key, raw_value = content.split(":", 1) # Codex
    key = key.strip() # Codex
    if key == "": # Codex
        raise SimpleYamlError(f"line {line_number}: empty key") # Codex
    return key, raw_value.strip() # Codex


def dump_simple_yaml(payload: Any, indent: int = 0) -> str: # Codex
    return "\n".join(dump_lines(payload, indent)) + "\n" # Codex


def dump_lines(payload: Any, indent: int) -> list[str]: # Codex
    pad = " " * indent # Codex
    if isinstance(payload, dict): # Codex
        lines: list[str] = [] # Codex
        for key, value in payload.items(): # Codex
            if isinstance(value, (dict, list)) and len(value) == 0: # cdx
                lines.append(f"{pad}{key}: {format_scalar(value)}") # cdx
            elif isinstance(value, (dict, list)): # cdx
                lines.append(f"{pad}{key}:") # Codex
                lines.extend(dump_lines(value, indent + 2)) # Codex
            else: # Codex
                lines.append(f"{pad}{key}: {format_scalar(value)}") # Codex
        return lines # Codex
    if isinstance(payload, list): # Codex
        if len(payload) == 0: # Codex
            return [f"{pad}[]"] # Codex
        lines = [] # Codex
        for item in payload: # Codex
            if isinstance(item, dict): # Codex
                lines.append(f"{pad}-") # Codex
                lines.extend(dump_lines(item, indent + 2)) # Codex
            else: # Codex
                lines.append(f"{pad}- {format_scalar(item)}") # Codex
        return lines # Codex
    return [f"{pad}{format_scalar(payload)}"] # Codex


def strip_comment(line: str) -> str: # Codex
    quote: str | None = None # Codex
    for index, char in enumerate(line): # Codex
        if char in {"'", '"'}: # Codex
            quote = None if quote == char else char if quote is None else quote # Codex
        elif char == "#" and quote is None: # Codex
            return line[:index] # Codex
    return line # Codex


def parse_scalar(value: str) -> Any: # Codex
    if value == "[]": # cdx
        return [] # cdx
    if value == "{}": # cdx
        return {} # cdx
    lowered = value.lower() # Codex
    if lowered in {"null", "none", "~"}: # Codex
        return None # Codex
    if lowered == "true": # Codex
        return True # Codex
    if lowered == "false": # Codex
        return False # Codex
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")): # Codex
        return value[1:-1] # Codex
    try: # Codex
        if any(marker in value for marker in [".", "e", "E"]): # Codex
            return float(value) # Codex
        return int(value) # Codex
    except ValueError: # Codex
        return value # Codex


def format_scalar(value: Any) -> str: # Codex
    if value == []: # cdx
        return "[]" # cdx
    if value == {}: # cdx
        return "{}" # cdx
    if value is None: # Codex
        return "null" # Codex
    if isinstance(value, bool): # Codex
        return "true" if value else "false" # Codex
    if isinstance(value, (int, float)): # Codex
        return str(value) # Codex
    text = str(value) # Codex
    if text == "" or needs_quotes(text): # Codex
        return '"' + text.replace('"', '\\"') + '"' # Codex
    return text # Codex


def needs_quotes(text: str) -> bool: # Codex
    if any(char in text for char in [":", "#", "{", "}", "[", "]", ","]): # Codex
        return True # Codex
    if text.lower() in {"true", "false", "null", "none", "~"}: # Codex
        return True # Codex
    try: # Codex
        float(text) # Codex
        return True # Codex
    except ValueError: # Codex
        return False # Codex
