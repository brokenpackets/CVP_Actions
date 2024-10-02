# Copyright (c) 2022 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the COPYING file.
import re
###### User Variables
api_token = ''
server1 = 'https://www.cv-prod-na-northeast1-b.arista.io'
######

def is_even(c):
    """Helper function to check if a character is even.
       For digits: '0', '2', '4', '6', '8' are even.
       For letters: 'b', 'd', 'f', ... (every second letter) are even."""
    if c.isdigit():
        return int(c) % 2 == 0
    elif c.isalpha():
        return (ord(c.lower()) - ord('a')) % 2 == 1  # Even-indexed letters (b, d, f, etc.)
    return False

def increment_char(c):
    """Helper to increment a character (digit or letter)."""
    if c.isdigit():
        return str(int(c) + 1)
    elif c.isalpha():
        return 'a' if c == 'z' else chr(ord(c) + 1)
    return c

def decrement_char(c):
    """Helper to decrement a character (digit or letter)."""
    if c.isdigit():
        return str(int(c) - 1) if c != '0' else '9'
    elif c.isalpha():
        return 'z' if c == 'a' else chr(ord(c) - 1)
    return c

def modify_last_char(c):
    """Modify the last character based on whether it's even or odd."""
    if is_even(c):
        # If it's even, decrement the character
        return decrement_char(c)
    else:
        # If it's odd, increment the character
        return increment_char(c)

def add_next_letter_or_number(hostname):
    # Split the hostname by '.' and focus only on the first part
    first_part = hostname.split('.')[0]

    # Match if the first part ends with a letter or number
    match = re.search(r'([a-z0-9]+)$', first_part, re.IGNORECASE)
    if match:
        last_sequence = match.group(1)
       
        # Handle numbers separately if the last part is purely digits
        if last_sequence.isdigit():
            new_sequence = str(int(last_sequence) + 1)  # Increment the full number
        else:
            # Handle letter or number at the end
            last_char = last_sequence[-1]
            new_char = modify_last_char(last_char.lower())
            # Replace only the last character
            new_sequence = last_sequence[:-1] + new_char

        # Replace the last sequence with the modified one
        new_first_part = first_part[:-len(last_sequence)] + new_sequence

        # Return the first part of the modified hostname
        return new_first_part
    else:
        return first_part  # Return original first part if no match

cmds = ["enable", "show mlag detail", "show lldp neighbors detail", "show ip bgp neighbors vrf all", "show interfaces status", "show hostname"]
commands = ctx.runDeviceCmds(cmds, fmt="json")
mlagRaw = commands[1]["response"]
peerMac = 'xxxxxxxx'
mlagState = 'null'
try:
  mlagState = mlagRaw["negStatus"]
  if mlagState == 'connected':
    peerMac = mlagRaw['detail']['peerMacAddress'].replace(':','')
except:
  pass
hostname = commands[5]["response"]["hostname"]
lldpRaw = commands[2]["response"]["lldpNeighbors"]
lldpPairs = []
peerHostname = 'xxxxxxxx'
for intf in lldpRaw:
  if intf.startswith('Ethernet'):
    lldpPeer = lldpRaw[intf]["lldpNeighborInfo"]
    if lldpPeer:
      try:
        lldpPeername = lldpRaw[intf]["lldpNeighborInfo"][0]['systemName']
        if lldpRaw[intf]["lldpNeighborInfo"][0]["chassisId"].replace('.','') == peerMac:
          peerHostname = lldpRaw[intf]["lldpNeighborInfo"][0]["systemName"]
        if lldpPeername.startswith(hostname[0:6]):
          if lldpPeername.startswith(peerHostname):
            pass
          else:
            lldpPairs.append(lldpPeername)
      except:
        pass
if peerHostname == 'xxxxxxxx':
  mlagPeer = 'spineTemp'
else:
  mlagPeer = peerHostname
intfStatusRaw = commands[4]["response"]["interfaceStatuses"]
intfParsed = []
for interface in intfStatusRaw:
    multiLaneIntf = r'Ethernet[0-9]{1}\/|Ethernet1[0-9]{1}\/|Ethernet20\/'
    singleLaneIntf = r'Ethernet[0-9]{1}$|Ethernet1[0-9]{1}$|Ethernet20$'
    if re.search(multiLaneIntf,interface):
      if intfStatusRaw[interface]["linkStatus"] == 'connected':
        intfParsed.append(interface)
    elif re.search(singleLaneIntf,interface):
      if intfStatusRaw[interface]["linkStatus"] == 'connected':
        intfParsed.append(interface)
bgpRaw = commands[3]["response"]["vrfs"]
vrfRouterIDs = []
for vrf in bgpRaw:
  vrfName = vrf
  peerList = bgpRaw[vrf]['peerList']
  bgpRouterIDs = []
  bgpLocalRouterID = '0.0.0.0'
  for peer in peerList:
      if peer["routerId"] == "0.0.0.0":
        pass
      elif peer["localAsn"] == peer['asn']:
        pass
      else:
        pfxReceived = peer['prefixesReceived']
        bgpRouterIDs.append({peer["routerId"]: pfxReceived})
      if bgpLocalRouterID == '0.0.0.0':
        bgpLocalRouterID = peer["localRouterId"]
      elif bgpLocalRouterID == peer["localRouterId"]:
        pass
  #if bgpLocalRouterID != '0.0.0.0':
    #if mlagPeer != 'spineTemp':
    #  bgpRouterIDs.append({bgpLocalRouterID: "0"})
  vrfRouterIDs.append({"vrf": vrf, "routerIDs": bgpRouterIDs})

if mlagPeer == 'spineTemp':
  mlagPeer = add_next_letter_or_number(hostname)

result = {"mlag": mlagState, "selfHostname": hostname, "peerHostname": mlagPeer, "lldp": lldpPairs, "bgp": vrfRouterIDs, "intfStatus": intfParsed}
##ctx.info(f"{result}")
##ctx.store(result,path=['compliance'],customKey=mlagPeer)

### Shim to work on 2023.1.3

#!/usr/bin/env python
import requests
import json

requests.packages.urllib3.disable_warnings()
session = requests.Session()
session.headers['Authorization'] = f"Bearer {api_token}"
def get_configlet_by_name(url_prefix,configlet_name):
  response = session.get(url_prefix+'/cvpservice/configlet/getConfigletByName.do?name='+configlet_name)
  return response.json()

def update_configlet(url_prefix,configlet_key,configlet_name,configlet_body):
  tempData = json.dumps({
  "config": configlet_body,
  "key": configlet_key,
  "name": configlet_name,
  "reconciled": False,
  "waitForTaskIds": False
  })
  response = session.post(url_prefix+'/cvpservice/configlet/updateConfiglet.do', data=tempData)
  #return tempData
  return response.json()

def add_configlet(url_prefix,configlet_name,configlet_body):
  tempData = json.dumps({
          "config": configlet_body,
          "name": configlet_name
  })
  response = session.post(url_prefix+'/cvpservice/configlet/addConfiglet.do', data=tempData)
  #return tempData
  return response.json()

configlet_name = mlagPeer
configlet_body = str(result)
output = add_configlet(server1,configlet_name,configlet_body)
if output == {'errorCode': '132518', 'errorMessage': 'Data already exists in Database'}:
  configlet_key = get_configlet_by_name(server1,mlagPeer)['key']
  output2 = update_configlet(server1,configlet_key,configlet_name,configlet_body)
ctx.info(f"{result}")
