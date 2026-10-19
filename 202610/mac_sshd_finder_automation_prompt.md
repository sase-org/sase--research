# Why the Mac Showed an "sshd" Permission Prompt (2026-10-19 12:17 EDT)

## Verdict

**It was a SASE agent. Nothing unexpected happened.** Agent `11v.w0` (Claude Opus, bob-cli
workspace 11) SSH'd from athena into the Mac and ran an AppleScript that talked to
**Finder**. macOS treats that as "remote login wants to control Finder", so it asked you.

The popup was a macOS **Automation** (Apple Events) prompt. It was not a firewall or
network prompt. It reads roughly: _"sshd-keygen-wrapper" wants access to control
"Finder"._

## Timeline (EDT)

| Time         | Where  | Event                                                                                            |
| ------------ | ------ | ------------------------------------------------------------------------------------------------ |
| 12:15:47     | athena | Agent `11v.w0` starts a `#plan` task: make the bob-mac-capture refs panel larger                 |
| 12:17:44     | athena | Agent SSHes to `mac` and runs `system_profiler` to get the display size (no prompt)              |
| 12:17:48     | athena | Agent SSHes to `mac` and runs `osascript -e 'tell application "Finder" to get bounds of window of desktop'` |
| 12:17:49.355 | Mac    | `tccd`: **"Prompting for access to indirect object Finder by sshd-keygen-wrapper"**              |
| 12:17:58.184 | Mac    | `tccd`: creates a `kTCCServiceAppleEvents` grant for `/usr/libexec/sshd-keygen-wrapper` (your Allow) |
| 12:17:58     | athena | Agent's command returns `0, 0, 1440, 900` (the screen size it wanted)                            |
| 12:18:21     | athena | Agent gets the same data again through JXA `NSScreen`, which needs no permission (no prompt)     |

The agent's command and the Mac's prompt are one second apart. This was the **only**
TCC prompt the Mac logged today (checked from 06:00 on).

## Why it said "sshd"

On macOS, any process started from an SSH session is attributed to
`sshd-keygen-wrapper`, which is Apple's wrapper for Remote Login. When that process sends
Apple Events to another app (here, `osascript` → Finder), macOS asks the logged-in user.
The agent's earlier SSH commands that day (rsync, `swift` builds, `system_profiler`) sent
no Apple Events, so they never prompted.

## What you granted

- **Scope:** Processes in SSH sessions on the Mac may now script **Finder** without asking
  again. Other apps (Mail, Safari, etc.) would still trigger their own prompts.
- **Who can use it:** Anyone who can SSH in as `bbugyi`. Today that means your tailnet
  machines and keys.
- **Risk:** Low to moderate. Finder scripting can list, move, and delete files, but an
  SSH user already has shell access to those same files. The grant mostly lets SSH
  sessions do Finder-specific things, such as reading window bounds or revealing items.
- **Needed?** No. The agent got the same screen size through `system_profiler` and JXA
  without any permission.

## If you want to revoke it

System Settings → Privacy & Security → **Automation** → `sshd-keygen-wrapper` → turn off
**Finder**.

(`tccutil reset AppleEvents` also works, but it resets the Automation grants for **every**
app.)

## Evidence sources

- Agent tool log on athena:
  `~/.sase/projects/gh_bobs-org__bob-cli/artifacts/ace-run/202610/19/20261019113301/tool_calls.jsonl`
  (calls at 16:17:44, 16:17:48, and 16:18:21 UTC).
- Mac unified log (`/usr/bin/log show`, processes `tccd`, `osascript`, and
  `UserNotificationCenter`, 12:17:40–12:18:05 EDT).
- No other process on athena was SSH'd into the Mac at the time. The only long-running
  transfer was the local `/home` backup rsync to `/mnt/hercules`, which does not touch the
  Mac.
