---
layout: layout.njk
permalink: config.html
eleventyNavigation:
  key: Configuration
  order: 3
templateEngineOverride: njk,md
---

# Bominade Configuration

Bominade can be configured using the configuration file, or by passing command
line options. They both have the same effect, although of course the config file
options are easier to maintain.

## Configuration file

The default config file is found at `~/.config/b8/b8.ini` which will be created
for you. If you have set a different user config directory according to XDG, the
file will be there instead.


You can choose a different location to find a config file by passing the
`--config` parameter, e.g.:

```bash
b8 --config=different-config.ini
```

The file itself is a standard ini file that follows the conventions of python's
configparser standard module which it uses.

## Configuration values

The list of options is gradually growing. Here are the defaults:

```ini
{{ 'exec python3 -c "import b8.configs; b8.configs.Config.generate_help()"' | exec | safe }}
```

## Command line options

The same configuration values can be passed on the command line, using
`--{section}-{name}` format, e.g.:

```bash
b8 --loging-level=error
```

Additionally there are a number of other flags that can be passed:


```text
$ b8 --help

{{ "b8 -h" | exec | safe }}
```

