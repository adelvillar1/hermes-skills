# Group chats (Bot rooms)

Source: Bot Mode docs — "Group chats" and "Rooms follow your gateways" sections.

## Shape

- A group is a **standalone row** in the same activity-ordered roster as Bot DMs, with member count,
  latest-message preview, timestamp and needs-you state.
- A Bot keeps **one DM row** even when it belongs to several groups; every group gets its own room row.
- **Open chat** on a group row opens the shared room. Sizes are **2–6 Bots**.
- Each member keeps its own persistent `Group: <name>` session, so room context survives like any other
  conversation — and each member's turns in a cross-machine room run in that session *on its own machine*.

## Turn mechanics (the part people get wrong)

- Your message triggers up to **three serial rounds** of member turns.
- **@-mentioned Bots respond; everyone responds when nobody is mentioned.** Mentioning specific
  members scopes the round to them.
- Each Bot replies briefly or **passes**. The room settles when a full round stays silent.
- **Not every Bot replies to every message** — speaking is each member's own choice; a Bot speaks only
  when it has something new to add. Expect the addressed members (or whoever has something to say) to
  speak and the rest to stay quiet. A quiet member is not a failure.
- Hard caps: **10 messages per send, 3 rounds**. Rooms cannot spin.
- Bots pull each other in with `@name`, and escalate real judgment calls to you with **`@user`** — the
  group row then shows a **needs you** badge.

## Membership

- Right-click a **local** Bot → **Manage groups** to add/remove it from any number of group chats; pick
  existing groups independently or create one inline.
- Local membership is stored in the Bot's **backend-synced profile metadata**, so it follows that profile
  across desktops. Older profiles with one legacy group keep working.
- **Connections Bots** join through the New Group Chat picker and remain source-qualified in the room's
  shared state.

## Durability and multi-gateway rooms

- Rooms follow your **gateways**, not one Desktop. Each room's recent transcript, members, picture and
  name are mirrored into the shared profile metadata of **every** gateway the Desktop is connected to,
  with **per-gateway versioning** so two Desktops writing at once merge instead of overwriting.
- Open Hermes Desktop on another machine against the same gateway and the room appears with its
  history; gateway-only clients see it too.
- Rooms carry a **durable internal identity**: renaming changes only the display name everywhere;
  disbanding removes it permanently on every client (even ones offline at the time); recreating a
  same-name group starts a genuinely fresh room.
- If a gateway dies or is removed, nothing is lost: every connected Desktop keeps the full room locally
  and re-seeds any gateway it reconnects to. The full orchestration log stays in each Desktop's local
  storage — the shared mirror is a bounded recent-history projection.

## Cross-machine rooms

- The New Group Chat picker seats Bots from any registered connection; each member's turns run on its own
  machine, in its own `Group: <name>` session there.
- Cross-machine members carry a device badge (`dixie · Mac Mini`) in the room and in other members'
  transcripts, and the disambiguated `@name-device` handle works in room mentions — same-named agents on
  two machines never blur together.

## Design implications

- Use a room when you want **deliberation between specialists that each hold their own context and
  skills**, not when you want a deterministic pipeline (that is a routine or `delegate_task`).
- Room members do **not** get the `message_agent` tool (it exists only in canonical Bot Chats), so a room
  cannot cascade into a DM storm — a property worth preserving when you design memberships.
- With 3 rounds and 10 messages per send, messages must be short and pointed if a group is to converge;
  @-mention the members whose opinion you actually want.
- Watch the **needs you** badge: it is the designed escalation channel for decisions a Bot shouldn't make.
