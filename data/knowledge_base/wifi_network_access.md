# Corporate Wi-Fi Network Access Policy & Configuration

## Overview
This document specifies the wireless network guidelines for on-premise office environments, defining access tiers, authentication protocols, and troubleshooting steps.

## Wireless Network Tiers

### 1. Corp-Secure (Employees Only)
- **SSID:** `Corp-Secure`
- **Security Protocol:** WPA3-Enterprise / 802.1X (EAP-TLS)
- **Access Scope:** Full access to intranet, internal repositories, print servers, and cloud resources.
- **Requirements:**
  - Corporate-managed laptop with installed root Certificate Authority (Enterprise-Root-CA).
  - Valid corporate user credentials.
  - Active EDR agent (CrowdStrike) running without critical alerts.

### 2. Corp-Guest (Visitors & Vendors)
- **SSID:** `Corp-Guest`
- **Security Protocol:** WPA2-Personal with Captive Portal
- **Access Scope:** Public Internet only. Complete isolation from internal corporate subnets.
- **Access Procedure:**
  1. Connect to `Corp-Guest`.
  2. Browser will redirect to `https://guest.enterprise.corp`.
  3. Enter visitor full name, email, and the email of the employee host.
  4. The host employee receives an approval email and clicks **Authorize Guest**.
  5. Access is granted for 8 hours.

## Setup Instructions for Corp-Secure

### MacOS Connection
1. Click the Wi-Fi menu bar icon and select `Corp-Secure`.
2. Enter your corporate email and password.
3. If prompted to accept the certificate `wifi-radius.enterprise.corp`, click **Show Certificate**, confirm issuer is **Enterprise-Root-CA**, and click **Continue**.

### Windows 11 Connection
1. Select `Corp-Secure` from the network flyout.
2. Check **Connect automatically** and click **Connect**.
3. Select **Use my Windows user account** or provide corporate domain credentials (`ENTERPRISE\username`).

## Troubleshooting Wi-Fi Issues

### Unable to Connect: Certificate Invalid Error
- **Cause:** Local certificate store missing latest intermediate certificate.
- **Fix:** Connect machine temporarily to Ethernet or mobile hotspot, launch **Company Portal**, select **Sync Device**, and restart network adapter.

### Low Bandwidth & Channel Interference
- All conference rooms feature dual-band 5GHz and 6GHz Wi-Fi 6E access points.
- If experiencing video lag, disable 2.4GHz on your Wi-Fi adapter to force 5GHz/6GHz connection.
