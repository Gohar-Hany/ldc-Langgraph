# Enterprise Password & Multi-Factor Authentication (MFA) Policy

## Overview
This document defines corporate standards for password complexity, lifecycle rotation, and mandatory Multi-Factor Authentication (MFA) enforcement across all enterprise accounts.

## Password Requirements & Standards
All employee accounts must adhere to NIST 800-63B standards:
- **Minimum Length:** 14 characters for regular employees; 18 characters for privileged/admin accounts.
- **Complexity:** Must include at least 1 uppercase letter, 1 lowercase letter, 1 number, and 1 special symbol (`!@#$%^&*`).
- **Forbidden Passwords:** Common dictionary words, sequential characters (`123456`, `abcdef`), and personal details (birthdays, company name).
- **Expiration Policy:** Passwords expire automatically every 90 days. Users receive notification reminders starting 14 days prior to expiration.
- **History:** The last 10 previous passwords cannot be reused.

## Multi-Factor Authentication (MFA) Enforcement
MFA is mandatory on 100% of corporate identities for all internal and external service access.

### Supported MFA Methods
1. **Primary Method (Approved):** Microsoft Authenticator or Google Authenticator using Time-Based One-Time Passwords (TOTP) or Number Matching push prompts.
2. **Hardware Keys (Approved for Developers & Admins):** FIDO2 / YubiKey physical security keys.
3. **Restricted Method:** SMS verification is strictly deprecated and not permitted due to SIM-swapping vulnerabilities.

### Setting Up a New Authenticator Device
1. Visit the corporate identity portal: `https://identity.enterprise.corp/mfa/setup`.
2. Authenticate using your initial temporary password provided by HR.
3. Scan the QR code using your mobile Authenticator app.
4. Enter the 6-digit confirmation token.
5. Save the 10 one-time emergency recovery codes in a secure location (such as corporate 1Password vault).

## Self-Service Password Reset (SSPR)
If you forget your password:
1. Navigate to `https://reset.enterprise.corp`.
2. Enter your corporate email address.
3. Complete two separate verification steps (e.g., Authenticator push prompt + verification code sent to registered secondary phone).
4. Enter a new password that meets complexity standards.
5. Account unlocks immediately across all SSO integrations within 60 seconds.

## Account Lockout Policy
- An account locks automatically after **5 consecutive failed password attempts**.
- Lockout duration is **30 minutes**.
- For immediate emergency unlock, contact the IT Helpdesk or request a Senior Agent / Admin unlock.
