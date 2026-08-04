RESERVED_CHARS = set("_*[]()~`>#+-=|{}.!")

class MarkdownV2Error(ValueError):
    """Строка не является валидным Telegram MarkdownV2."""
 
 
def validate_markdown_v2(text: str) -> None:
    """Бросает MarkdownV2Error, если `text` не является валидным MarkdownV2."""
    if not text:
        raise MarkdownV2Error("empty text is not valid MarkdownV2")
 
    i = 0
    n = len(text)
    stack: list[tuple[str, int]] = []
 
    def fail(message: str, position: int) -> None:
        raise MarkdownV2Error(f"{message} (позиция {position})\n  текст: {text!r}")
 
    while i < n:
        ch = text[i]
 
        if ch == "`":
            marker = "```" if text[i:i + 3] == "```" else "`"
            marker_len = len(marker)
            if stack and stack[-1][0] == marker:
                stack.pop()
                i += marker_len
                continue
            start = i
            j = i + marker_len
            closed = False
            while j < n:
                if text[j] == "\\" and j + 1 < n and text[j + 1] in ("`", "\\"):
                    j += 2
                    continue
                if text[j:j + marker_len] == marker:
                    j += marker_len
                    closed = True
                    break
                j += 1
            if not closed:
                fail(f'entity "{marker}" is never closed', start)
            i = j
            continue
 
        if ch == "\\":
            if i + 1 >= n:
                fail("dangling escape character '\\' at end of string", i)
            nxt = text[i + 1]
            if nxt not in RESERVED_CHARS:
                fail(
                    f"{nxt!r} is escaped with '\\', but it is not a reserved "
                    "MarkdownV2 character",
                    i,
                )
            i += 2
            continue
 
        if ch == "_" and text[i:i + 2] == "__":
            _toggle(stack, "__", i)
            i += 2
            continue
        if ch == "_":
            _toggle(stack, "_", i)
            i += 1
            continue
        if ch == "*":
            _toggle(stack, "*", i)
            i += 1
            continue
        if ch == "~":
            _toggle(stack, "~", i)
            i += 1
            continue
        if ch == "|" and text[i:i + 2] == "||":
            _toggle(stack, "||", i)
            i += 2
            continue
        if ch == "|":
            fail('a lone "|" is not valid MarkdownV2 (spoilers use "||")', i)
 
        if ch == "[":
            stack.append(("[", i))
            i += 1
            continue
        if ch == "]":
            if not stack or stack[-1][0] != "[":
                fail('unmatched "]"', i)
            stack.pop()
            if text[i + 1:i + 2] != "(":
                fail('"]" is not followed by "(" (malformed link)', i)
            j = i + 2
            depth = 1
            while j < n and depth:
                if text[j] == "\\" and j + 1 < n:
                    j += 2
                    continue
                if text[j] == "(":
                    depth += 1
                elif text[j] == ")":
                    depth -= 1
                j += 1
            if depth:
                fail('unmatched "(" in link URL', i + 1)
            i = j
            continue
 
        if ch in "()":
            fail(f"unescaped {ch!r} outside of link syntax", i)
 
        if ch in RESERVED_CHARS:
            fail(f"unescaped reserved character {ch!r}", i)
 
        i += 1
 
    if stack:
        marker, pos = stack[-1]
        fail(f'entity "{marker}" opened here is never closed', pos)
 
 
def _toggle(stack: list[tuple[str, int]], marker: str, pos: int) -> None:
    if stack and stack[-1][0] == marker:
        stack.pop()
    else:
        stack.append((marker, pos))
