# Copyright (c) 2022 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the COPYING file.
import re
from cloudvision.cvlib import ActionFailed

api_token = ''
server1 = 'https://www.cv-prod-na-northeast1-b.arista.io'

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
####

cmds = ["enable", "show mlag detail", "show lldp neighbors detail", "show ip bgp neighbors vrf all", "show interfaces status", "show hostname"]
commands = ctx.runDeviceCmds(cmds, fmt="json")
### MLAG
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
### LLDP
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
### Intf Status
for interface in intfStatusRaw:
    multiLaneIntf = r'Ethernet[0-9]{1}\/|Ethernet1[0-9]{1}\/|Ethernet20\/'
    singleLaneIntf = r'Ethernet[0-9]{1}$|Ethernet1[0-9]{1}$|Ethernet20$'
    if re.search(multiLaneIntf,interface):
      if intfStatusRaw[interface]["linkStatus"] == 'connected':
        intfParsed.append(interface)
    elif re.search(singleLaneIntf,interface):
      if intfStatusRaw[interface]["linkStatus"] == 'connected':
        intfParsed.append(interface)
### BGP
bgpRaw = commands[3]["response"]["vrfs"]
vrfRouterIDs = []
pfxAccepted = []
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
      #if bgpLocalRouterID == '0.0.0.0':
      #  bgpLocalRouterID = peer["localRouterId"]
      #elif bgpLocalRouterID == peer["localRouterId"]:
      #  pass
  #if bgpLocalRouterID != '0.0.0.0':
    #if mlagPeer != 'spineTemp':
    #  bgpRouterIDs.append({bgpLocalRouterID: "0"})
  vrfRouterIDs.append({"vrf": vrf, "routerIDs": bgpRouterIDs})
## Collect results
selfResult = {"mlag": mlagState, "selfHostname": hostname, "peerHostname": mlagPeer, "lldp": lldpPairs, "bgp": vrfRouterIDs, "intfStatus": intfParsed}
#PeerResult = ctx.retrieve(path=['compliance'],customKey=hostname)
#PeerResult = ctx.retrieve(path=['compliance'],customKey=hostname, delete=False)
PeerResult1 = get_configlet_by_name(server1,hostname)['config']
PeerResult = json.loads(PeerResult1.replace('\'','\"'))

if not PeerResult:
  raise ActionFailed(f"Peer result for {mlagPeer} not found")

lldpCheck = set(selfResult['lldp']) == set(PeerResult['lldp'])
if not lldpCheck:
  raise ActionFailed(f'lldp check failed.\nPeer: {PeerResult['lldp']}\nSelf: {result['lldp']}')
if str(selfResult['bgp']) == str(PeerResult['bgp']):
  pass
else:
  raise ActionFailed(f'bgp check failed.\nPeer: {PeerResult['bgp']}\nSelf: {result['bgp']}')
intfCheck = len(selfResult['intfStatus']) == len(PeerResult['intfStatus'])
if not intfCheck:
  raise ActionFailed(f'interface check failed.\nPeer: {PeerResult['intfStatus']}\nSelf: {result['intfStatus']}')

#ctx.info(f"{PeerResult}")
ctx.info(f"{'All checks passed.'}")
