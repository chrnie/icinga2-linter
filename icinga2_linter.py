#!/usr/bin/env python3

import os
import sys
import re
import difflib  # Import for similarity checking
from parse import Icinga2Parser  # Import the parser

# Keywords and valid object types
KEYWORDS = {"object", "apply", "template"}
VALID_OBJECT_TYPES = {
    "ApiUser", "CheckCommand", "Dependency", "Endpoint", "EventCommand",
    "Host", "HostGroup", "Notification", "NotificationCommand", "ScheduledDowntime",
    "Service", "ServiceGroup", "Timeperiod", "User", "UserGroup", "Zone",
    "Comment", "Downtime", "ApiListener", "CheckerComponent", "CompatLogger", 
    "ElasticsearchWriter", "ExternalCommandListener", "FileLogger", "GelfWriter", 
    "GraphiteWriter", "IcingaApplication", "IcingaDB", "IdoMySqlConnection", 
    "IdoPgsqlConnection", "InfluxdbWriter", "Influxdb2Writer", "JournaldLogger", 
    "LiveStatusListener", "NotificationComponent", "OpenTsdbWriter", "PerfdataWriter", 
    "SyslogLogger", "WindowsEventLogLogger"
}

SPECIAL_KEYWORDS = {"import", "assign", "ignore"}  # Special keywords that don't require an operator

def suggest_correction(word, valid_words):
    """Suggest the closest valid word for a given word."""
    suggestions = difflib.get_close_matches(word, valid_words, n=1, cutoff=0.8)
    return suggestions[0] if suggestions else None

def is_quotes_balanced(line):
    """Check if quotes (single and double) are balanced, considering escaping and nesting."""
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

def lint_file(path):
    issues = []
    lineno = 0
    brace_stack = []
    lines = []

    with open(path, 'r') as f:
        lines = f.readlines()

    parser = Icinga2Parser()
    constants = []

    inside_object = False
    inside_multiline_structure = False
    multiline_structure_type = None

    for i, line in enumerate(lines):
        lineno = i + 1
        stripped = line.strip()

        # Skip empty and comment lines
        if not stripped or stripped.startswith("//"):
            continue

        # 1. Loosen object definition check
        if not inside_object and not inside_multiline_structure:
            tokens = stripped.split()
            if tokens:
                first_token = tokens[0]
                if first_token in KEYWORDS:
                    if len(tokens) > 1:
                        object_type = tokens[1].strip('"')
                        if object_type not in VALID_OBJECT_TYPES:
                            issues.append(f"{path}:{lineno}: ERROR '{object_type}' is not a valid object type.")
                        if first_token == "apply" and object_type in {"Dependency", "Notification"}:
                            if not ("to Host" in stripped or "to Service" in stripped):
                                issues.append(f"{path}:{lineno}: ERROR 'apply {object_type}' must include 'to Host' or 'to Service'.")
                    if not is_quotes_balanced(stripped):
                        issues.append(f"{path}:{lineno}: ERROR unbalanced quotes in object definition")
                    if "{" in stripped:
                        inside_object = True
                        brace_stack.append(("{", lineno))
                        extra_opens = stripped.count("{") - 1
                        for _ in range(extra_opens):
                            brace_stack.append(("{", lineno))
                        continue
                    else:
                        suggestion = suggest_correction(first_token, KEYWORDS)
                        if suggestion:
                            issues.append(f"{path}:{lineno}: WARN '{first_token}' is not a valid keyword. Did you mean '{suggestion}'?")
                        else:
                            issues.append(f"{path}:{lineno}: ERROR '{first_token}' is not a valid keyword.")
                        continue

        # 2. Track opening and closing braces/brackets to determine object or structure boundaries
        open_curly = stripped.count("{")
        close_curly = stripped.count("}")
        open_square = stripped.count("[")
        close_square = stripped.count("]")
        open_paren = stripped.count("(")
        close_paren = stripped.count(")")

        # Add for multiline structures (arrays/dicts) and nested objects
        for _ in range(open_square):
            brace_stack.append(("[", lineno))
            inside_multiline_structure = True
            multiline_structure_type = "array"
        for _ in range(open_curly):
            brace_stack.append(("{", lineno))
            if not inside_object:
                inside_multiline_structure = True
                multiline_structure_type = "dict"

        for _ in range(close_square):
            if brace_stack and brace_stack[-1][0] == "[":
                brace_stack.pop()
            else:
                # If mismatch, warn about expected ']' but found something else
                issues.append(f"{path}:{lineno}: ERROR mismatched bracket: expected ']'")

        for _ in range(close_curly):
            if brace_stack:
                if brace_stack[-1][0] == "{":
                    brace_stack.pop()
                else:
                    # Mismatched bracket: we expected ']', found '}'
                    issues.append(f"{path}:{lineno}: ERROR mismatched bracket: expected ']' but found '}}'")
            # If the last '{' was the object, end object
            if not brace_stack and inside_object:
                inside_object = False
                inside_multiline_structure = False
                multiline_structure_type = None

        # Ensure multiline structures are properly closed
        if inside_multiline_structure and multiline_structure_type == "array" and not brace_stack:
            issues.append(f"{path}:{lineno}: ERROR unclosed array structure")
        elif inside_multiline_structure and multiline_structure_type == "dict" and not brace_stack:
            issues.append(f"{path}:{lineno}: ERROR unclosed dictionary structure")

        # Right after we detect we're inside_multiline_structure:
        if inside_multiline_structure:
            if not is_quotes_balanced(stripped):
                issues.append(f"{path}:{lineno}: ERROR unbalanced quotes in multiline structure")

        # 3. Validate attributes, keywords, and valid syntax inside objects or multiline structures
        if inside_object or inside_multiline_structure:
            tokens = stripped.split()
            if tokens:
                # Special check: 'import' must NOT have an operator
                if tokens[0] == "import" and re.search(r'\s*(=|\+=|-=|\*=|/=)\s*', stripped):
                    issues.append(f"{path}:{lineno}: ERROR 'import' must not be used with an operator")
                    continue
                if tokens[0] not in SPECIAL_KEYWORDS:
                    # Allow valid syntax for multiline structures
                    if inside_multiline_structure:
                        if multiline_structure_type == "array" and (stripped.endswith(",") or stripped.endswith("]") or stripped.startswith('"')):
                            continue
                        if multiline_structure_type == "dict" and (stripped.endswith(",") or stripped.endswith("}")):
                            continue
                        if not is_quotes_balanced(stripped):
                            issues.append(f"{path}:{lineno}: ERROR unbalanced quotes in multiline structure")
                    # Check for attribute assignment without value (e.g., dict =)
                    attr_assign = re.match(r'^([a-zA-Z_][a-zA-Z0-9_]*)\s*(=|\+=|-=|\*=|/=)\s*$', stripped)
                    if attr_assign:
                        issues.append(f"{path}:{lineno}: ERROR attribute '{attr_assign.group(1)}' assigned with operator '{attr_assign.group(2)}' but no value")
                        continue
                    # Check if the line contains a valid attribute with an operator
                    if not re.search(r'\s*(=|\+=|-=|\*=|/=)\s*', stripped) and not inside_multiline_structure:
                        issues.append(f"{path}:{lineno}: ERROR invalid attribute syntax: '{stripped}'")
                    else:
                        # Use the parser to validate the attribute syntax
                        try:
                            parsed_line = parser.parse({"dummy_key": stripped}, constants)  # Example usage
                        except Exception as e:
                            issues.append(f"{path}:{lineno}: ERROR parsing attribute failed: {e}")

        # 4. Quote check
        if not is_quotes_balanced(stripped):
            issues.append(f"{path}:{lineno}: ERROR unbalanced quotes")

    # 5. Unclosed brackets
    for open_char, open_line in brace_stack:
        issues.append(f"{path}:{open_line}: ERROR unclosed bracket '{open_char}'")

    return issues

def find_config_files(base_path):
    for root, _, files in os.walk(base_path):
        for file in files:
            if file.endswith(".conf"):
                yield os.path.join(root, file)

def run_linter(path):
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
        print("Usage: ./icinga2_linter.py /path/to/conf.d")
        sys.exit(1)

    run_linter(sys.argv[1])

