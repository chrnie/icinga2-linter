#!/usr/bin/env python3

import os
import sys
import re
from parse import Icinga2Parser

# Keywords and valid object types
KEYWORDS = {"object", "apply", "template"}
VALID_OBJECT_TYPES = {
    "ApiUser", "CheckCommand", "Dependency", "Endpoint", "EventCommand",
    "Host", "HostGroup", "Notification", "NotificationCommand", "ScheduledDowntime",
    "Service", "ServiceGroup", "TimePeriod", "User", "UserGroup", "Zone",
    "Comment", "Downtime", "ApiListener", "CheckerComponent", "CompatLogger", 
    "ElasticsearchWriter", "ExternalCommandListener", "FileLogger", "GelfWriter", 
    "GraphiteWriter", "IcingaApplication", "IcingaDB", "IdoMySqlConnection", 
    "IdoPgsqlConnection", "InfluxdbWriter", "Influxdb2Writer", "JournaldLogger", 
    "LiveStatusListener", "NotificationComponent", "OpenTsdbWriter", "PerfdataWriter", 
    "SyslogLogger", "WindowsEventLogLogger"
}
VALID_ATTRIBUTES = {"vars", "assign", "ignore", "import", "ranges"}

# Helper functions
def is_quotes_balanced(line):
    """Check if quotes (single and double) are balanced."""
    in_single = False
    in_double = False
    escaped = False

    for char in line:
        if escaped:
            escaped = False
            continue
        if char == '\\':
            escaped = True
            continue
        if char == '"' and not in_single:
            in_double = not in_double
        elif char == "'" and not in_double:
            in_single = not in_single

    return not in_single and not in_double

def parse_line(line, brace_stack):
    """Parse a single line and update the brace stack."""
    open_curly = line.count("{")
    close_curly = line.count("}")
    open_square = line.count("[")
    close_square = line.count("]")

    for _ in range(open_curly):
        brace_stack.append("{")
    for _ in range(close_curly):
        if brace_stack and brace_stack[-1] == "{":
            brace_stack.pop()
        else:
            return False, "Mismatched closing '}'"

    for _ in range(open_square):
        brace_stack.append("[")
    for _ in range(close_square):
        if brace_stack and brace_stack[-1] == "[":
            brace_stack.pop()
        else:
            return False, "Mismatched closing ']'"

    return True, None

def lint_file(path):
    """Lint a single file."""
    issues = []
    brace_stack = []
    inside_multiline_comment = False
    lineno = 0

    with open(path, "r") as f:
        lines = f.readlines()

    for line in lines:
        lineno += 1
        stripped = line.strip()

        # Skip empty lines
        if not stripped:
            continue

        # Handle multiline comments
        if inside_multiline_comment:
            print(f"DEBUG: {path}:{lineno} Multiline comment continues")
            if "*/" in stripped:
                inside_multiline_comment = False
                print(f"DEBUG: {path}:{lineno} Multiline comment ends")
            continue
        if stripped.startswith("/*"):
            inside_multiline_comment = True
            print(f"DEBUG: {path}:{lineno} Multiline comment starts")
            if stripped.endswith("*/"):
                inside_multiline_comment = False
                print(f"DEBUG: {path}:{lineno} Multiline comment ends in the same line")
            continue

        # Skip single-line comments
        if stripped.startswith("//"):
            print(f"DEBUG: {path}:{lineno} Single-line comment (//) detected")
            continue
        if stripped.startswith("#"):
            print(f"DEBUG: {path}:{lineno} Single-line comment (#) detected")
            continue

        # Check for unbalanced quotes
        if not is_quotes_balanced(stripped):
            issues.append(f"{path}:{lineno}: ERROR unbalanced quotes")

        # Parse the line and update the brace stack
        success, error = parse_line(stripped, brace_stack)
        if not success:
            issues.append(f"{path}:{lineno}: ERROR {error}")

        # Debug output for multiline structures
        if brace_stack:
            print(f"DEBUG: {path}:{lineno} Multiline structure detected, current stack: {brace_stack}")

    # Check for unclosed brackets at the end of the file
    for char in brace_stack:
        issues.append(f"{path}:{lineno}: ERROR unclosed bracket '{char}'")

   
    return issues

def find_config_files(base_path):
    """Find all .conf files in the given directory."""
    for root, _, files in os.walk(base_path):
        for file in files:
            if file.endswith(".conf"):
                yield os.path.join(root, file)

def run_linter(path):
    """Run the linter on the given path."""
    if not os.path.isdir(path):
        print(f"Path not found: {path}")
        sys.exit(1)

    total_issues = 0
    for file in find_config_files(path):
        issues = lint_file(file)
        for issue in issues:
            print(issue)
            total_issues += 1

    if total_issues == 0:
        print("✅ No issues found.")
        sys.exit(0)
    else:
        print(f"⚠️ 💩  {total_issues} issues found.")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: ./icinga2_linter2.py /path/to/conf.d")
        sys.exit(1)

    run_linter(sys.argv[1])
