# Running STR day to day

For whoever looks after STR. No technical background needed.

Everything here is done from the **Control Panel** — the button at the bottom
right of the login screen.

---

## Every morning (30 seconds)

Open the Control Panel. Read the top box.

- **"Everything is working"** → done, close it.
- **"Needs attention"** → it lists what's wrong, in plain words. Fix from the list below.

---

## Every week

Control Panel → **Back up now**.

That's it. The app also backs itself up automatically, but a backup you took
yourself before a busy week is worth having.

---

## The problems you will actually see

### "No host is running. Nobody can save changes."

The host PC isn't running STR.

Go to the host PC → Control Panel → **Start host on this PC**.

If the host PC is off, turn it on and log in. STR cannot run while nobody is
logged in.

### "This PC's copy of the data is X hours old."

This PC can't reach the shared folder.

1. Control Panel → **Check the shared folder**
2. If it fails, open File Explorer and paste `\\ENGAMMARPC\STR_data`
   - Asks for a password → enter the STR share credentials
   - "Access denied" → this PC needs the share account (see SETUP.md step B)
   - "Can't find" → the host PC is off, or the network is down

### "X changes are waiting to be saved."

Work people did is queued but not saved yet. Normally means the host stopped.

Start the host. The queue drains on its own — **nothing is lost while it waits.**

### Someone can't log in

- Wrong password 5 times locks the account. An admin unlocks it in the app.
- If *nobody* can log in, the host is down. See above.

---

## The host PC died

Another PC can take over. All the data is on the shared folder.

1. On the PC that will take over, open the Control Panel
2. Press **Make this PC the host**
3. Press **Start host on this PC**

Everyone else keeps working — their app finds the new host by itself.

> **Only do this on ONE PC.** Two hosts at once will cause problems. If the old
> host PC comes back, do not start the host on it again until you have stopped
> the new one.

---

## Restoring after something went wrong

If data was lost or damaged:

1. Control Panel → **Stop host** (a restore cannot happen while the host runs)
2. Control Panel → **Check data is healthy** — this often repairs it by itself
3. Still wrong? Restore a backup — ask whoever maintains the app; this is the
   one operation worth having a second pair of eyes on
4. Control Panel → **Start host on this PC**

**Take a backup before you do any of this**, even if the data looks broken. A
damaged copy is still evidence of what happened.

---

## Giving a new person a PC

See [SETUP.md](SETUP.md) section C. Short version:

1. On the host: Control Panel → **Build client folder**
2. Copy that folder to the new PC at `C:\STR`
3. Double-click `FIU_System.exe`

---

## Updating STR to a new version

Client PCs run a single file, `FIU_System.exe`. To update:

1. Get the new `FIU_System.exe`
2. On each client PC, close STR and replace the file
3. Their settings and local data are untouched — those live beside it, not inside it

There is no automatic update for client PCs. That is deliberate: pushing code
to workstations by itself is the kind of thing security teams object to, and
rightly.

---

## Things that are true and worth knowing

**The host PC must be on and logged in.** Not just switched on — *logged in*.
After a restart, someone has to log in before STR starts serving.

**Only the host holds the real data.** Every other PC holds a copy. Backing up
a client PC backs up nothing that matters.

**A locked screen is fine.** The host keeps running when the screen is locked.
Sleep and shutdown are not fine.

**Nothing is lost when the network drops.** Work is queued on the PC and sent
when the connection returns.

---

## When to ask for help

Anything not on this page. Take a photo of:

1. The message on screen
2. The Control Panel's top box at that moment

Those two together are usually enough to identify the problem.
