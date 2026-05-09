# Fix GitHub Workspace / github.dev Empty Page Issue on Windows 11 via Android Hotspot

## Problem

While opening a GitHub workspace URL such as:

```txt
https://improved-train-xrwqgp9rg7wg2vggj.github.dev/?editor=web
```

the page stays blank and Chrome DevTools console shows errors like:

```txt
assets.github.dev/static/primer.css:1 Failed to load resource: net::ERR_NAME_NOT_RESOLVED
assets.github.dev/static/splash-screen-styles.css:1 Failed to load resource: net::ERR_NAME_NOT_RESOLVED
commons-bootstrap~pfHelper-index.js.7e7a315c8cee92c7da56.js:1 Failed to load resource: net::ERR_NAME_NOT_RESOLVED
```

---

# Observed Network Logs

## Ping Result

```cmd
C:\Users\Manoj>ping improved-train-xrwqgp9rg7wg2vggj.github.dev

Pinging vsapi-cluster-prod-rel-web-perf-tm.trafficmanager.net [64:ff9b::142b:b90e] with 32 bytes of data:
Reply from 64:ff9b::142b:b90e: time=119ms
Reply from 64:ff9b::142b:b90e: time=126ms
Reply from 64:ff9b::142b:b90e: time=94ms
Reply from 64:ff9b::142b:b90e: time=138ms

Ping statistics for 64:ff9b::142b:b90e:
    Packets: Sent = 4, Received = 4, Lost = 0 (0% loss),
Approximate round trip times in milli-seconds:
    Minimum = 94ms, Maximum = 138ms, Average = 119ms
```

---

## NSLookup Result

```cmd
C:\Users\Manoj>nslookup improved-train-xrwqgp9rg7wg2vggj.github.dev

Server:  UnKnown
Address:  172.26.130.112

Non-authoritative answer:
Name:    vsapi-cluster-prod-rel-web-perf-tm.trafficmanager.net
Addresses:  64:ff9b::142b:b90e
          20.43.185.14
Aliases:  improved-train-xrwqgp9rg7wg2vggj.github.dev
```

---

# Root Cause

This issue is usually caused by:

- Android mobile hotspot networking
- Carrier DNS issues
- Broken IPv6 routing
- NAT64/DNS64 translation problems
- Mobile ISP incompatibility with GitHub Codespaces/github.dev

The important clue is:

```txt
64:ff9b::142b:b90e
```

The `64:ff9b::/96` range is a NAT64 translation prefix.

This means:

- the mobile carrier is translating IPv4 into IPv6
- Chrome/browser resources fail resolving properly
- GitHub assets fail loading
- page becomes blank

---

# Why VPN Fixes It

VPN bypasses:

- carrier DNS
- carrier IPv6 routing
- NAT64 translation layer

So GitHub assets load correctly.

This confirms the issue is network-related rather than browser-related.

---

# Permanent Fixes

---

# Fix 1 — Change DNS Servers on Windows (Recommended)

## Step 1 — Open Network Adapter Settings

Press:

```txt
Win + R
```

Type:

```txt
ncpa.cpl
```

Press Enter.

---

## Step 2 — Configure IPv4 DNS

1. Right-click `Wi-Fi`
2. Select `Properties`
3. Double-click:

```txt
Internet Protocol Version 4 (TCP/IPv4)
```

4. Select:

```txt
Use the following DNS server addresses
```

### Use Cloudflare DNS

```txt
Preferred DNS: 1.1.1.1
Alternate DNS: 1.0.0.1
```

OR use Google DNS:

```txt
Preferred DNS: 8.8.8.8
Alternate DNS: 8.8.4.4
```

---

## Step 3 — Configure IPv6 DNS

Open:

```txt
Internet Protocol Version 6 (TCP/IPv6)
```

Use Cloudflare IPv6 DNS:

```txt
2606:4700:4700::1111
2606:4700:4700::1001
```

OR Google IPv6 DNS:

```txt
2001:4860:4860::8888
2001:4860:4860::8844
```

Click OK.

---

# Fix 2 — Flush DNS and Reset Network Stack

Open Command Prompt as Administrator and run:

```cmd
ipconfig /flushdns
netsh winsock reset
netsh int ip reset
```

Restart the computer.

---

# Fix 3 — Disable IPv6 (Most Effective)

Many mobile carriers in India have unstable IPv6 routing for developer domains.

## Steps

1. Press:

```txt
Win + R
```

2. Type:

```txt
ncpa.cpl
```

3. Open Wi-Fi Properties
4. Uncheck:

```txt
Internet Protocol Version 6 (TCP/IPv6)
```

5. Click OK
6. Reconnect hotspot

---

# Fix 4 — Disable Secure DNS in Chrome

Sometimes Chrome DNS-over-HTTPS conflicts with mobile carrier DNS.

Open:

```txt
chrome://settings/security
```

Disable:

```txt
Use secure DNS
```

OR manually choose:

```txt
Cloudflare
```

Restart Chrome.

---

# Fix 5 — Change Android APN to IPv4 Only

Some mobile carriers use problematic IPv6 APN configurations.

## Android Steps

1. Open:

```txt
Settings → Mobile Network → Access Point Names (APN)
```

2. Edit current APN
3. Find:

```txt
APN protocol
```

4. Change:

```txt
IPv4/IPv6
```

TO:

```txt
IPv4
```

5. Save APN
6. Restart mobile data
7. Reconnect hotspot

---

# Fix 6 — Verify DNS Resolution

Run:

```cmd
nslookup assets.github.dev
```

Expected:
- valid IPv4 addresses

Bad sign:
- only `64:ff9b::` addresses appear

---

# Recommended Order

Apply fixes in this order:

1. Change DNS to Cloudflare
2. Disable IPv6 on Windows
3. Flush DNS
4. Reconnect hotspot
5. Restart Chrome

This usually permanently fixes:

- GitHub Codespaces
- github.dev
- VS Code Web
- remote developer environments

without requiring VPN.

---

# Commonly Affected Networks

This issue is common on:

- Jio
- Airtel
- CGNAT mobile networks
- IPv6-heavy carrier infrastructure

---

# Useful Diagnostic Commands

## Check DNS Resolution

```cmd
nslookup github.dev
```

---

## Check Network Path

```cmd
ping github.dev
```

---

## View Current IP Configuration

```cmd
ipconfig /all
```

---

## Check Active Routes

```cmd
route print
```

---

# Alternative Workarounds

If issue still exists:

- use USB tethering instead of WiFi hotspot
- try another browser (Firefox/Edge)
- switch mobile carrier temporarily
- disable antivirus network filtering
- use Cloudflare WARP
- use VPN as fallback

---

# Final Conclusion

If VPN fixes the issue, then the problem is almost certainly:

- mobile carrier DNS
- IPv6 routing
- NAT64/DNS64 incompatibility

The most effective permanent fix is:

- disable IPv6
- switch to Cloudflare DNS
- use IPv4 APN configuration

These changes usually solve GitHub Codespaces/github.dev blank page issues permanently.
