#!/usr/bin/env python3

import os
import sys
import re

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
    "SyslogLogger", "WindowseventlogLogger"
}

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

    expect_opening_brace = None

    for i, line in enumerate(lines):
        lineno = i + 1
        stripped = line.strip()

        # Skip empty and comment lines
        if not stripped or stripped.startswith("//"):
            continue

        # 1. Attributes must not end with a semicolon
        if stripped.endswith(";"):
            issues.append(f"{path}:{lineno}: ERROR attributes must not end with a semicolon")

        # 2. Line starts with keyword but isn't a valid object/apply/template
        tokens = stripped.split()
        if tokens:
            first_token = tokens[0]
            if first_token in KEYWORDS:
                if not re.match(rf'^{first_token}\s+\w+\s+".*"', stripped):
                    issues.append(f"{path}:{lineno}: WARN line starts with '{first_token}' but is not a valid definition")

                # Schedule brace check for next relevant line
                if "{" not in stripped:
                    expect_opening_brace = lineno

        # 3. Check next line after keyword line contains opening brace
        if expect_opening_brace and "{" in stripped:
            expect_opening_brace = None
        elif expect_opening_brace and not stripped.startswith("//") and stripped:
            issues.append(f"{path}:{expect_opening_brace}: ERROR missing opening '{{' after keyword declaration")
            expect_opening_brace = None

        # 4. Invalid object type
        match = re.match(r'^\s*object\s+(\w+)\s+"[^"]*"', stripped)
        if match:
            obj_type = match.group(1)
            if obj_type not in VALID_OBJECT_TYPES:
                issues.append(f"{path}:{lineno}: ERROR invalid object type '{obj_type}'")

        # 5. Bracket matching: {}, [], ()
        for char in stripped:
            if char in "{[(":
                brace_stack.append((char, lineno))
            elif char in "}])":
                if not brace_stack:
                    issues.append(f"{path}:{lineno}: ERROR unmatched closing bracket '{char}'")
                    continue
                open_char, open_line = brace_stack.pop()
                expected = {')': '(', ']': '[', '}': '{'}[char]
                if open_char != expected:
                    issues.append(f"{path}:{lineno}: ERROR mismatched bracket '{char}', expected '{expected}' from line {open_line}")

        # 6. Quote check
        if not is_quotes_balanced(stripped):
            issues.append(f"{path}:{lineno}: ERROR unbalanced quotes")

    # 7. Unclosed brackets
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
        print(f"⚠️  {total_issues} issues found.")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: ./icinga2_linter.py /path/to/conf.d")
        sys.exit(1)

    run_linter(sys.argv[1])

