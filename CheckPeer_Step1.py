# Copyright (c) 2022 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the COPYING file.
import re

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

result = {"mlag": mlagState, "selfHostname": hostname, "peerHostname": mlagPeer, "lldp": lldpPairs, "bgp": vrfRouterIDs, "intfStatus": intfParsed}
ctx.info(f"{result}")
ctx.store(result,path=['compliance'],customKey=mlagPeer)
