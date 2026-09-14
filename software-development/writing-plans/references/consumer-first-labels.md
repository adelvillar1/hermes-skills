# Consumer-First Label Mappings

Field-by-field mapping tables for common cruise-industry entities. Use these when writing plans that surface PG data in the Cruiser Intelligence mobile app.

## Principles

1. **Speak English, not schema.** Column names are for developers. Labels are for cruisers.
2. **Show only what helps a decision.** Technical specs that only a travel agent would care about get dropped.
3. **Translate enums before displaying.** Raw values like `"partial"` become "Some included".
4. **Frame as questions.** Section titles should be things a cruiser would actually ask.
5. **Hide if empty.** No "N/A", no placeholder cards.
6. **No scores without context.** Pair numeric scores with a human label.

---

## Ships

### Show (consumer label → PG field)

| Consumer label | PG field | Format example |
|---|---|---|
| "Class" | `shipClass` | "Icon class" |
| "Built" | `yearBuilt` | "2024" |
| "Last renovated" | `yearRefurbished` | "2022" |
| "Guests" | `passengerCapacity` | "5,610" |
| "Crew" | `crewCount` | "2,350" |
| "Size" | `grossTonnage` | "248,663 GT" |
| "Length" | `length` | "365m" |
| "Decks" | `decks` | "20" |
| "Speed" | `speed` | "22 knots" |

### Hide (travel-agent trivia)

| PG field | Why skip |
|---|---|
| `builder` | Only travel agents care who built the ship |
| `flag` | Maritime regulatory detail |
| `registryPort` | Regulatory detail |
| `propulsion` | Engineering spec |
| `buildCost` | Not relevant to cruise experience |
| `imoNumber` | Maritime identifier |

### Section titles

| Internal | Consumer |
|---|---|
| "Cabin Profile" | "Rooms" |
| "Venue Amenities" | "Onboard" |
| "Ship Facts" | "At a Glance" |

### Cabin type labels

| PG value | Consumer label |
|---|---|
| Interior | "Inside" |
| Oceanview | "Ocean view" |
| Balcony | "Balcony" |
| Suite | "Suite" |

---

## Cruise Lines

### Inclusion labels

| PG field | Consumer label | "included" | "partial" | "not_included" |
|---|---|---|---|---|
| `beverages` | "Drinks" | "Drinks included" | "Some drinks included" | "Drinks extra" |
| `gratuities` | "Tips" | "Tips included" | "Some tips included" | "Tips extra" |
| `wifi` | "WiFi" | "WiFi included" | "Basic WiFi included" | "WiFi extra" |
| `specialtyDining` | "Upscale restaurants" | "Included" | "Some included" | "Extra charge" |
| `excursions` | "Shore excursions" | "Included" | "Credit included" | "Extra" |
| `butlerService` | "Butler service" | "Available" | — | — |
| `minibarIncluded` | "Minibar" | "Included" | — | — |
| `laundry` | "Laundry" | "Included" | "Some included" | "Extra" |
| `roomServiceIncluded` | "Room service" | "Included" | — | — |

### Section titles

| Internal | Consumer |
|---|---|
| "Expert Assessment" | "What experts say" |
| "Inclusions" | "What's included" |
| "Fare Packages" | "Fare options" |

### Hidden fields

| PG field | Why skip |
|---|---|
| `packageSlug` | Internal identifier |
| `packageScore` | Internal ranking |
| `minNights` | Booking restriction, not consumer-facing |
| `cabinTypes` | Internal classification |

---

## Ports

### Guide section titles

| Guide key | Consumer title | Emoji |
|---|---|---|
| `welcome` | "Welcome" | 👋 |
| `safety` | "Staying safe" | 🛡️ |
| `weather` | "Weather" | ☀️ |
| `getting_around` | "Getting around" | 🚗 |
| `attractions` | "Things to see" | 🏛️ |
| `shopping` | "Shopping" | 🛍️ |
| `local_currency` | "Money" | 💰 |
| `port_location` | "Where you dock" | 📍 |
| `nearby_cities` | "Nearby" | 🏙️ |

### Section titles

| Internal | Consumer |
|---|---|
| "Verdict Badge" | "Port rating" (stars, not raw score) |
| "Value Comparison" | "Is it expensive?" |
| "Risk Flags" | "Good to know" |
| "Port Guide" | "Port guide" |

### Risk flag reframing

| Internal | Consumer framing |
|---|---|
| "Weather risk: moderate" | "Best time to visit: {seasonal note}" |
| "Crowding risk" | "Expect crowds {note}" |
| "Contingency plan" | "Backup plan: {tip}" |

### Hidden fields

| PG field | Why skip |
|---|---|
| `vsPeers` | Internal analytics |
| `medianExcursionCost` | Internal analytics |
| `costIndex` | Internal analytics |
| Raw numeric verdict score | Use tier word + stars instead |

---

## Itineraries

### Section titles

| Internal | Consumer |
|---|---|
| "Book" button | "View this cruise" (we don't know if it's bookable) |
| "Ship Dossier" | Ship card with "Learn more about this ship →" |
| "Port Guide Previews" | "Quick tips" on each port |

### Price display

| Format | Use |
|---|---|
| "From $X,XXX per person" | ✅ Clear, honest |
| "$X,XXX*" with fine print | ❌ Don't use asterisks or caveats |
| "Price not available" | ❌ Don't show anything if no price |

---

## General inclusion status icons

| Status | Icon | Color |
|---|---|---|
| `"included"` | ✅ | Green |
| `"partial"` | ~ | Yellow/amber |
| `"not_included"` | — | Gray |
| null/missing | (skip entirely) | — |
