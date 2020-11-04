---
layout: layout.njk
permalink: manual.html
eleventyNavigation:
  key: User Manual
  order: 2
templateEngineOverride: njk,md
---

# User Manual

## Running

Start the bominade by running it:

```
$ b8
```

You can open files by passing them as positional arguments on the command line:

```
$ b8 ~/src/b8/README.md ~/src/b8/tools/LICENSE
```

## Remote

You can open files in an existing instance of b8 by using the `--remote` flag.
This will not start a new b8 instance, but communicate with existing instance.

```
$ b8 --remote ~/src/b8/README.md ~/src/b8/tools/LICENSE
```

For additional configuration options, please see the
[configuration](/config.html) page.

## Keyboard Shortcuts

The following actions are available at the top-level. You can modify them in the
[configuration](/config.html).

| Key Press 	| Action            	|
|-----------	|-------------------	|
| `Alt-Up`    | Previous Buffer   	|
| `Alt-Down`  | Next Buffer       	|
| `Alt-Right` | Previous Terminal 	|
| `Alt-Left`  | Next Terminal     	|
| `Alt-t`     | New Terminal      	|


