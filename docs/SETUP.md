# STR Setup

**One host PC. Every other PC is a client.**

Do the sections in order. Stop at the end of each one and check it worked.

---

## Two files, one folder, and they must stay together

`build.bat` produces two executables:

| File | What it is |
|---|---|
| `FIU_System.exe` | the app. Double-click this one. |
| `FIU_Control_Panel.exe` | check-up mode, for when the app will not start. |

**Keep them in the same folder.** This is not tidiness — both find `config\`
and `database\` by looking next to themselves, and the Control Panel starts the
host by launching `FIU_System.exe` from its own folder. Separate them and the
panel's start buttons report `could not start host`, and the two programs read
two different configurations.

You do not normally touch the second file: the app opens it for you from
**bottom-right of the login screen → "Control Panel"**. It exists as its own
`.exe` for the one case that button cannot cover — the app not starting at all,
so the login screen never appears.

There is no launcher script and nothing to install.

---

## FIRST: pick the host

The host is the PC that owns the data. It must be **on** whenever anyone works.

Pick the PC that is always on. Usually yours.

Currently: **ENGAMMARPC**, share `\\ENGAMMARPC\STR_data`

---

## A. Set up the HOST (once)

### A1. Build

```
build.bat
```

Wait for `Build OK`. If it says BUILD FAILED, stop — nothing else will work.

Copy **both** files out of `dist\` into `C:\STR`:

```
FIU_System.exe
FIU_Control_Panel.exe
```

### A2. Create the database

Double-click **`FIU_System.exe`** and complete the setup wizard:

- **Mode:** host
- **Database folder / backup folder:** leave the defaults
- **Shared folder:** `\\ENGAMMARPC\STR_data`

This is the step that creates `database\`. Nothing later works without it —
the host has no way to create a database for itself and will refuse to start.

### A3. Open the control panel

Double-click **`FIU_Control_Panel.exe`**, then click
**"Show setup and recovery options ▾"** — the setup buttons are collapsed
behind it.

### A4. Press these buttons, in this order

1. Type the share path into **Shared folder** — `\\ENGAMMARPC\STR_data`
2. **Make this PC the host**
3. **Check the shared folder** → must say *reachable and writable*
4. **Start host on this PC**

> Order matters. "Check the shared folder" reads the box above it, so checking
> before you have typed a path just tells you no path is set.

### A5. Make it start at login

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
2. Hold the **RIGHT** mouse button, drag `FIU_System.exe` into that window,
   let go, and choose **Create shortcuts here**
3. Right-click the new shortcut → **Properties** → in **Target**, add ` --host`
   at the very end, after the closing quote → OK
4. Log out and back in. The Control Panel must say the host is running.

> **Right-drag, not left-drag.** A normal drag either moves the .exe out of
> `C:\STR` or copies a 100 MB binary into your Startup folder — and a copied
> .exe has no **Target** box to edit, because only shortcuts have one.
>
> An .exe sitting in Startup is worse than useless: the app finds `config\` and
> `database\` next to itself, so it would look for them *inside the Startup
> folder*, find nothing, and either open the setup wizard or die with no
> message at all.
>
> The shortcut is made by hand on purpose: creating one in code needs a Windows
> scripting component that endpoint security flags, and this app does not use
> one. A shortcut you make from Explorer's own menu runs nothing.

### A6. Confirm

The top of the panel must say **Everything is working**.

If it doesn't, it tells you what's wrong. Fix that, press **Refresh**.

**Done with the host.**

---

## B. Share permissions

Nothing to do, as long as the people using STR can already open
`\\ENGAMMARPC\STR_data` in File Explorer and save a file there.

Check it once: paste the path into File Explorer on one client PC, create a text
file, delete it. If that works, skip to C.

> If it does *not* work, the share needs permissions granted, and that needs
> administrator rights on the host. `deploy\grant_share_access.ps1` is the
> specification of what is required — treat it as the text of a request to
> whoever administers that PC, not as something to run from this document. It
> creates a local `STR_client` account and grants it **Change** (share) and
> **Modify** (NTFS). Note it does *not* create the share itself.

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

Normally it does not — if that person can already reach the share in File
Explorer, the app can too.

If it does ask, enter the account that has access to `\\ENGAMMARPC\STR_data`
and tick **Remember my credentials**.

**Done with that PC.** Repeat C2–C4 for each one.

---

## D. Going live (clearing the test data)

Do this **once**, when you stop testing and start real work.

It deletes every report, number and log made during testing.

Settings and field configuration are kept.

> **It also deletes every user account.** You are left with a single `admin`,
> whose password is printed once when the script finishes. Nobody else can log
> in until you recreate them.
>
> **Write down who needs recreating before you run this** — name, username and
> role for each person. There is no list afterwards.

1. Make sure nobody is using STR
2. On the host PC, Control Panel → **Back up now**
3. Write down the user list
4. Run:

```
python reset_to_production.py
```

5. It asks you to confirm. Read what it says before typing anything.
6. **Copy the admin password it prints.** It is shown once and not stored
   anywhere you can read it back.
7. Log in as `admin`, change the password when asked, recreate the users.

> **There is no undo.** The backup from step 2 is your only way back.
> Do not skip it, even though the data is "only test data" — if the reset
> catches something real, that backup is the difference between an
> inconvenience and a loss.

After this, the numbering starts clean and the app is ready for real reports.

---

## Something is wrong

### The app says it can't reach the shared folder

That screen is the *correct* behaviour and the PC is still set up properly —
nothing local is lost, and anything saved earlier is queued and will send by
itself. Usually the host PC is off, asleep, or nobody has logged into it.

1. On that PC, open File Explorer
2. Paste: `\\ENGAMMARPC\STR_data`
3. Press Enter

- **Asks for a password** → enter the account that can reach the share
- **"Access denied"** → that account has no permission (section B)
- **"Can't find"** → the host PC is off, asleep, or the network is down

Press **Retry** on the app screen once it's back.

### The app asks me to set up a database

On a client PC this should no longer happen just because the share is
unreachable. If it does, this PC has genuinely lost its settings:

Open `FIU_Control_Panel.exe` and read **My settings**. If the path is not
`C:\STR\config\config.json`, the app is running from the wrong folder — most
often a copy of the .exe left somewhere like the Startup folder. Delete that
copy and run the one in `C:\STR`.

> Never click through the wizard to make the message go away. Choosing "local"
> creates a private database on that PC, and every report filed into it is
> invisible to the FIU unit.

### The app opens but there are no reports

The host isn't running.

Go to the host PC → control panel → **Start host on this PC**.

### It was working, now it isn't

On the host, open the control panel and read the top box. It names the problem.

Most common: **the host stopped.** Press **Start host on this PC**.

### The host keeps stopping

The host dies when the PC sleeps, logs off, or restarts. That is not
preventable without administrator rights — but nothing is lost when it happens:
client writes wait safely in each PC's local queue and send themselves when the
host is back.

- Do section **A5** so it restarts at every login
- Set the host PC to never sleep
- The Startup entry runs at **login, not at boot** — after a restart, someone
  must log in on the host PC

If the host PC is gone for good: Control Panel → **Show setup and recovery
options** → **Take over as host** on another PC.

### The host won't start and says nothing

It now tells you why, in a message box. If it says it cannot open the database,
that PC never completed step **A2**, or `database\` is not next to the .exe.

### Changes aren't showing on other PCs

Open the panel on the PC that looks wrong and read these two lines:

- **Waiting to save** — `N on this PC` means that PC can't reach the host.
  `N on the shared folder` means the host is stopped or struggling.
- **My data** — names the file this PC is actually reading and how old it is.
  Hours or days old means this PC isn't getting updates.

---

## Quick reference

| I want to | Where | Do |
|---|---|---|
| Start the host | Host PC | Panel → Start host on this PC |
| Stop the host | Host PC | Panel → Stop host |
| Add a client PC | Host PC | Panel → Build client folder, copy to `C:\STR` |
| Back up now | Host PC | Panel → Back up now |
| See what's wrong | Any PC | Panel → top box |
| Take over a dead host | Another PC | Panel → setup and recovery → Take over as host |

---

## The rules

1. The host PC must be **on and logged in** for anyone to save.
2. Clients go in **`C:\STR`**, never Program Files.
3. Both .exe files stay in the same folder, on every PC.
4. Every client must be able to reach `\\ENGAMMARPC\STR_data`.
5. Only the **host** holds the real data. Clients hold a copy.
6. Back up before anything risky.
7. **Never click through the setup wizard to dismiss an error.** Choosing
   "local" makes that PC a private island, and the reports filed on it are
   invisible to the FIU unit.
