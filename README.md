# icinga2-linter
The Icinga 2 DSL linter checks Icinga config files for syntax errors, style issues, and potential misconfigurations in the domain-specific language.

## Help
```
[icinga2-lint]$ ./icinga2_linter.py
Usage: ./icinga2_linter.py /path/to/conf.d [--debug]
```
## Example

```
github/chrnie/icinga2-lint/icinga2_linter.py example_conf 

example_conf/errors/hosts.conf:15: ERROR unclosed bracket '{'
example_conf/errors/hosts2.conf:7: ERROR unbalanced quotes
example_conf/errors/hosts2.conf:39: ERROR 'apply Dependency "Däpp"' must be followed by 'to Service' or 'to Host'
example_conf/errors/notification.conf:1: ERROR 'apply Notification "mail-icingaadmin"' must be followed by 'to Service' or 'to Host'
example_conf/errors/time.conf:1: ERROR Duplicate TimePeriod name '"9to5"' (previously defined at example_conf/zones.d/global-templates/timeperiods.conf:19)
⚠️ 💩  5 issues found.
```