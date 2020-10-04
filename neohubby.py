

# MIT License

"""Python package for dealing with Heatmiser Neohub."""


import json, socket


class Sender:

  def send(self, msg: dict):
    raise NotImplementedError


class SocketSender(Sender):

  def __init__(self, host, port):
    self._sock = socket.create_connection((host, port), timeout=5)

  def send(self, msg: dict):
    d = json.dumps(msg)
    payload = '{}\0\r'.format(d).encode('ascii')
    print([payload])
    self._sock.send(payload)
    r = self._recvall()
    print([r])
    return json.loads(r.strip())

  def _recvall(self):
    fragments = []
    while True: 
      chunk = self._sock.recv(4096)
      print([chunk])
      if chunk == b'\0': 
        break
      fragments.append(chunk)
    return b''.join(fragments)


class LoggingSender(Sender):

  def __init__(self):
    self.log = []

  def send(self, msg: dict):
    self.log.append(msg)

  

class Hub:

  def __init__(self, sender: Sender):
    """Create a new Hub"""
    self.sender = sender

  def send(self, msg):
    """Send a single message to the server."""
    return self.sender.send(msg)

  def get_zones(self):
    """GET_ZONES command.

    No arguments.

    Reference:

    {"GET_ZONES":0} returns the zone name and ID number of all Neostats
    {"Bathroom": 1,"Room name ": 2,"Office": 3,"plug": 4}
    """
    return self.send({'GET_ZONES': 0})

  def get_devices(self):
    """GET_DEVICES command

    No arguments.

    {"GET_DEVICES":0} returns a list of all devices except Neostats
    {"result": ["plug"]}

    """
    return self.send({'GET_DEVICES': 0})

  def get_device_list(self, room_name):
    """GET_DEVICE_LIST command

    Args:
      room_name: the name of the room

    {"GET_DEVICE_LIST":"room name"} returns a list of all devices except Neostats
    {"room name": []} 

    """
    return self.send({'GET_DEVICE_LIST': room_name})

  def permit_join(self, zone_name, timeout=120):
    """PERMIT_JOIN command

    Most devices are added to the system using the standard command.

    {"PERMIT_JOIN":[120,"kitchen"]}
    {'result': 'network allows joining'}

    In this case you have 120 seconds to pair the device you want to call
    kitchen.  The device will show up as a zone in the get Zones list or a
    device in the Get Devices list.
    """
    return self.send({'PERMIT_JOIN': [timeout, zone_name]})

  def get_profile_names(self) -> list:
    """GET_PROFILE_NAMES command

    No arguments.

    {"GET_PROFILE_NAMES":0} returns a list of thermostat profile names.

    {'result': ['Cool', 'General', 'Hot']}

    For some amazing reason using 'result', which we remove.
    """
    return self.send({'GET_PROFILE_NAMES': 0}).get('result')

  def get_profiles(self):
    """GET_PROFILES command

    No arguments.

    To load a complete list of all profiles stored on the Neohub use the GET
    PROFILES command {"GET_PROFILES":0} which returns all the thermostat
    profiles complete with names and profile ids {"my profile": {"PROFILE_ID":
    25,"info": {"monday": {"leave": ["09:30",17],"return": ["17:30",25],"sleep":
    ["22:30",15],"wake": ["07:00",14]},"sunday": {"leave":
    ["09:30",17],"return": ["17:30",21],"sleep": ["22:30",15],"wake":
    ["07:00",21]}},"name": "my profile"}}

    """
    return self.send({'GET_PROFILES': 0})
    
  def get_profile(self, profile_name: str):
    """GET_PROFILE command

    Args:
      profile_name the name of the profile.

    {"GET_PROFILE":"kitchen"} returns the named profile.
    """
    return self.send({'GET_PROFILE': profile_name})

  def get_profile_0(self, zone_name: str):
    """GET_PROFILE_0 command

    Args:
      zone_name: zone or device name.
    """
    return self.send({'GET_PROFILE_0': zone_name})

  def run_profile_id(self, profile_id: int, zones: [str]):
    """RUN_PROFILE_ID command

    RUN_PROFILE_ID {“RUN_PROFILE_ID”:[25,"Kitchen","Lounge"]} which will make
    the Neohub send the complete profile to each Neostat named in the command.
    The Neostats will report the profile id they are using in the live data
    field. Eliminating the need to send the full profile more than once to the
    App. 

    Ali: Amazingly you need the profile ID, not just the name, unlike all the
    other commands.
    """
    return self.send({'RUN_PROFILE_ID': [profile_id] + zones})

  def zone_title(self, old_title, new_title):
    """ZONE_TITLE command
    
    Args:
      old_title the original name
      new_title the name to change to

    Used to change the room name after installation
    {"ZONE_TITLE":["HCtest","HCtest2"]} 
    """
    return self.send({'ZONE_TITLE': [old_title, new_title]})

  def get_live_data(self):
    """GET_LIVE_DATA command

    The live data array contains up to the minute status information about the
    thermostats and the timestamps for all the caches.
    
    No arguments.
    """
    return self.send({'GET_LIVE_DATA': 0})


  def info(self):
    """INFO command

    No arguments.
    """
    return self.send({'INFO': 0})
    



def new_hub(host, port=4242):
  return Hub(SocketSender(host, port))

  


if __name__ == '__main__':
  h = new_hub('10.0.0.30')
  #p = h.get_zones()
  #p = h.get_live_data()
  #print(p)
  #print(p.keys())
  #print(p['devices'][0].keys())

  #d = p['devices'][0]

  #print(d['ZONE_NAME'])
  #print(d['ACTIVE_PROFILE'])
  #for z in p:
  #  print(z)

  #h.zone_title('Bedroom 3 Ensuite', 'Haeideh Ensuite')
  #r = h.run_profile_id(p, ['Office'])
  #print(r)

  #p = h.get_profile_0('Kitchen')

  p = h.info()
  print(p)

