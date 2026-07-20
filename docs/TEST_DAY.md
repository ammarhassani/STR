# Multi-PC test day

One page. Take it with you.

---

## Before you leave this PC

- [ ] `build.bat` → says **Build OK**
- [ ] Run `deploy\grant_share_access.ps1` as admin, set a real password
- [ ] Write the password here: ________________
- [ ] Panel → **Build client folder** → copy `STR_Client` to a USB stick
- [ ] Panel → **Start host on this PC**
- [ ] Panel top box says **Everything is working**

---

## On the client PC

- [ ] Copy `STR_Client` to `C:\STR`
- [ ] Double-click `FIU_System.exe`
- [ ] Enter credentials if asked (`ENGAMMARPC\STR_client`)
- [ ] Log in
- [ ] You can see reports

**If it asks to set up a database → it can't reach the share. Paste
`\\ENGAMMARPC\STR_data` into File Explorer and see what it says.**

---

## The things actually worth testing

These are the unknowns. Everything else is already proven.

### 1. Does it survive a normal day?
- [ ] Leave both PCs on for a few hours with the app open
- [ ] Come back → still working? Or did it go stale/disconnect?

### 2. Antivirus
This is the most likely thing to break it.
- [ ] Save several reports in a row on the client
- [ ] Any errors about files being in use or access denied?
- [ ] If yes → note the exact message

### 3. Two people at once
- [ ] Client PC and host PC both create a report at the same time
- [ ] Both saved? Both get different report numbers?

### 4. The network drops
- [ ] Unplug the client's network cable (or disable Wi-Fi)
- [ ] Try to save a report → what does it say?
- [ ] Plug it back in → does the saved work arrive?

**This is the important one.** It should queue and catch up, not lose work.

### 5. The host stops mid-work
- [ ] On the client, start writing a report
- [ ] On the host, panel → **Stop host**
- [ ] Try to save on the client → what happens?
- [ ] Panel → **Start host on this PC**
- [ ] Does the client recover on its own?

### 6. Speed
- [ ] Open the reports list → instant, or a wait?
- [ ] Save a report → how long?
- [ ] Note anything that feels slow

---

## What to write down

For anything that goes wrong:

1. Which PC
2. What you pressed
3. The **exact** message (photo is fine)
4. What the panel's top box said at that moment

That last one matters most.

---

## If it all falls over

Nothing is lost. The host's data is on the host PC.

- Panel → **Back up now** before you change anything
- Host data lives at `C:\Users\WinDows\FIU_System\database\`
