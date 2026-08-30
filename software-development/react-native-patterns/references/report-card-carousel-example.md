# Report Card Carousel — Complete Example

## API Response Shapes

### GET /api/cruise-lines/:id/report-card
```json
{
  "reportCard": {
    "id": "uuid",
    "name": "Royal Caribbean",
    "tier": "contemporary",
    "avgExpertRating": 4.2,
    "fleetSize": 28,
    "familyFriendly": true,
    "couplesFriendly": true,
    "soloFriendly": false,
    "avgDailyRateMin": 120,
    "avgDailyRateMax": 350,
    "medianAge": 45,
    "activityLevel": "high",
    "dressCode": "Casual",
    "budgetLevel": "moderate",
    "fleet": {
      "shipCount": 28,
      "avgCapacity": 4200,
      "avgFleetAge": 12
    },
    "narrative": "Royal Caribbean excels in family-friendly mega-ship experiences..."
  }
}
```

### GET /api/ships/:id/report-card
```json
{
  "reportCard": {
    "id": "uuid",
    "name": "Symphony of the Seas",
    "yearBuilt": 2018,
    "passengerCapacity": 5518,
    "grossTonnage": 228081,
    "crewCount": 2200,
    "length": 362,
    "cruiseLine": "Royal Caribbean",
    "cruiseLineTier": "contemporary",
    "demographics": {
      "familyFriendly": true,
      "couplesFriendly": true,
      "soloFriendly": false,
      "medianAge": 42,
      "activityLevel": "high",
      "budgetLevel": "moderate"
    },
    "venueProfile": {
      "familyScore": 85,
      "couplesScore": 60,
      "luxuryScore": 40,
      "foodieScore": 70,
      "nightlifeScore": 75
    },
    "cabinProfile": {
      "familyScore": 80,
      "couplesScore": 65,
      "luxuryScore": 45,
      "budgetScore": 55,
      "soloScore": 30
    }
  }
}
```

## Score Bar Colors

Use distinct colors per dimension for quick visual scanning:

| Dimension | Color | Hex |
|-----------|-------|-----|
| Family | Blue | `#5B8DEF` |
| Couples | Coral | `#D9534F` |
| Luxury | Purple | `#9B59B6` |
| Foodie | Gold | `#D4A574` |
| Nightlife | Deep Purple | `#8E44AD` |
| Budget | Green | `#2D8A56` |
| Solo | Teal | `#16A085` |

## Wiring Pattern

```jsx
// In CruiseLineDetail.js
const [reportCard, setReportCard] = useState(null);

useEffect(() => {
  getCruiseLineReportCard(id)
    .then((data) => setReportCard(data.reportCard || null))
    .catch(() => {}); // Non-critical — carousel just won't show
}, [id]);

// In the ScrollView, after the header card:
{reportCard && <ReportCardCarousel data={reportCard} type="cruise-line" />}
```

The `.catch(() => {})` is intentional — the report card is supplementary content. If the endpoint fails or returns no data, the screen works fine without it.

## API Client Functions

```js
export function getCruiseLineReportCard(id) {
  return request(`/cruise-lines/${id}/report-card`);
}
export function getShipReportCard(id) {
  return request(`/ships/${id}/report-card`);
}
```
