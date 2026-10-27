---
name: users-and-presence
description: Set up family accounts and home/away presence in Home Assistant. Covers owner, admin and regular users, what Home Assistant can and can't restrict, keeping admin-only dashboards, linking phones to people for home/away, location permissions, and adding Wi-Fi presence from UniFi. Use when someone adds a partner or family member, asks about permissions, or sees "Select the devices that belong to this person".
---

# Users and presence

## Accounts

Settings → People → Add person → turn on "Allow person to login".
- **Owner:** the first account. Keep using it, or make a named admin account for daily use.
- **Administrator:** sees Settings and everything else.
- **Regular user:** no Settings menu, but **can still see and control every device**, and every dashboard that
  isn't admin-only.

Set expectations honestly: Home Assistant **has no per-device permissions**.
- **What you can do:** hide dashboards (the dashboard's `require_admin: true` setting) and keep risky things,
  such as the Network dashboard with power-cycle buttons, admin-only.
- **What you can't do:** a regular user can still use the entity search or the default dashboard.

## Presence ("Select the devices that belong to this person")

That screen is for **home/away**, not permissions. Pick the tracker that follows the person, which is usually
their phone.
1. Each person installs the **Home Assistant app** and logs in with **their own account**.
   - A phone logged in as someone else gets registered to that other account.
   - **To switch:** in the app, Settings → Companion app → server → Log out, then sign in again with the right
     account.
2. **Give each phone a clear name:** set the device name in the app, e.g. "<Name> iPhone". Otherwise two phones
   can show up with the same name.
3. **Allow location "Always"** with Precise Location on: iOS Settings → Home Assistant → Location.
   - With "While using", the tracker often reads "unknown".
4. **Link the phone to the person:** Settings → People → the person → choose their `device_tracker.<phone>`.
5. **Add Wi-Fi presence (optional):** add the phone's UniFi client tracker too.
   - Home Assistant combines the two, so a sleeping phone doesn't make someone look "away".
   - Turn off private Wi-Fi addresses for the home network on the phone, so UniFi sees the same MAC every time.

## Ideas once presence works

"Everyone left" (turn off lights, lock the door), "first person home after dark" (entry light on), and a
"who's home" tile on the dashboard.
