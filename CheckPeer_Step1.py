# Copyright (c) 2022 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the COPYING file.
import re

cmds = ["enable", "show mlag", "show lldp neighbors", "show ip bgp neighbors", "show interfaces status"]
commands = ctx.runDeviceCmds(cmds, fmt="json")
mlagRaw = commands[1]["response"]
try:
    mlagDomain = mlagRaw["domainId"]
except:
    mlagDomain = 'spineTemp'
mlagState = mlagRaw["state"]
lldpRaw = commands[2]["response"]["lldpNeighbors"]
lldpPairs = []
for intf in lldpRaw:
    lldpPeer = intf["neighborDevice"]
    lldpPairs.append(lldpPeer)
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
bgpRaw = commands[3]["response"]["vrfs"]["default"]["peerList"]
bgpRouterIDs = []
bgpLocalRouterID = '0.0.0.0'
for peer in bgpRaw:
    if peer["routerId"] == "0.0.0.0":
      pass
    else:
      bgpRouterIDs.append(peer["routerId"])
    if bgpLocalRouterID == '0.0.0.0':
      bgpLocalRouterID = peer["localRouterId"]
    elif bgpLocalRouterID == peer["localRouterId"]:
      pass
if bgpLocalRouterID != '0.0.0.0':
  if mlagDomain != 'spineTemp':
    bgpRouterIDs.append(bgpLocalRouterID)

result = {"mlag": mlagState, "lldp": lldpPairs, "bgp": bgpRouterIDs, "intfStatus": intfParsed}
ctx.info(f"{result}")
ctx.store(result,path=['compliance'],customKey=mlagDomain)
