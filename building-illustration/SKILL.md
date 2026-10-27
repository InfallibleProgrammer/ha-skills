---
name: building-illustration
description: Draw an SVG illustration of the owner's actual home (a house, townhouse or apartment building) for a dashboard hero card. Gathers references (Google Maps or Street View links, the owner's own photos of every face, builder elevation drawings), lines up windows floor by floor, draws side faces in perspective, changes the sky with the sun and weather, and lights the owner's windows from the lights in each room. Use when someone wants their house or building shown on the dashboard, or is giving feedback on the drawing.
---

# Building illustration

The goal is a simple, flat SVG that the owner instantly recognises as **their** building, with their own
windows glowing when the lights in those rooms are on.

## 1. Gather references (ask for all of these up front)

1. **Address or map link:** a Google Maps link, so you can see where the building is. Ask them to send
   **Street View screenshots** of each side people see, since you may not be able to open Street View yourself.
2. **Their own photos:**
   - the full street-facing front, as straight-on as possible,
   - each side face,
   - close-ups of anything distinctive (entry door, balconies, stone or tile areas, railings),
   - and a **marked-up photo** circling or outlining their unit.
3. **Builder drawings:** elevation drawings from the purchase or HOA documents are the most accurate source of
   window positions and widths.
   - Ask whether the drawing is **mirrored or rotated** compared with the street view, since condo and
     HOA documents often are. Rotate and flip it until it matches their photo before you measure.
4. **Which parts to include:** have them draw a line on a photo or drawing to mark where the building starts
   and ends.
5. **Their unit:** the floor, and which windows belong to which **room** (office, living, bedroom, kitchen,
   dining). For a house, ask which floors and faces to show. Also which rooms have smart lights; rooms without them shouldn't light up.

## 2. Draw from measurements, not impressions

- **Measure positions:** read x-positions off the elevation (left/right edge of each block, window and door)
  and convert them to SVG units with one scale per block.
  - Proportions matter more than detail. One window that's too wide makes the whole building look wrong.
- **Line up the floors:** first-floor windows usually sit **directly under** the windows above them. Check
  every column.
- **Use real building blocks:** the facade is made of vertical blocks (towers, recessed strips, balcony
  columns), each with its own colour band and roofline height. Draw each block, then put its windows on a
  shared list of floor heights.
- **Side faces:** use a trapezoid in perspective (the top edge slopes down toward the back, the bottom stays
  level).
  - Put side windows through the same perspective mapping, so their tops and bottoms angle with the roofline.
  - Flat rectangles on a slanted face look wrong.
- **Balconies (if there are any):** a dark recess, a door and a window behind a railing of horizontal bars, on a white slab.
  - Copy the owner's photo for which side the door is on, and the relative heights (the door is often the
    tallest piece).
- **Leave out neighbouring buildings and sheds** unless they ask for them.
- **Keep it flat:** a few tones per material (white plaster, light and mid grey, dark accent, stone), thin dark
  window frames, a mullion line and a lower transom.

## 3. Make it alive

- **Sky:** day, golden hour (sun elevation under ~8°) and night (stars, moon) from `sun.sun`. Add an overcast
  sky from the weather entity only if the owner wants it.
- **Colours after dark:** blend the facade colours toward the night sky, so the lit windows stand out.
- **The owner's windows:** glow amber when **any** light in the mapped room or rooms is on. Let a window map to
  a list of rooms (e.g. a window shared by two rooms lights for either one).
- **Neighbours' windows:** use a fixed pseudo-random pattern of dimly lit windows at night, so the building
  doesn't flicker between renders.

## 4. Iterate with discipline (the most important part)

- **One change per round:** change exactly what the owner pointed at, nothing else. Unrequested "improvements"
  (new wall textures, extra materials) are the usual reason a round goes badly.
- **Preview first:** render a screenshot (day and night) before deploying, and look at it.
- **Ask when unsure:** if a request could mean two things ("the window is slightly less tall from the top of
  the door"), ask one multiple-choice question with ASCII sketches of each option.
- **Save every version:** keep a numbered copy of every version, and mark the approved ones. "Go back N
  versions" means restoring an exact earlier file, and it's normal for the owner to then go forward one.
- **Confirm the result:** after each deploy, say what changed in one or two lines, plus the version number
  that's now live.
