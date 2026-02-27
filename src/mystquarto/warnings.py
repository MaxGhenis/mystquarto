"""Warning and error reporting for mystquarto conversions."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class WarningCollector:
    """Collects warnings and errors during conversion.

    In strict mode, warnings are promoted to errors.
    """

    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    strict: bool = False

    def warn(self, message: str, file: str = "", line: int = 0):
        """Add a warning. In strict mode, treat as error.

        Args:
            message: The warning message.
            file: Optional source file path.
            line: Optional source line number.
        """
        formatted = self._format(message, file, line)
        if self.strict:
            self.errors.append(formatted)
        else:
            self.warnings.append(formatted)

    def error(self, message: str, file: str = "", line: int = 0):
        """Add an error.

        Args:
            message: The error message.
            file: Optional source file path.
            line: Optional source line number.
        """
        formatted = self._format(message, file, line)
        self.errors.append(formatted)

    def has_errors(self) -> bool:
        """Check if any errors have been recorded."""
        return len(self.errors) > 0

    def report(self) -> str:
        """Generate a summary report of all warnings and errors.

        Returns:
            A formatted string report.
        """
        lines: list[str] = []

        if self.errors:
            lines.append(f"Errors ({len(self.errors)}):")
            for err in self.errors:
                lines.append(f"  ERROR: {err}")

        if self.warnings:
            lines.append(f"Warnings ({len(self.warnings)}):")
            for warn in self.warnings:
                lines.append(f"  WARNING: {warn}")

        if not self.errors and not self.warnings:
            lines.append("No warnings or errors.")

        return "\n".join(lines)

    def _format(self, message: str, file: str, line: int) -> str:
        """Format a message with optional file and line prefix."""
        if file:
            prefix = f"{file}:{line}: " if line else f"{file}: "
            return prefix + message
        return message
