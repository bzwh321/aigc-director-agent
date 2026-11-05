# 双角色合成执行提示词 v001

执行器：Codex 内置 GPT Image 2。执行日期：2026-10-15。每张输入对应场景母版、猫身份表和猪身份表；调用三次，自动重试 0 次。

## S01 家庭生活区

```text
Use case: compositing
Asset type: vertical 9:16 character-in-scene production still
Primary request: Edit Image 1 by adding exactly two animals: one orange-and-white kitten and one pale pink-white miniature piglet. Preserve the existing living-room background, camera, crop, furniture, rug, window, plants, lighting, materials and geometry as closely as possible.
Input images: Image 1 is the authoritative background edit target. Image 2 is a multi-view identity reference for the one kitten; do not copy multiple views. Image 3 is a multi-view identity reference for the one piglet; do not copy multiple views.
Characters and placement: place the piglet standing naturally in the left-middle area of the rug, and the kitten sitting in the right-middle area of the same rug at nearly the same depth. Keep both full bodies visible, separated, and large enough to read while preserving bottom subtitle-safe space. Their bodies angle slightly toward each other and their eyes meet.
Identity: kitten must retain the approved round face, large dark eyes, tiny pink nose, orange crown/back/tail, white muzzle/chest/paws, short legs and fluffy realistic fur. Piglet must retain pale pink-white skin with extremely short fuzz, round dark eyes, salmon-pink snout, small upright ears, compact body, short legs and tiny hooves. Piglet body volume may be slightly larger than the kitten, but both are believable juveniles.
Performance: calm pre-dialogue moment. Kitten mouth closed, tail naturally raised; piglet nose slightly lifted. No exaggerated grin or human gesture.
Lighting/contact: integrate them into the existing left-side window light; match color temperature, direction and softness. Paws and hooves press into the rug pile with coherent contact shadows and slight occlusion. They must not look pasted on.
Constraints: output exactly one kitten and one piglet, no extra animals, no people, no clothing, no collars, no props added, no human-like hands or feet, no text, no logos, no watermark. Keep realistic animal anatomy, correct limb count, grounded weight and 9:16 portrait composition.
Avoid: background redesign, changed sofa or window, duplicated cats or pigs, identity-sheet grid, toy/plush/3D/cartoon look, floating bodies, mismatched shadows, giant or miniature scale mismatch.
```

## S02 办公桌工作区

```text
Use case: compositing
Asset type: vertical 9:16 character-in-scene production still
Primary request: Edit Image 1 by adding exactly two animals: one orange-and-white kitten and one pale pink-white miniature piglet. Preserve the existing home-office background, camera, crop, chair, desk, laptop, lamp, cabinet, rug, lighting, materials and geometry as closely as possible.
Input images: Image 1 is the authoritative background edit target. Image 2 is a multi-view identity reference for the one kitten; do not copy multiple views. Image 3 is a multi-view identity reference for the one piglet; do not copy multiple views.
Characters and placement: place the kitten sitting safely on the desktop toward the right side, in front of clear wall space and not covering the laptop or lamp, with its full body and tail visible. Place the piglet standing on the wooden floor in the open zone to the right of the office chair and left of the drawer cabinet, fully visible and not intersecting chair wheels, desk legs or cabinet. The piglet looks upward at the kitten; the kitten looks down at the piglet, creating a clear shared eyeline.
Identity: kitten must retain the approved round face, large dark eyes, tiny pink nose, orange crown/back/tail, white muzzle/chest/paws, short legs and fluffy realistic fur. Piglet must retain pale pink-white skin with extremely short fuzz, round dark eyes, salmon-pink snout, small upright ears, compact body, short legs and tiny hooves. Both are believable juveniles at coherent scale.
Performance: a quiet, curious work-interruption moment. Both mouths closed. Piglet has all four hooves grounded; kitten is stably seated with paws contacting the desktop.
Lighting/contact: match the existing left window light and soft indoor fill. Give the kitten a stable desktop contact shadow and the piglet a soft floor contact shadow. Preserve correct occlusion and perspective so neither looks pasted on or floating.
Constraints: output exactly one kitten and one piglet, no extra animals, no people, no clothing, no collars, no added props, no human-like hands or feet, no readable text, no logos, no watermark. Keep realistic animal anatomy, correct limb count, grounded weight and 9:16 portrait composition.
Avoid: changing the desk scene, moving the chair, duplicated animals, identity-sheet grid, kitten covering the computer, piglet cut by furniture, toy/plush/3D/cartoon look, giant scale mismatch, floating animals, mismatched shadows.
```

## S03 公园

```text
Use case: compositing
Asset type: vertical 9:16 character-in-scene production still
Primary request: Edit Image 1 by adding exactly two animals: one orange-and-white kitten and one pale pink-white miniature piglet. Preserve the existing park background, low camera, path, grass, leaves, bench, trees, lighting, materials and geometry as closely as possible.
Input images: Image 1 is the authoritative background edit target. Image 2 is a multi-view identity reference for the one kitten; do not copy multiple views. Image 3 is a multi-view identity reference for the one piglet; do not copy multiple views.
Characters and placement: place both animals together in the middle ground on the path near the grass edge, at comparable distance and believable scale. The kitten is on the left and half a body length ahead; the piglet is on the right. Both move in the same forward direction while turning their heads slightly toward each other, maintaining a readable shared eyeline. Keep their full bodies visible and leave lower subtitle-safe space.
Identity: kitten must retain the approved round face, large dark eyes, tiny pink nose, orange crown/back/tail, white muzzle/chest/paws, short legs and fluffy realistic fur. Piglet must retain pale pink-white skin with extremely short fuzz, round dark eyes, salmon-pink snout, small upright ears, compact body, short legs and tiny hooves. Piglet body volume may be slightly larger than kitten while both remain juveniles.
Performance/anatomy: natural mid-walk moment with believable alternating fore and hind legs, grounded feet, coherent body weight, kitten tail naturally raised and piglet ears oriented toward the kitten. No running, jumping or human gesture.
Lighting/contact: integrate dappled tree light into fur and skin according to the original scene. Add soft contact shadows on the path and accurate foot occlusion. Match camera focus, grain and depth so they do not look pasted on.
Constraints: output exactly one kitten and one piglet, no extra animals, no people, no vehicles, no clothing, no collars, no human-like limbs, no text, no logos, no watermark. Preserve 9:16 portrait composition and the original bench/path/tree arrangement.
Avoid: background redesign, duplicated cats or pigs, identity-sheet grid, incorrect gait or limb count, floating feet, extreme bokeh, giant or toy scale, plush/3D/cartoon appearance, mismatched light.
```
