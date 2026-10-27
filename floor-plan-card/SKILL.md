---
name: floor-plan-card
description: Turn the owner's floor plan into an interactive SVG card that shows which rooms have lights on, toggles a room's lights when tapped, and shows the robot vacuum's dock and current room. Covers getting a plan image, tracing rooms as rectangles and polygons, matching rooms to Home Assistant areas, placing labels and the dock, and checking taps. Use when someone wants a floor plan on their dashboard or says tapping rooms doesn't work.
---

# Floor plan card

## 1. Get the plan

Ask for the builder's floor plan (purchase documents, the listing, the HOA) as an image or PDF page. If they
don't have one, a clear phone photo of a hand sketch with room names works.

Also ask:
- **Which floor** to draw, if the home has several.
- **The vacuum:** where its **dock** is (which room, which wall, how far along it), and the names it uses for
  rooms.
- **Outdoor areas:** any deck or balcony, which gets a hatched pattern and isn't tappable.

## 2. Trace rooms in the plan's own pixel coordinates

Work in the image's pixel space, so you can check the drawing against the plan by laying one over the other:
```js
const PLAN_VIEWBOX = '<minx> <miny> <w> <h>';     // crop to the drawn area
const PLAN_ROOMS = [
  { id: 'kitchen', label: 'Kitchen', points: 'x1,y1 x2,y2 ...', labelAt: [x, y], center: [x, y] },   // L-shapes as polygons
  { id: 'living_room', label: 'Living', rect: [x, y, w, h] },
  { id: 'deck', label: 'Deck', rect: [...], outdoor: true },
  { id: 'hall', label: '', rect: [...], passive: true },          // drawn, not interactive
];
```
- **`id` must equal the Home Assistant area id.** Tapping a room toggles the lights configured for that area:
  `rooms: { kitchen: ['light.kitchen_main', ...], ... }`. Rooms with no lights are drawn but can't be tapped.
- **Room names come from the owner.** For example, if they call a nook the "dining room", use that, even if
  the plan says something else.
- **Draw the outline separately:** one polygon for the outside wall, with `pointer-events="none"` so it
  doesn't swallow taps.
- **Polygons need placement:** give each one an explicit `labelAt` and a `center` (where the vacuum marker
  goes).

## 3. Vacuum

- **Dock:** `dock: [x, y, 'left'|'right'|'top'|'bottom']`. This is a point on the wall it's against, plus which
  wall. The robot icon parks just in front of it.
- **Labels:** move any room label that overlaps the dock.
- **While cleaning:** the marker moves to the centre of the room in the vacuum's current-room sensor, matched by
  area id or label, and pulses.
- **Washer (optional):** a small pulsing dot in the laundry room while it runs.

## 4. Behaviour and styling

- **Lit rooms:** a warm gradient fill with a soft glow, and dark label text.
- **Off rooms:** the card's plan colour.
- **Outdoor areas:** hatched.
- **Hover:** tappable rooms highlight their outline in the accent colour.
- **Summary line:** "Lights on in Kitchen, Entry" or "All lights are off".

## 5. When taps "do nothing"

Check the data before the code:
1. **Read the light states:** `GET /api/states/<light>`. If they're all `unavailable`, the lighting
   integration is down (see `troubleshooting-dropouts`). The card is fine.
2. **Check the room id:** the `id` must match a key in `rooms`. A room with an empty list isn't tappable.
3. **Check the outline:** an overlaying element without `pointer-events="none"` swallows clicks.
4. **Test without touching the owner's lights:** check in the local preview harness rather than switching their
   real lights, unless they say it's OK.
