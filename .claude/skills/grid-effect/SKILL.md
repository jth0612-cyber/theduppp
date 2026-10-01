---
name: grid-effect
description: Apply the "trending grid effect" to a photo — a white rule-of-thirds grid where one or two lines bend to interact with the subject (grabbed, lifted, traced, weighed down, or flowing along a leading line), with the subject cut out and layered so lines pass behind it. Use when the user hands over a photo and asks for the grid effect, 그리드 효과, or white grid lines on a photo.
---

# Grid effect

Learned from reference reels (pixifect Photoshop tutorial; designwith.p_; thekevinpiatek)
across footballers, a carpenter, a mountain, a church spire, a fern, a pigeon over a roof
and a bee on blossoms. The effect reads as *the subject is touching the grid*. Everything
below serves that illusion.

## 1. Base grid

- 3 × 3 rule-of-thirds: 2 vertical lines at 1/3 and 2/3 of the width, 2 horizontal at 1/3
  and 2/3 of the height. Full-bleed, edge to edge. No outer frame.
- Pure white, 100 % opacity, flat (no glow, no shadow).
- Stroke ≈ 0.3–0.4 % of the image width (12 px on a 3059 px-wide image). Every line,
  bent or straight, uses the same stroke.

## 2. Read the photo first

Decide, by looking:

1. **Subject** and its silhouette (person, animal, building, peak, plant, object).
2. **Contact candidates**: the points where the subject reaches outward —
   fingertips, raised fists, a kicking foot, a ball, a spire tip, a summit, a leaf tip, a beak,
   a roof corner.
3. **Leading lines** already in the photo: a cable, a flight path, a roof diagonal, a pitch
   line, a ridge.
4. **The subject's geometry language**: organic (bodies, plants, animals) or angular
   (mountains, roofs, machines).

## 3. Pick ONE interaction (rarely two)

| Interaction | When | Line behaviour | Seen in |
|---|---|---|---|
| **Grab / pull** | a hand or limb reaches toward a grid line | the nearest line bends so it runs *through* the hand; hand sits on top of the line. Symmetric pose → mirror the curve onto the opposite line | Mbappé (both verticals bowed outward to both hands) |
| **Lift** | a pointed top or raised fists sit just below a horizontal line | that horizontal rises into a wide, gentle bell whose apex meets the tip; the rest stays near its original height | Messi (two fists), church spire (golden ball) |
| **Wrap / dip** | a foot or object sits on/through a line | the line dips into a narrow U around it and comes back | Haaland's boot |
| **Trace** | an angular silhouette (peak, roof) meets a line | the line becomes straight segments running parallel to the silhouette, a small even offset outside it, kinks at grid intersections | mountain summit |
| **Sag** | a soft, drooping subject (leaf, cloth, a body resting) lies across a line | the line hangs like a rope beneath it, deepest under the subject's weight | fern |
| **Flow** | the photo has a strong leading line or direction of motion | a vertical (or horizontal) becomes a long S-curve that follows that direction and passes close to the subject's key point | carpenter (power cable, around the router), pigeon (beak → along the dormer roof) |
| **Taut / angular pull** | tension, sharp athletic pose | straight segments meeting at the hand in a V instead of a curve | Ronaldo |
| **Depth only** | delicate, busy or centred subject with no natural contact | no bending; the straight grid simply passes *behind* the subject | bee on blossoms |

Choosing: prefer the interaction the subject's action already implies (reaching → grab,
pointing up → lift, hanging → sag, moving → flow). Match geometry language: organic
subjects get smooth curves, angular subjects get straight segments.

## 4. Shape rules for a bent line

- Bend only the grid line **nearest** the contact point (within about one cell). All other
  lines stay perfectly straight — they are the reference that makes the bent one read.
- One bent line is the default. Two only when the pose is symmetric (both hands, both
  fists) or the two contacts are clearly separate.
- **Endpoints stay put**: on the frame edge at the line's original position, or (for Trace)
  at the grid intersections either side of the subject.
- Build from few anchors (start, contact, end; at most one extra): cubic Béziers with
  tangents parallel to the original line at the endpoints, so the line leaves the frame
  edge straight and eases into the bend.
- At the contact the curve passes exactly through the point (fingertip, ball centre, tip);
  its tangent there follows the subject's limb or edge, not an arbitrary angle.
- Amplitude is only what is needed to reach the contact. Never loop, never cross itself,
  never pass through the face or the main focal point.
- Lift is broad and subtle (rise spread across the full width); Grab and Wrap are local and
  pronounced; Sag is a single smooth catenary; Flow is one long S, top to bottom.

## 5. Layering (what makes it look real)

Stack, bottom to top:

1. Original photo
2. Straight grid lines
3. Subject cut-out (exact mask; Photoshop's Select › Subject or a background-removal model)
4. Bent line(s)
5. Mask on the bent line(s): erase it where the contact part of the subject (fingers,
   fist, boot, ball, spire ball, leaf) should sit in front

So straight lines vanish behind the body; the bent line rides over the subject but is
held, lifted or wrapped by the contact part. Blurred foreground or background elements
that are not the subject (bokeh blossoms, crowd) are not cut out — lines run over them.

## 6. Output

- Keep the photo's own aspect ratio and resolution; lines as vectors (SVG paths) over
  the photo, plus the cut-out as a separate PNG layer, then a flattened PNG export.
- State in one line which interaction was chosen and why, and offer the next most
  natural alternative.

## 7. Checklist before handing over

- Exactly 4 lines total, same stroke, white.
- The bent line clearly *touches* the subject at a meaningful point.
- Straight lines disappear behind the subject; nothing floats on top of a face.
- Endpoints sit where the original grid line met the frame edge (or intersection).
- The bend direction agrees with the subject's action or the photo's leading line.
