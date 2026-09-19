# Roster, presence, and Bot identity

Source: Bot Mode docs — "The roster", "Hiding a Bot", "The canonical Bot Chat is a forever-chat",
"Renaming Bots", "Faces" sections. Verified against the shipped probe in `tools/bot_mode_probe.py`.

## Roster mechanics

- One row per agent profile: avatar, latest-message preview, timestamp.
- Clicking a row lands in that Bot's canonical **Bot Chat**.
- **Active now** strip above the roster: the gateway-busy profile plus any Bot that wrote within the
  last **90 seconds**. Each chip opens that Bot's chat. The strip never reorders the roster and
  disappears when the fleet is idle.
- **Search** filters the roster as you type.
- The roster is activity-ordered, and group rows sit in the same list as Bot DMs.

## Hide / unhide (display-only)

- Right-click a row → **Hide Bot** removes it from the roster and the Active-now strip.
- Hiding does NOT affect: @mention resolution, group-chat membership, or routines. Routines keep running.
- Hidden Bots never toast but accumulate unread activity silently; the **eye toggle** (appears once at
  least one Bot is hidden) badges a dot and reveals hidden Bots dimmed in place.
- Right-click → **Unhide Bot** restores a Bot.
- Hidden state is stored in the Bot's **profile metadata**, so it follows the Bot to every desktop
  connected to that backend.

## The canonical Bot Chat is a forever-chat

- Created and pinned **the moment the Bot is born**; the Bot introduces itself as its first message.
- Title is exactly `Bot Chat`. This exact title is load-bearing: the backend injects the teammate
  protocol only into a session whose title matches (`BOT_CHAT_TITLE`), and the desktop creates the
  session under the same title.
- Typing `/new` or `/reset` inside it is rerouted to `/compact`: fresh working context, same
  conversation. Regular sessions on the same profile keep full `/new` freedom.
- A preference can hide canonical Bot Chats from the regular sidebar session list (uses the core
  hidden-session flag; on older gateways they simply stay visible).
- Consequence for tooling: the canonical chat is hidden from a plain session listing, so anything
  resolving it remotely must ask for hidden sessions too. `hermes peer` does this — it looks up the
  exact title with `include_hidden=1` before creating, because creating a duplicate hits the peer's
  `UNIQUE(title)` guard.

## Renaming and mention tags

- Rename via the pencil in the Bot's chat header, or `hermes profile rename`.
- After a rename the Bot is taggable by its friendly name: a Bot titled *Research Buddy* answers to
  `@research-buddy` and `@researchbuddy`, in regular chats and group rooms alike.
- The composer's `@` autocomplete offers the renamed tag **and** still matches the original profile
  name, which keeps resolving. Renaming does not break old habits.
- The default profile's handle in protocol text is `@hermes` (not `@default`).

## Faces

| Face | Behaviour |
|---|---|
| **Blob faces** (default) | Deterministic soft-body face derived from the Bot's name — same name, same face, forever. Follows the name live while typing. **Randomize** re-rolls; **Lock face** keeps it even if the name changes; the six silhouettes (round, organic, boxy, nub, cloud, sun) can be pinned while everything else still comes from the name. |
| **Geometric faces** | The classic 7 shapes × 10 colours, with blinking eyes that scan while the Bot works. |
| **Uploaded image** | Any picture. |
| **AI portrait** | Generated in place when an image backend is configured — rides the standard `image.generate` RPC, so it works over local and remote gateways alike. |
| **Pixel pet** | A companion from the petdex gallery that bounces beside the avatar while the Bot is busy; explore the gallery with `hermes pets`. |

A Bot's look, title and description are stored in the **profile's metadata on the backend**, so the
same Bot appears the same way on every desktop connected to that backend.

## Identity facts worth remembering

- A Bot's *title* + *description* are not cosmetic: they are the **role** text the backend reads when
  it builds every other Bot's teammate roster (`_profile_role` truncates to 160 chars, collapsing
  whitespace). A vague description degrades every Bot's teammate selection.
- The roster helper treats the default profile as name `default` and renders its handle as `hermes`;
  named profiles render as their directory name.
- Presence is a heuristic (busy gateway + recent writes), not a task-state tracker — don't build
  "is this bot done?" logic on it.
