"""Line scanner engine for MyST directive detection and processing."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


# Regex patterns for directive fence detection
# Backtick open: ```{directive-name} optional-argument
BACKTICK_OPEN_RE = re.compile(r"^(\s*)(`{3,})\{(\w[\w-]*)\}\s*(.*)$")
# Colon open: :::{directive-name} optional-argument
COLON_OPEN_RE = re.compile(r"^(\s*)(:{3,})\{(\w[\w-]*)\}\s*(.*)$")
# Option line: :key: value (must appear right after opening fence)
OPTION_RE = re.compile(r"^:(\w[\w-]*):\s*(.*)$")


@dataclass
class DirectiveFrame:
    """Represents a parsed MyST directive block."""

    name: str  # e.g. "code-cell", "note", "figure"
    fence_char: str  # "`" or ":"
    fence_count: int  # 3+ for backticks, 3+ for colons
    argument: str  # e.g. "python" for code-cell, path for figure
    options: dict = field(default_factory=dict)
    body_lines: list[str] = field(default_factory=list)
    indent: int = 0  # leading whitespace count


class Scanner:
    """Regex-based line scanner with a directive stack.

    Processes MyST markdown line by line, detecting directive fences,
    parsing options, collecting body content, and calling a transform
    function for each completed directive.
    """

    def __init__(self, transform_fn, inline_fn=None):
        """Initialize the scanner.

        Args:
            transform_fn: Called with a DirectiveFrame when a directive is
                fully parsed (closing fence matched). Should return a list
                of output lines (without trailing newlines).
            inline_fn: Optional function applied to each regular line
                (lines outside of directives). Should return the
                transformed line string.
        """
        self.stack: list[DirectiveFrame] = []
        self.transform_fn = transform_fn
        self.inline_fn = inline_fn

    def scan(self, text: str) -> str:
        """Process text line by line and return transformed output.

        Args:
            text: The full MyST markdown text.

        Returns:
            The transformed text with directives processed.
        """
        lines = text.split("\n")
        output_lines: list[str] = []
        # Track whether we are in the options section of a directive
        in_options = False
        # Track regular (non-directive) code fences to avoid transforming
        # inline roles inside them
        in_regular_code_fence = False
        regular_fence_char = ""
        regular_fence_count = 0
        regular_fence_indent = 0

        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.lstrip()
            indent = len(line) - len(stripped)

            # ----------------------------------------------------------
            # Check if this line opens a directive fence
            # ----------------------------------------------------------
            backtick_m = BACKTICK_OPEN_RE.match(line)
            colon_m = COLON_OPEN_RE.match(line)
            open_match = backtick_m or colon_m

            if open_match and not in_regular_code_fence:
                leading_ws = open_match.group(1)
                fence_str = open_match.group(2)
                directive_name = open_match.group(3)
                argument = open_match.group(4).strip()

                fence_char = fence_str[0]
                fence_count = len(fence_str)

                frame = DirectiveFrame(
                    name=directive_name,
                    fence_char=fence_char,
                    fence_count=fence_count,
                    argument=argument,
                    indent=len(leading_ws),
                )
                self.stack.append(frame)
                in_options = True
                i += 1
                continue

            # ----------------------------------------------------------
            # If we have a stack, we are inside a directive
            # ----------------------------------------------------------
            if self.stack:
                current = self.stack[-1]

                # Check for closing fence
                if self._is_close_fence(stripped, indent, current):
                    # Pop the frame and transform
                    frame = self.stack.pop()
                    transformed = self.transform_fn(frame)

                    if self.stack:
                        # Nested: add transformed lines to parent body
                        for tl in transformed:
                            self.stack[-1].body_lines.append(tl)
                    else:
                        output_lines.extend(transformed)

                    in_options = False
                    i += 1
                    continue

                # Check for option lines (only right after opening)
                if in_options:
                    # Strip the directive's indentation from the line
                    content = self._strip_indent(line, current.indent)
                    opt_match = OPTION_RE.match(content.strip())
                    if opt_match:
                        key = opt_match.group(1)
                        value = opt_match.group(2).strip()
                        current.options[key] = value
                        i += 1
                        continue
                    else:
                        # End of options section
                        in_options = False
                        # Skip blank lines between options and body
                        if content.strip() == "":
                            i += 1
                            continue

                # Body line for the current directive
                content = self._strip_indent(line, current.indent)
                current.body_lines.append(content)
                i += 1
                continue

            # ----------------------------------------------------------
            # Outside any directive: handle regular code fences
            # ----------------------------------------------------------
            # Check for regular code fence (``` or ~~~ without {directive})
            if not in_regular_code_fence:
                regular_fence_m = re.match(r"^(\s*)(`{3,}|~{3,})(\w*)\s*$", line)
                if regular_fence_m:
                    regular_fence_indent = len(regular_fence_m.group(1))
                    regular_fence_char = regular_fence_m.group(2)[0]
                    regular_fence_count = len(regular_fence_m.group(2))
                    # Only if it looks like a regular fence (has language or is plain)
                    in_regular_code_fence = True
                    output_lines.append(line)
                    i += 1
                    continue
                # Also check opening fences with language like ```python
                regular_fence_m2 = re.match(r"^(\s*)(`{3,}|~{3,})(\w+)\s*$", line)
                if regular_fence_m2:
                    regular_fence_indent = len(regular_fence_m2.group(1))
                    regular_fence_char = regular_fence_m2.group(2)[0]
                    regular_fence_count = len(regular_fence_m2.group(2))
                    in_regular_code_fence = True
                    output_lines.append(line)
                    i += 1
                    continue
            else:
                # Inside a regular code fence: check for close
                close_m = re.match(
                    r"^(\s*)(" + re.escape(regular_fence_char) + r"{3,})\s*$",
                    line,
                )
                if close_m:
                    close_count = len(close_m.group(2))
                    close_indent = len(close_m.group(1))
                    if (
                        close_count >= regular_fence_count
                        and close_indent <= regular_fence_indent
                    ):
                        in_regular_code_fence = False
                output_lines.append(line)
                i += 1
                continue

            # ----------------------------------------------------------
            # Regular line: apply inline transforms
            # ----------------------------------------------------------
            if self.inline_fn:
                output_lines.append(self.inline_fn(line))
            else:
                output_lines.append(line)
            i += 1

        # Handle unclosed directives (shouldn't happen in valid input,
        # but handle gracefully)
        while self.stack:
            frame = self.stack.pop()
            transformed = self.transform_fn(frame)
            output_lines.extend(transformed)

        return "\n".join(output_lines)

    def _is_close_fence(
        self, stripped: str, indent: int, frame: DirectiveFrame
    ) -> bool:
        """Check if a stripped line is a valid close fence for the given frame."""
        if not stripped:
            return False
        # Must be only fence characters (and whitespace already stripped)
        if stripped[0] != frame.fence_char:
            return False
        # Must be all the same char
        if not all(c == frame.fence_char for c in stripped):
            return False
        # Must have at least as many chars as the opening fence
        if len(stripped) < frame.fence_count:
            return False
        # Indent must be <= the opening fence indent
        if indent > frame.indent:
            return False
        return True

    def _strip_indent(self, line: str, indent: int) -> str:
        """Remove up to `indent` spaces from the beginning of a line."""
        if indent == 0:
            return line
        # Remove up to indent characters of whitespace
        removed = 0
        for ch in line:
            if removed >= indent:
                break
            if ch == " ":
                removed += 1
            elif ch == "\t":
                removed += 1  # treat tab as 1 for simplicity
            else:
                break
        return line[removed:]
