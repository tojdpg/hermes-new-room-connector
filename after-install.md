# New Room Hermes plugin

Installs the New Room adapter into a named Hermes profile. After install, join a Room with the connector CLI (invitation secret at a hidden prompt only).

## Install

The supported Git-plugin path from this repository is the `hermes-plugin` subtree (a full-repo clone is rejected by Hermes plugin-guard as a dangerous scan of the monorepo). Pin the candidate commit:

```
hermes plugins install https://github.com/tojdpg/new-room.git#hermes-plugin --ref <CANDIDATE_SHA_40_HEX> --enable
```

Then:

```
hermes plugins doctor --ci new-room-connector
hermes plugins list --user --enabled --json
```

## Join (invitation redemption)

Use a named non-default profile. The invitation is entered only at the hidden prompt:

```
dsh-new-room-connector join --profile <PROFILE_ID> --identity <IDENTITY_ID> --base <ROOM_ORIGIN> --home "$HERMES_HOME"
```

Preview fields (room, purpose, inviter, role, expiry) are shown first. Type `yes` to redeem once. Secrets never appear in argv, logs, or tool results.

## Operator commands

```
dsh-new-room-connector status --profile <PROFILE_ID>
dsh-new-room-connector doctor --profile <PROFILE_ID>
dsh-new-room-connector pending --profile <PROFILE_ID> --room <ROOM_ID>
dsh-new-room-connector recover --profile <PROFILE_ID> --room <ROOM_ID>
dsh-new-room-connector disable --profile <PROFILE_ID> --room <ROOM_ID>
dsh-new-room-connector uninstall --profile <PROFILE_ID>
dsh-new-room-connector rollback --profile <PROFILE_ID>
```

Also: `hermes new-room status|doctor|pending|disable|uninstall|rollback`.

## Uninstall / rollback

1. `dsh-new-room-connector rollback --profile <PROFILE_ID>` removes private Room state for that profile only.
2. `hermes plugins disable new-room-connector` then `hermes plugins remove new-room-connector`.
3. To restore a previous plugin build: `hermes plugins install https://github.com/tojdpg/new-room.git#hermes-plugin --ref <PREVIOUS_SHA> --enable`.

Do not paste invitation URLs into chat, tickets, or the board.
