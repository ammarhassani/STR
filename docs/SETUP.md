# STR Setup

**One host PC. Every other PC is a client.**

Do the sections in order. Stop at the end of each one and check it worked.

---

## There is only ONE program

`FIU_System.exe` is everything.

- **Double-click it** → the app
- **Bottom-right of the login screen → "Control Panel"** → check-up mode

There is no second program, no launcher script, and nothing to install.

> The Control Panel sits on the login screen on purpose. When something is
> wrong, nobody can get past that screen — so that is where the button that
> tells you what's wrong has to be.

---

## FIRST: pick the host

The host is the PC that owns the data. It must be **on** whenever anyone works.

Pick the PC that is always on. Usually yours.

Currently: **ENGAMMARPC**, share `\\ENGAMMARPC\STR_data`

---

## A. Set up the HOST (once)

### A1. Build the app

```
build.bat
```

Wait for `Build OK: dist\FIU_System.exe`.

If it says BUILD FAILED, stop. Nothing else will work. Read the error.

### A2. Open the control panel

```
python flet_app\main.py --panel
```

### A3. Press these buttons, in this order

1. **Check the shared folder** → must say *reachable and writable*
2. **Make this PC the host**
3. **Start host on this PC**

### A4. Make it start at login

> **Tell security BEFORE you do this.**
>
> Anything placed in the Startup folder gets picked up by the endpoint
> security automation, which scans persistence locations and asks what the
> entry is. That is exactly how the old `.vbs` launcher was found — not by
> analysing it, but by finding it in Startup.
>
> A business application starting at login is completely normal (OneDrive and
> Teams do it). It just needs to be declared rather than discovered. One line
> in your open ticket: *"the STR host application will have a Startup entry on
> ENGAMMARPC so it runs when I log in."*
>
> Until that is acknowledged, **skip this step** and start the host by hand
> from the Control Panel each morning. It costs one click.

Once it's declared:

1. Press **Show me the Startup folder** → a window opens
2. Drag `FIU_System.exe` into that window
3. Right-click the copy that appears → **Properties** → in **Target**, add ` --host` at the end → OK

> Done by hand on purpose: creating that shortcut in code needs a Windows
> scripting component that endpoint security flags, and this app does not use
> one.

### A4. Confirm

The top of the panel must say **Everything is working**.

If it doesn't, it tells you what's wrong. Fix that, press **Refresh**.

**Done with the host.**

---

## B. Give client PCs permission (once)

Client PCs are refused by default. They need an account.

Run **as administrator**, on the host:

```
powershell -ExecutionPolicy Bypass -File deploy\grant_share_access.ps1 -Password "PICK-A-STRONG-ONE"
```

Write the password down. You need it on every client PC.

---

## C. Set up each CLIENT PC

### C1. On the HOST: build the client folder

In the control panel, bottom section:

1. Check the **Shared folder** box shows `\\ENGAMMARPC\STR_data`
2. Press **Build client folder**

You get a folder on your Desktop: `STR_Client`

### C2. Copy that folder to the client PC

Put it at **`C:\STR`**

> Not Program Files. The app writes next to itself and can't write there.

### C3. On the client PC: double-click `FIU_System.exe`

### C4. If Windows asks for network credentials

```
user:     ENGAMMARPC\STR_client
password: the one from step B
```

Tick **Remember my credentials**.

**Done with that PC.** Repeat C2–C4 for each one.

---

## D. Going live (clearing the test data)

Do this **once**, when you stop testing and start real work.

It deletes every report, number and log made during testing, and keeps your
users, settings and field configuration.

1. Make sure nobody is using STR
2. On the host PC, Control Panel → **Back up now**
3. Run:

```
python reset_to_production.py
```

4. It asks you to confirm. Read what it says before typing anything.

> **There is no undo.** The backup from step 2 is your only way back.
> Do not skip it, even though the data is "only test data" — if the reset
> catches something real, that backup is the difference between an
> inconvenience and a loss.

After this, the numbering starts clean and the app is ready for real reports.

---

## Something is wrong

### The app asks me to set up a database

It can't see the shared folder.

1. On that PC, open File Explorer
2. Paste: `\\ENGAMMARPC\STR_data`
3. Press Enter

- **Asks for a password** → enter the step B credentials
- **"Access denied"** → step B wasn't run, or the password is wrong
- **"Can't find"** → the host PC is off, asleep, or the network is down

### Access denied

The client PC doesn't have the share account. Redo step B, then C4.

### The app opens but there are no reports

The host isn't running.

Go to the host PC → control panel → **Start host on this PC**.

### It was working, now it isn't

On the host, open the control panel and read the top box. It names the problem.

Most common: **the host stopped.** Press **Start host on this PC**.

### The host keeps stopping

The host dies when the PC sleeps, logs off, or restarts.

- Press **Start automatically at login** (starts it again at every login)
- Set the host PC to never sleep
- After a restart, **someone must log in** for the host to start

### Changes aren't showing on other PCs

Check the panel:

- **Waiting to save** is a big number → the host is stopped or struggling
- **Data copy updated** says hours/days ago → that PC isn't reaching the share

---

## Quick reference

| I want to | Where | Do |
|---|---|---|
| Start the host | Host PC | Panel → Start host on this PC |
| Stop the host | Host PC | Panel → Stop host |
| Add a client PC | Host PC | Panel → Build client folder, copy to `C:\STR` |
| Back up now | Host PC | Panel → Back up now |
| See what's wrong | Any PC | Panel → top box |
| Let a new PC in | Host PC, admin | `deploy\grant_share_access.ps1` |

---

## The rules

1. The host PC must be **on and logged in** for anyone to save.
2. Clients go in **`C:\STR`**, never Program Files.
3. Every client needs the share account (step B).
4. Only the **host** holds the real data. Clients hold a copy.
5. Back up before anything risky.
