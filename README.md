# NeoHubby

**Python API for NeoHub heating controllers**

[Reference docs from Heatmizer](docs/Neohub_Api_For_Systems_Developers.pdf) (email support@heatmiser.com if you want a copy)

## Installation

```
$ pip install neohubby
```

## Getting started

```python
>>> import neohubby
>>> hub = neohubby.new_hub('10.0.0.30') # The address of your Hub
>>> print(hub.get_zones())

{'Bedroom 2': 9, 'Bedroom 2 Ensuite': 10, 'Breakfast': 7, 'Cloakroom': 20, ...}
```

## About this library

There are other libraries around which go to great extremes to be complicated, using async and other such stuff. This library has no external dependencies. It does need Python 3 though for the type annotations. Sorry about that. If you want Python2.7 you should just remove them and it should work.

## About the API

The API itself is somewhat bizarre. You send JSON over TCP without any sane wrapoping protocol, except you terminate your commands in `\0\r` i.e. a NULL byte and a carriage return. Responses are JSON terminated in the same way. This does have the nice advantage of being able to just use netcat to send commands for testing, though. E.g.

```
$ echo -e '{"GET_ZONES": 0}\0\r' | nc 10.0.0.30 4242

{"Bedroom 2":9,"Bedroom 2 Ensuite":10,"Breakfast":7,"Cloakroom":20...}
```