# Copyright (c) 2022 Arista Networks, Inc.
# Use of this source code is governed by the Apache License 2.0
# that can be found in the COPYING file.

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
bgpRaw = commands[3]["response"]["vrfs"]["default"]["peerList"]
bgpRouterIDs = []
intfStatusRaw = commands[4]["response"]["interfaceStatuses"]
intfParsed = []
for interface in intfStatusRaw:
    if interface.startswith("Ethernet"):
      intfParsed.append({interface:intfStatusRaw[interface]["linkStatus"]})
for peer in bgpRaw:
    if peer["routerId"] == "0.0.0.0":
      pass
    else:
      bgpRouterIDs.append(peer["routerId"])
result = {"mlag": mlagState, "lldp": lldpPairs, "bgp": bgpRouterIDs, "intfStatus": intfParsed}
ctx.info(f"{result}")
ctx.store(result,path=['compliance'],customKey=mlagDomain)
