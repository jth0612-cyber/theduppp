---
name: grid-effect
description: Apply the "trending grid effect" to a photo — a white rule-of-thirds grid where one or two lines bend to interact with the subject (grabbed, lifted, traced, weighed down, or flowing along a leading line), with the subject cut out and layered so lines pass behind it. Use when the user hands over a photo and asks for the grid effect, 그리드 효과, or white grid lines on a photo.
---

# Grid effect

Learned from reference reels (pixifect Photoshop tutorial; rob.sexton.chengdu "bent grid
effect" tutorial; designwith.p_; thekevinpiatek) across footballers, a monk holding prayer
beads on a hillside, a carpenter, a mountain, a church spire, a fern, a pigeon over a roof
and a bee on blossoms. The effect reads as *the subject is touching the grid*. Everything
below serves that illusion.

## 0. Failure modes (learned the hard way — read first)

A first attempt on 10 photos was rejected as "not sensual at all". The causes:

- **No actor, no contact.** Lines wandered *near* the subject (a little triangle floating
  above a summit, a wobble beside a facade). Every bent line must hook on ONE precise point
  that can plausibly grab, lift, hang or tow it: summit, tip, nose, flame, lamp, stem.
- **Tracing an existing edge.** Copying a roof or ridge line at an offset just draws the
  photo's own line twice. Do not trace unless the shape is a clean geometric figure that
  lands on grid intersections.
- **Timid, local bumps.** A straight line with a small gaussian bump reads as a glitch.
  The WHOLE line moves, from both fixed endpoints, and the move is bold — at least about a
  quarter of a cell, usually much more. If the contact sits almost on the original line,
  pick another line that has to travel to reach it (e.g. pull the bottom line up to a cone
  tip as a tent, rather than nudging the top line).
- **Wobbly splines.** Never pass a spline through 5–7 hand-placed points. Build each side
  as ONE cubic Bézier: endpoint handle along the original grid direction, contact handle
  along the motion/edge direction, long handles (≈ 1/3 – 1/2 of the span). Angular
  subjects get straight segments (tent, taut V) instead.
- **Two moves at once.** One bent line per image unless the pose is truly symmetric.
- **No verification.** Before showing, put the result next to the references at full
  size and zoom on the contact.

Moves that worked in the redo: reflection-tip pulls the bottom line into a deep U (lake);
summit lifts the top line in a Haaland-style long rise and steep drop; pendant lamp hangs
the top line as a taut V; cone tip holds the bottom line up as a tent; line threaded
through an apple-shaped window's stem slot; line dives into a fire pit and is hidden by
the near rim; arc seen only in the sky gap between trees and a curved facade; plane drags
the vertical line into an S, passing behind the fuselage to the nose; line draped over a
sea rock like a rope.

## 1. Base grid

- 3 × 3 rule-of-thirds: 2 vertical lines at 1/3 and 2/3 of the width, 2 horizontal at 1/3
  and 2/3 of the height. Full-bleed, edge to edge. No outer frame.
- Pure white, 100 % opacity, flat (no glow, no shadow).
- Stroke ≈ 0.25–0.4 % of the image width (12 px on 3059 px; 7.5 px in the monk reel).
  Every line, bent or straight, uses the same stroke.
- Grid positions can be taken from the crop tool's rule-of-thirds overlay; cropping to
  9:16 first is optional. Lines are vector shapes (pen tool, Shape mode, no fill).
- Bending in Photoshop: Add Anchor Point Tool on the line → drag the new anchor onto the
  contact point; leave it a corner for a Taut V, or pull its handles for a curve. Repeat
  per line.

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
| **Taut / angular pull** | tension, sharp athletic pose, or a hand holding something thin (string, beads, rope, rein) | ONE anchor added on the straight line and dragged onto the hand; the line stays two straight segments meeting there in a sharp V. Both endpoints stay put | Ronaldo, monk |
| **Converge** | one strong contact point lies between a vertical and a horizontal line | pull BOTH of them to that same point (each as a Taut V or a Grab curve) so two lines meet in the hand — the hand becomes the grid's knot | monk (left vertical + bottom horizontal both meet in the hand holding the beads) |
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
5. Contact cut-out on top: just the contact part (fingers, fist, boot, ball, spire ball,
   leaf tip) selected tightly (Object Selection Tool around the hand → Ctrl+J → layer to the
   top), so it sits in front of the bent line(s)

Minimal variant (rob.sexton.chengdu): skip layer 3 and do only layer 5 — every line runs
over the photo and only the small contact part is lifted on top. Use it when a full
cut-out would be messy (hair, fur, low contrast against the background) or when the
lines crossing the body read well; the grab illusion comes from the contact layer alone.

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

## 8. More moves (from a second batch of reference reels)

- **Pinch:** fingertips pinch a grid intersection. The crossing point moves to the
  fingertips and every line through it becomes a straight line to its original
  endpoints, so the whole grid tilts toward the pinch (statue).
- **String between two hands:** one straight taut line runs from one hand to the other;
  the rest of the grid tilts slightly to agree with it (seated Buddha).
- **Hand with several strings:** two or three lines converge into one hand like reins
  (standing Buddha).
- **Hug the outline:** a vertical bends around a heel or limb with a small, tight radius,
  and a horizontal tucks under the sole, both returning to straight right after (football boot).
- **Lens warp:** the whole grid bends with the photo's own perspective or fisheye
  distortion, following curved structures (arches, cables); a foreground hand covers it
  (fisheye portrait).
- **Perspective grid:** in a one-point-perspective scene the lines converge on the
  vanishing point, so the grid reads as part of the space.
- Vary the move inside a batch: never use the same kind of interaction twice in a row.

## 9. What landed with the user (batch 19–24, "much better")

Approved: pinch at a tree tip, fisheye lens warp in a sky opening, a lid traced over a
skyline, gravity lensing around a sun reflection, reins into an upturned face, and a wire
strung between two traffic lights (chosen over a vanishing-point starburst, which read as
"tacky", a finish tape and an eye-shaped opening). Lesson: pick a small, concrete object
in the photo (signal, tip, glare, face) and give the line a believable physical role
(wire, rein, tape, pinch); avoid purely geometric gimmicks.

## 10. Redo lesson (07, 10, 12, 13)

Rejected as "all weird": a line burnt into curled ends, a loop for a breaking wave,
dashed "rain" lines, V-shaped bow waves, and occlusion faked with rough rectangles.
Picked instead: taut straight lines only, each ending exactly on a real object, with
real masks so the lines go behind it — a grid crossing pinched into the tallest
flame tip, two verticals tied to a sea rock like mooring ropes, and a vertical that
shifts onto a hanging rain chain and becomes the chain. Lesson: never add
decorative shapes (curls, loops, dashes) to show a story; let one straight line
touch one real object. If an earlier, simpler version is better, keep it.
