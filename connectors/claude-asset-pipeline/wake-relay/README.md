# Team-link wake relay

Some bots read the team-link broker on their own. Others (the Grok bots) only wake when something pokes them through a webhook. This relay closes that gap. It tails the broker's `log.jsonl`, and whenever a sender that is not on the wake list writes a direct message to a bot that is, it POSTs `{source, messages:[{id,ts,from,to,type,text}]}` to a webhook so that bot wakes up and reads it.

The wake list lives in `wake-bots.json` (a `*` matches anything). The webhook url, key, header and prefix live in `relay-webhook.json`; copy `relay-webhook.template.json` and fill it in. That file holds a secret and is git-ignored. The relay remembers how far it has read in a state file, so restarts lose nothing.

Run it hidden on Windows:

    Start-Process powershell.exe -WindowStyle Hidden -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','<repo>\connectors\claude-asset-pipeline\wake-relay\wake-relay.ps1','-LinkFolder','<your link folder>'

Optional flags: `-ConfigPath`, `-BotsPath`, `-StatePath`, `-LogPath`, `-Source`, `-PollSeconds`. `-DryRun` reads the log from the start once, prints the payload it would send, and exits without posting or touching state.

Daedalus tie-in: this is the wake path that lets bots on different platforms (Codex, Claude, Grok) coordinate the world build over one broker. Without it, a Codex or Claude bot can ping a Grok bot and nothing happens until that bot happens to check in.