# icinga2-linter
The Icinga 2 DSL linter checks Icinga config files for syntax errors, style issues, and potential misconfigurations in the domain-specific language.

## Help

[icinga2-lint]$ ./icinga2_linter.py 
Usage: ./icinga2_linter.py /path/to/conf.d

## Example

github/chrnie/icinga2-lint/icinga2_linter.py example_conf 
example_conf/hosts.conf:5: ERROR unbalanced quotes in object definition
example_conf/hosts.conf:8: ERROR 'ost' is not a valid object type.
example_conf/hosts.conf:13: ERROR unbalanced quotes
example_conf/hosts.conf:14: ERROR invalid attribute syntax: ')'
example_conf/hosts.conf:12: ERROR unclosed bracket '{'
example_conf/hosts2.conf:7: ERROR unbalanced quotes in multiline structure
example_conf/hosts2.conf:14: ERROR unbalanced quotes in multiline structure
example_conf/hosts2.conf:29: ERROR unbalanced quotes
example_conf/hosts2.conf:39: ERROR 'apply Dependency' must include 'to Host' or 'to Service'.
⚠️ 💩  9 issues found.