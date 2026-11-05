# v005 猫与小猪场景合成提示词

执行器：Codex 内置 GPT Image 2。执行日期：2026-10-15。三张独立合成，自动重试 0 次。每张输入顺序均为背景母版、v005 猫身份表、小猪身份表。

## S01 家庭

```text
Use case: compositing
Asset type: vertical 9:16 character-in-scene production still
Primary request: Edit Image 1 by adding exactly two approved characters: one real childhood-version long-haired calico kitten from Image 2 and one pale pink-white miniature piglet from Image 3. Preserve Image 1's living-room camera, crop, sofa, rug, window, plants, lighting, materials and geometry as closely as possible.
Input images: Image 1 is the authoritative background edit target. Image 2 is a multi-view identity sheet for exactly one kitten; it is the only cat authority and must not be copied as multiple cats. Image 3 is a multi-view identity sheet for exactly one piglet; it must not be copied as multiple pigs.
Placement: piglet stands naturally on the left-middle of the rug; kitten sits on the right-middle at nearly the same depth. Both full bodies are visible, separated, and large enough to read while leaving bottom subtitle-safe space. Their bodies angle slightly toward each other and their eyes meet.
Kitten identity: unmistakably the approved v005 real kitten — tall slightly oversized ears, large pale gray-green eyes, dark black-brown tabby mask, narrow light central muzzle/blaze, broad white chest, a continuous white fur ring around the neck, extensive white legs and tiny white paws, concentrated copper-orange patches on the side/rear, compact delicate kitten body, and a kitten-stage dark fluffy tail. Do not turn it into an orange-white kitten or an adult cat.
Piglet identity: pale pink-white skin with extremely short fuzz, round dark eyes, salmon-pink snout, small upright ears, compact body, short legs and tiny hooves.
Performance: calm neutral pre-dialogue moment; both mouths closed. Kitten tail rests or lifts naturally without becoming an adult plume; piglet nose slightly lifted.
Lighting/contact: integrate both into the existing left-side window light. Match color temperature, direction and softness. Paws and hooves press into the rug pile with coherent contact shadows and slight occlusion.
Constraints: exactly one v005 kitten and one approved piglet; no extra animals, people, clothing, collars, props, human-like limbs, text, logos or watermark. Keep realistic anatomy, correct limb count, grounded weight and 9:16 portrait composition.
Avoid: any orange-white cat, adult calico proportions, missing white neck ring, saturated neon-green eyes, duplicated identity-sheet views, background redesign, floating bodies, mismatched shadows, cartoon/3D/plush appearance.
```

## S02 办公桌

```text
Use case: compositing
Asset type: vertical 9:16 character-in-scene production still
Primary request: Edit Image 1 by adding exactly two approved characters: one real childhood-version long-haired calico kitten from Image 2 and one pale pink-white miniature piglet from Image 3. Preserve Image 1's home-office camera, crop, chair, desk, laptop, lamp, cabinet, rug, lighting, materials and geometry as closely as possible.
Input images: Image 1 is the authoritative background edit target. Image 2 is a multi-view identity sheet for exactly one kitten and the only cat authority. Image 3 is a multi-view identity sheet for exactly one piglet.
Placement: kitten sits safely on the right side of the desktop in front of clear wall space, not covering the laptop or lamp, with full body and kitten-stage tail visible. Piglet stands on the wooden floor in the open zone to the right of the chair and left of the drawer cabinet, fully visible and not intersecting chair wheels, desk legs or cabinet. Piglet looks up at kitten; kitten looks down at piglet.
Kitten identity: preserve v005 exactly — tall kitten ears, pale gray-green eyes, dark black-brown tabby mask, narrow light central muzzle/blaze, broad white chest and continuous white neck ring, extensive white legs and tiny white paws, limited concentrated copper-orange side/rear patches, compact delicate kitten body, and modest dark fluffy kitten tail. Do not use adult or orange-white cat traits.
Piglet identity: pale pink-white skin and short fuzz, dark round eyes, salmon snout, small upright ears, compact juvenile body and tiny hooves.
Performance: quiet curious work-interruption moment; both mouths closed. Kitten is securely seated with paws contacting desk; piglet has four hooves grounded.
Lighting/contact: match the existing left window light and soft indoor fill. Kitten has a stable desktop contact shadow; piglet has soft floor contact shadow. Correct perspective and occlusion, no pasted-on look.
Constraints: exactly one v005 kitten and one approved piglet; no extra animals, people, clothing, collars, added props, human-like limbs, readable text, logos or watermark. Preserve the 9:16 background.
Avoid: orange-white cat, adult cat body, missing white neck ring, kitten covering laptop, piglet cut by furniture, duplicated views, moved chair, floating animals, scale mismatch, cartoon/3D/plush appearance.
```

## S03 公园

```text
Use case: compositing
Asset type: vertical 9:16 character-in-scene production still
Primary request: Edit Image 1 by adding exactly two approved characters: one real childhood-version long-haired calico kitten from Image 2 and one pale pink-white miniature piglet from Image 3. Preserve Image 1's park camera, path, grass, leaves, bench, trees, lighting, materials and geometry as closely as possible.
Input images: Image 1 is the authoritative background edit target. Image 2 is a multi-view identity sheet for exactly one kitten and the only cat authority. Image 3 is a multi-view identity sheet for exactly one piglet.
Placement: both animals are together in the middle ground on the path near the grass edge, at comparable distance and believable juvenile scale. Kitten is on the left and half a body length ahead; piglet is on the right. Both move forward while turning heads slightly toward each other, with full bodies visible and lower subtitle-safe space preserved.
Kitten identity: approved v005 real kitten — tall oversized ears, large pale gray-green eyes, dark black-brown tabby mask, narrow light central muzzle/blaze, wide white chest and continuous white neck ring, extensive white legs and tiny white paws, concentrated copper-orange side/rear patches, small delicate kitten body, and a kitten-stage dark fluffy tail. Do not turn it into an adult cat or orange-white kitten.
Piglet identity: approved pale pink-white piglet with short fuzz, round dark eyes, salmon-pink snout, upright ears, compact juvenile body, short legs and tiny hooves. Piglet may be slightly larger in body volume than kitten.
Performance: natural gentle walking moment with believable alternating legs, grounded feet and coherent weight; both mouths closed; kitten tail moves naturally without becoming a giant adult plume.
Lighting/contact: integrate original dappled tree light into fur and skin. Add soft path contact shadows, correct foot occlusion, matching focus and depth.
Constraints: exactly one v005 kitten and one approved piglet; no extra animals, people, vehicles, clothes, collars, human-like limbs, text, logos or watermark. Preserve the original bench/path/tree arrangement and 9:16 portrait composition.
Avoid: orange-white cat, adult cat proportions, missing white neck ring, giant adult tail, duplicated animals, incorrect gait, floating feet, extreme bokeh, toy scale, cartoon/3D/plush appearance or mismatched light.
```
