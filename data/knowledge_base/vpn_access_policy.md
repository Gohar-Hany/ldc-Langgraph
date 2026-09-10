# Enterprise VPN Access Policy & Troubleshooting Guide

## Overview
This document outlines the corporate Virtual Private Network (VPN) connection standards, client setup instructions across operating systems, and common troubleshooting steps for all remote employees.

## Required VPN Client
The standard corporate VPN client is **GlobalProtect VPN** (version 6.1 or later). Alternative legacy client **Cisco AnyConnect** is strictly deprecated and restricted to legacy lab access.

## Client Setup by Operating System

### MacOS Configuration
1. Download GlobalProtect from the internal portal: `https://software.enterprise.corp/vpn/macos`.
2. Install the `.pkg` installer and approve the system extension in **System Settings > Privacy & Security**.
3. Launch GlobalProtect and enter the corporate portal address: `vpn.enterprise.corp`.
4. Sign in with your corporate SSO credentials (`username@enterprise.corp`) and complete Multi-Factor Authentication (MFA) via Authenticator push notification.
5. Once connected, the status icon will change to a blue globe with a shield.

### Windows 11 / Windows 10 Configuration
1. Open the **Company Portal** app and search for **GlobalProtect**. Click **Install**.
2. When prompted for the portal address, input: `vpn.enterprise.corp`.
3. Provide your corporate domain credentials and approve the MFA challenge.
4. Verify connection by pinging internal gateway: `ping gateway.internal.corp`.

### Linux (Ubuntu / Fedora) Configuration
1. Install the CLI or GUI package:
   ```bash
   sudo apt-get install globalprotect-openconnect
   ```
2. Connect using terminal command:
   ```bash
   gp-saml-gui --gateway --portal vpn.enterprise.corp
   ```
3. Complete browser authentication and export session cookies.

## Common Connection Errors & Resolution

### Error Code 0x80070005 (Access Denied)
- **Cause:** Expired client certificate or missing device compliance check.
- **Resolution:**
  1. Open GlobalProtect > **Settings > Certificates**.
  2. Click **Refresh Certificates**.
  3. Ensure your local machine has the latest OS security patches installed.
  4. Reboot your machine and retry connecting.

### Gateway Unreachable (Error 504)
- **Cause:** Local ISP blocking UDP port 4501 or corporate firewall throttling.
- **Resolution:**
  1. Open GlobalProtect Settings > **Connections**.
  2. Toggle **Force TCP Tunneling** to bypass ISP UDP throttling.
  3. Reconnect to portal `vpn.enterprise.corp`.

## Security & Usage Rules
- Split-tunneling is enabled by default: only internal subnets (`10.0.0.0/8` and `172.16.0.0/12`) route through the VPN.
- Maximum session lifetime is 12 hours. Users are automatically disconnected and must re-authenticate.
- Connecting through unapproved third-party commercial VPNs simultaneously is strictly prohibited.
