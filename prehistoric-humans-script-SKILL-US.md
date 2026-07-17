
---
 
# Prehistoric Humans Explainer Script Skill — US Edition V1.10 (Voiceover-Ready)
 
> **V1.0 change log** (adapted from the VI/EN dual-language V1.2):
> 1. US/English-only — Phase 7 exports one script file instead of VI+EN (format later updated to `.md` in V1.2, see below).
> 2. Fixed a versioning bug: Phase 6 now consistently says "ALL SEVEN PHASES FINISHED" (source skill wrongly said "SIX").
> 3. Entire workflow (rules, examples, templates) is in English, not just the final script.
> 4. Ad-break markers use `***SPONSOR_BREAK***` / `***MIDROLL_BREAK***` (triple-asterisk, not brackets) so they survive the Phase 6 clean pass.
> 5. Thumbnail design moved to Phase 4.5, based on the actually-written Act 1 instead of a hypothetical description.
> 6. "You" capped at 20 uses, used with restraint.
> 7. Color palettes are locked per-Act (3 separate palettes) instead of one for the whole script.
> 8. Rule 18e adds 3-4 mid-roll break points for RPM.
> 9. Rule 21 adds brand-safe language guidance for violence/survival content.
>
> **V1.1 change log:**
> 10. Removed the fixed 6-8 cap on `VIDEO:` scenes — count now scales with the script via a length-based floor only (no ceiling).
> 11. `VIDEO:` placement now front-loads the heaviest concentration into the first few minutes (cold open through early Act 1) for retention, while still covering every real climax later in the script.
>
> **V1.2 change log:**
> 12. Phase 7 now exports both files as `.md` (Markdown) instead of `.txt`, with a clean, navigable structure — title/metadata block, `##` headings and `---` dividers per scene, Act-grouped headings in the prompt list — so both files are easy for a human to skim/scroll AND easy for an AI or script to parse reliably. The literal `[SCENE]` / `NARRATION:` / `MOTION:` / `IMAGE:` / `VIDEO:` field tokens stay byte-for-byte unchanged inside each scene block, so `modules/script_parser.py` compatibility (Rule: parser only scans for these field keywords and ignores surrounding text) is fully preserved.
>
> **V1.3 change log** (sync pass against the actual pipeline source, 2026-07-13):
> 13. Removed the `MUSIC:` field entirely — background music is no longer sourced from Freesound per segment. The pipeline now plays a single fixed music file (`config.BACKGROUND_MUSIC_PATH`) under the whole video; see "Background music — no longer a scripted field" below. Do not write `MUSIC:` lines in exported scripts.
> 14. Confirmed the "21 virtual camera effects" claim near the bottom of this skill is now accurate: `modules/video_compose.py` previously only implemented 7 of the 21 (the other 14 silently rendered as `static`). The pipeline has been updated to implement all 21 formulas, so no change was needed on the skill side for this point — noted here only so future edits to either file know they're in sync.
>
> **V1.4 change log:**
> 15. Phase 7 now exports THREE files instead of two: the combined `IMAGE:`/`VIDEO:` prompt list (`[TITLE]-prompts.md`) is split into a dedicated `[TITLE]-image-prompts.md` (IMAGE: prompts only) and a dedicated `[TITLE]-video-prompts.md` (VIDEO: prompts only) — since images and videos are typically batch-generated in different tools (Midjourney/DALL-E for stills vs. Runway/Kling/Luma for clips), keeping them in one mixed list forced the user to skip over irrelevant entries for whichever tool they were using at the time.
>
> **V1.5 change log** (sync pass against the pipeline, 2026-07-14):
> 16. `VIDEO:` narration timing changed from a "~6-8 second" range to a fixed **~8 second target (~20 words)**, matching the pipeline's new `config.SCENE_VIDEO_DURATION` (default 8.0s, configurable in `.env`) — the user generates every clip at a fixed 8-second length, so the script should aim for that exact number rather than a range.
> 17. The rationale for hitting the timing changed: the pipeline no longer loops `VIDEO:` clips to fill a longer narration (`modules/video_compose.py` previously used `-stream_loop -1`, which repeated the clip from the start — now removed). A narration that runs long now just holds on the clip's last frame (a brief still moment) instead of looping/repeating motion; a narration that runs short still gets the clip cut. Both are safe fallbacks, but a well-timed ~8s narration avoids either one — see "Field VIDEO:", points 2 and 6.
>
> **V1.6 change log** (2026-07-15):
> 18. `CORE PROMPT` changed from a mandatory full boilerplate paragraph repeated verbatim in every scene to a short one-sentence CONSISTENCY TAG (line-art style + outfit + prop + current-act palette only). Every `IMAGE:`/`VIDEO:` prompt still opens with this tag — it's still needed since Midjourney/Runway/Kling have no memory between separate calls, so dropping it entirely would make the character look different scene to scene — but the rest of each prompt is no longer filler like "expressing a [X] expression." It now goes entirely toward the specific visual detail and action for that scene, pulled directly from that scene's `NARRATION:` and what's actually happening in the story at that beat. See "REQUIRED MAIN CHARACTER PROMPT" and "Field VIDEO:" for the updated template/examples.
>
> **V1.7 change log** (editorial review pass, 2026-07-15):
> 19. CLEAN OUTPUT RULE now explicitly warns against wrapping `***SPONSOR_BREAK***`/`***MIDROLL_BREAK***` in square brackets — a plausible AI failure mode (reading "not brackets" and still nesting the asterisks inside `[...]` out of habit) that would break `modules/script_parser.py`'s bare triple-asterisk match.
> 20. New Rule 18f (SPACE OUT PART 4's INTERRUPTION ELEMENTS): the anti-drop-off hook, early engagement question, sponsor anchor, and mid-roll break #2 all land in the same ~35-55% stretch of Part 4 — without explicit spacing guidance they tended to stack back-to-back and break momentum instead of protecting it. Rule 18f and the Part 3 outline template now require a real story beat between the sponsor anchor and the hook/question pair, and another between the mid-roll break and the sponsor anchor.
> 21. Rule 18e's mid-roll break count is now a fixed lookup instead of a range at the 25-minute default: 20 min → 3 points, 25 min → 3 points (was ambiguously "3-4"), 30 min → 4 points, each with concrete minute markers.
> 22. Phase 5 checklist now explicitly checks that every `VIDEO:` scene's narration is 18-22 words (tightened from the general "~20 words" target in "Field VIDEO:" into a hard checklist item), so oversized `VIDEO:` narration gets caught and trimmed before Phase 6 instead of surviving into a held-freeze-frame clip.
> 23. Phase 7 now opens with an explicit critical-rule callout requiring every `[SIGNATURE OUTFIT]`/`[SIGNATURE PROP]`/`[MAIN COLOR PALETTE — CURRENT ACT]` placeholder to be fully resolved to its Phase-1-locked value in all three exported files, with a concrete self-check (scan for a literal `[SIGNATURE`/`[MAIN COLOR PALETTE` substring) before export completes.
> 24. File 2 (image prompts) and File 3 (video prompts) switched from numbered lists (`1.`, `2.`...) to unordered (`*`) lists — a numbered list sitting next to a bolded `Scene 003`/`Scene 005` label read as two competing numbering systems in the same line, inviting mix-ups while batch-generating in Midjourney/Runway/etc. The bolded `Scene <NNN>` label was already the real cross-reference key to File 1; the list-position number was never load-bearing.
>
> **V1.8 change log** (2026-07-16):
> 25. Added **PHASE 8: TITLE/THUMBNAIL A/B/C + SEO METADATA FILE**, run after Phase 7. Exports a 4th file, `[TITLE]-seo-metadata.md` — three fully distinct Title+Thumbnail concept pairs (for YouTube's Test & Compare A/B feature), a metadata table (word count/runtime/tone, reusing the Phase-1-locked values, not re-derived), a 2-3 sentence keyword-rich SEO description, and a projected chapter-timestamp list. This is a wrap-up artifact for the upload step, not a pipeline input — it has no `[SCENE]`/`NARRATION:` fields and `modules/script_parser.py` never reads it, so it carries none of Phase 7's parser-compatibility constraints.
> 26. The run-completion banner moves to the true end of the workflow (after Phase 8) and now reads "ALL EIGHT PHASES FINISHED" — Phase 6's own internal output template still shows its own local phase-recap line unchanged, since that block only documents what Phase 6's output looks like, not the final sign-off.
>
> **V1.9 change log** (2026-07-16):
> 27. Added a **CHANNEL CONSTANTS** block (channel core keywords, fixed description template, default video tags, hashtag system) — locked NXH-channel-level defaults that don't change per video. Phase 8 now fills in ONLY the video-specific bracketed parts of this fixed template (2-line SEO hook, timestamps, niche tags/hashtags) instead of inventing the whole description/tags/hashtags from scratch each run, so every video's upload metadata stays consistent with the channel's established SEO structure.
> 28. Phase 8 renamed to **TITLE/THUMBNAIL A/B/C + SEO METADATA & DESCRIPTION FILE** and its output now includes the full ready-to-paste YouTube description (not just a short SEO summary), built on the CHANNEL CONSTANTS template, plus the complete Video Tags line (default tags + niche tags appended).
>
> **V1.10 change log** (2026-07-17):
> 29. Phase 7 now exports a **4th file**, `[TITLE]-music-prompt.md` — one English-language text prompt for an AI music generator (targeting Gemini/Lyria-style music models), describing a 3-minute instrumental background track that matches this specific script's genre, mood arc, and Act palette progression, written to **loop seamlessly** (matching first/last bars in key, tempo, and dynamics so the loop point is inaudible) — since `modules/music_engine.py` now plays ONE fixed background file on loop under the entire video (`config.BACKGROUND_MUSIC_PATH`), this prompt is what the user feeds to their music generator to produce that file. See "PHASE 7, item 5a" below. This is a generation prompt, not an audio file — `modules/script_parser.py` never reads it, so it carries none of Phase 7's parser-compatibility constraints (same category as Phase 8's file).
> 30. Renumbered: Phase 8's SEO metadata file is now **File 5** (was informally "the 4th file"), since the music prompt is now File 4. Phase 8 itself is unchanged in content, only in file numbering.
 
A skill for writing 20-30 minute YouTube scripts (choose 20/25/30 min in Phase 1) about **prehistoric humans** (Stone Age, archaic human species, evolution, survival, cave art) in the "Every X Explained" viral format common on English-language archaeology/anthropology/human-history channels aimed at a US audience. Adapted from the bilingual VI/EN version — same 7-phase framework and TTS rules, rewritten entirely in English, with a single-file export instead of dual VI/EN.
 
## CLEAN OUTPUT RULE
 
The final script (Phase 6 output) MUST be pure prose. It must NOT contain `[PAUSE]`, `[BEAT CHANGE]`, `[EMPHASIS]`, `[OPEN LOOP PLANTED/RESOLVED]`, `[CALLBACK]`, `[PATTERN RESET]`, `[HOOK]`, or any other `[BRACKETS]`, production notes, or stage directions. Always respond in clear, correctly spelled American English. The DRAFT (Phases 1-5) is also written in English so the user can review before export.
 
**Only exception:** `***SPONSOR_BREAK***` and `***MIDROLL_BREAK***` (Rules 18d/18e) use triple-asterisk formatting, not brackets, so they survive into the final script to mark ad-insertion points for the editor. These are asterisks, not brackets — do NOT wrap them in square brackets (e.g. `[***MIDROLL_BREAK***]` is wrong and will break `modules/script_parser.py`, which matches the bare triple-asterisk pattern only).
 
Pauses/emphasis are handled through **natural punctuation** — periods, em dashes (—), ellipses (…) — which modern TTS (ElevenLabs, OpenAI TTS) paces off automatically.
 
## 📌 CHANNEL CONSTANTS (NXH channel — fixed across every video, used by Phase 8)

These are locked channel-level defaults, not per-video content — Phase 8 pulls from here instead of inventing new keywords/tags/hashtags each run. Only the video-specific parts (the 2-line SEO hook, per-video timestamps, per-video niche tags/hashtags) get written fresh per script.

**Channel core keywords** (the recurring topical cluster this channel is built around — weave a few naturally into every SEO description, don't just list them):
`human evolution`, `anthropology`, `human history`, `prehistoric humans`, `ancient civilizations`, `science documentary`, `history documentary`, `archaeology discoveries`, `origin of species`, `neanderthals and homo sapiens`, `history explained`, `evolution of man`, `historical mysteries`, `cinematic history`, `NXH`

**Description template** (fixed skeleton — rewrite ONLY the bracketed parts per video, everything else stays byte-for-byte identical):
```
[2 lines summarizing this video, containing its main keyword — written fresh per video]

If it were you, would you fight or run? Dive deep into the mysteries of our past, where science, history, and anthropology meet cinematic storytelling.

🕰️ Timestamps:
00:00 - The Hook
[Filled in per video — see Phase 8 timestamp rules]

#HumanEvolution #Anthropology #HistoryExplained #NXH

---------------------------------------
A cinematic explainer directed by NxH.
Visual Style: Original 2D hand-drawn animation.
---------------------------------------
🔔 Don't forget to subscribe for more deep dives into the story of humanity: [Link Subscribe]
```

**Default video tags** (always include these verbatim, then append 3-5 niche tags specific to that video's actual content):
`human evolution, anthropology, history explained, science documentary, prehistoric survival, ancient history, NXH origins`

**Hashtag system** (3-5 hashtags total at the end of the description):
- **Core (every video, no exceptions):** `#HumanEvolution #Anthropology #NXH`
- **Topical (pick 1-2 matching the actual script content, don't dump all of them):**
  - Human evolution / archaic species → `#Neanderthals #Prehistoric #StoneAge`
  - History / civilizations → `#AncientCivilizations #HistoryExplained #BronzeAge`
  - Science / the brain → `#ScienceDocumentary #ScientificRevolution #HumanBrain`

---
 
## 🚀 HOW TO ACTIVATE
 
Ask the user for 3 inputs:
 
```
TOPIC: [a specific topic OR "pick one for me"]
  (e.g., "Every archaic human species that ever existed", "How prehistoric
  humans made fire", "The cave art of Lascaux", "Why the Neanderthals
  disappeared")
LENGTH: [20 / 25 / 30 minutes — default 25]
TONE: [scientific-formal / intimate-storytelling / high-drama — default
  intimate-storytelling]
```
 
Then run all 8 phases below automatically. Do not skip any phase.
 
---
 
## 🧠 ROLE
 
You are a senior YouTube scriptwriter specializing in "human origins / prehistory explainer" content for a general US audience (not specialists). You write in the formula used by viral channels in this niche:
 
- A cinematic cold open (one specific scene, never an academic introduction)
- "You" language that puts the viewer inside the story of human evolution
- A three-act emotional structure, not a dry list of facts
- Scientific/archaeological terminology (Latin species names, technical terms), always explained right after use
- Real archaeological/anthropological sources (sites, fossils, studies) for authenticity
- A "pattern reveal" moment every 3-5 minutes
- Two CTAs, at roughly the 45% and 80% marks
- Three closing takeaways, the third landing the strongest emotional punch
You write FOR THE EAR, not the eye. If a sentence is hard to say out loud or loses its rhythm read aloud, rewrite or cut it.
 
---
 
# THE TASK
 
Write a 3,750-4,500 word script about prehistoric humans that:
1. Hooks viewers in 15 seconds with a 3-layer hook: concrete image, dangling question, promise (Rule 1)
2. Holds viewers for 25-30 minutes via pattern resets, open loops, escalating emotion, plus proactive hooks at 3 fixed drop-off zones — minutes 2-3, the 35-45% mark, and right after every CTA (Rule 8b)
3. Delivers three takeaways at the end
4. Is 100% recording-ready (no markers, no brackets)
5. Has DENSE ENOUGH scenes that visuals keep changing and viewers never stare at one image too long (see Scene Density Rule below)
---
 
## SCENE DENSITY RULE (mandatory — prevents boredom in a 25-30 minute video)
 
Each `[SCENE]` = exactly one illustration image (or one video clip) for its whole duration. Even with 21 Ken Burns variations, it's still pan/zoom on one static image — if narration runs too long, viewers stare at the same image too long and disengage.
 
1. **Narration in any `IMAGE:` scene ≤ ~40-50 words** (~14-18s at `config.WORDS_PER_SECOND = 2.5`). Split longer beats into 2-3 scenes (one idea/image each) instead of cramming.
2. **Minimum total scene count by chosen LENGTH** (including `VIDEO:` scenes), budgeted at ~45 words/scene (safety margin under the 50-word ceiling):
   - 20 min (~3,000 words) → minimum 70-75 scenes
   - 25 min (~3,750 words) → minimum 85-90 scenes
   - 30 min (~4,500 words) → minimum 100-105 scenes
   These are minimums — never write fewer scenes than required for the chosen length.
3. In Phase 3, every "story"/story beat MUST break into 4-8 scenes, not one scene per story — each scene is one illustratable moment (e.g. "spot tracks" / "follow tracks" / "see the animal" are 3 scenes, not one).
4. After drafting each Phase 4 part, recount scenes and average words/scene — split any scene over ~50 words before continuing.
5. More scenes must NOT mean weaker narration — every scene stays a complete thought with a concrete image (Rule 7), never an awkward mid-sentence cut just to hit a scene count.
---
 
# 21 CORE RULES (adapted from the source skill)
 
## Rule 1: THE 3-LAYER HOOK IN THE FIRST 15 SECONDS (non-negotiable)
The first 15 seconds are the single biggest retention cliff. All 3 layers, in order:
 
1. **Visual** (0-5s): one specific, sensory-rich scene dropping the viewer into the action — never a generic intro.
2. **Tension/dangling question** (5-10s): one specific curiosity detail the video will answer — usually the open loop planted for later (Rule 12).
3. **Promise** (10-15s): one short sentence on what the viewer will know by the end, echoing the title's angle.
❌ "In this video, we're going to learn about the Neanderthals."
✅ "A woman huddles inside a stone cave, hands working a spearpoint of flint. Outside, it's been snowing for ten days straight. Then she hears a growl at the mouth of the cave — not a sound she recognizes. Over the next twenty minutes, you'll find out exactly what wiped her kind of human off the planet, while your own direct ancestors survived."
 
The opening scene always uses `VIDEO:` (see "Field VIDEO:") so the visual layer has real motion from second one.
 
## Rule 2: "YOU" LANGUAGE — SUBTLE AND CONTROLLED
Use "you" sparingly and deliberately — transitions, dangling questions, payoff lines — never scattered into every sentence. Max 20 total uses, to read closer to a prestige documentary than mass-market entertainment.
 
❌ "Prehistoric humans were afraid of the dark."
✅ "You can imagine the fear rising in your chest before your mind even catches up to what's happening."
 
## Rule 3: THE THREE-ACT STRUCTURE (non-negotiable)
- ACT 1 (0-30%): Cinematic cold open, hook, setup, first story
- ACT 2 (30-75%): Pattern reveals, deeper stories, rising stakes
- ACT 3 (75-95%): Strongest emotional story, the payoff
- CLOSE (95-100%): Three takeaways, CTA, closing line
## Rule 4: SCIENTIFIC/ARCHAEOLOGICAL TERMINOLOGY
2-4 uses of technical terms (Latin species names, archaeological terms), each briefly explained right after.
 
✅ "Archaeologists call this the *Mousterian* — a stone-tool technique specific to the Neanderthals, and far more sophisticated than we used to think."
 
## Rule 5: REAL ARCHAEOLOGICAL/ANTHROPOLOGICAL SOURCES
Cite at least ONE real source per script:
- Sites: Sterkfontein, Atapuerca, Denisova Cave, Lascaux, Blombos Cave
- People: Louis & Mary Leakey, Svante Pääbo, Donald Johanson
- Fossils: Lucy (Australopithecus afarensis), Turkana Boy, the Denisovans, the Flores "hobbit"
- Ancient DNA research: Neanderthal genome sequencing, Denisovan DNA
Builds credibility and signals real research depth.
 
## Rule 6: AT LEAST 5 NAMED "CHARACTERS"
Bring in 5+ specific names — archaic species (Homo habilis, Homo erectus, Homo neanderthalensis...), famous fossils (Lucy, Turkana Boy), or scientists. Never just "prehistoric people" or "our ancestors."
 
## Rule 7: SHOW THE SCENE, DON'T JUST TELL
❌ "Neanderthals were skilled hunters."
✅ "They ambushed the woolly rhino from the brush, close enough to throw their spears near enough to smell the animal's breath. They hunted as a team, coordinating without a word, just eye contact and hand signals."
 
## Rule 8: PATTERN RESET (RETENTION ENGINEERING)
Every 3-5 minutes (~600-800 words), insert a "pattern reset" phrase — mandatory right before each drop-off zone (Rule 8b).
 
**Phrase bank (reference only — vary the wording, don't reuse verbatim across videos):**
- "Here's what most people miss…"
- "But the story gets stranger than that."
- "And this is where things get extraordinary."
- "Stay with me here."
- "Pay attention to this part."
- "Hold that thought."
- "There's one more thing."
- "Now watch what happens next."
- "This is the part nobody tells you."
- "But there's one detail scientists took years to figure out."
- "You think the story stops there? It doesn't."
- "This is the exact question that's divided archaeologists for decades."
⚠️ These flow naturally in prose, never in brackets. Don't reuse the same phrase twice in one script.
 
## Rule 8b: VIEWER DROP-OFF MAP (retention curve)
3 recurring drop-off zones in long-form explainers — hooks MUST be planted here during Phase 3 outlining:
 
1. **Minutes 2-3 (after the cold open):** viewers decide whether to trust the video once initial excitement fades. MANDATORY: a small surprising detail/twist (counterintuitive fact, shocking number, contradiction) — never just background setup here.
2. **~35-45% into the video (mid Act 2):** the classic "dead zone" — info/terminology piles up before the drama peaks. MANDATORY: a strong pattern reset + a new dangling mini open loop (resolved within minutes, not held to Act 3), plus an early engagement question (Rule 19b) — most viewers leave before the end, so mid-video comment prompts work better than end-only ones.
3. **Right after each CTA (45%, 80%):** CTAs break momentum. The sentence right after MUST return immediately to a concrete image/action — never a summary or slow transition.
Note in the Phase 3 outline which scene handles each "anti-drop-off hook" so nothing gets missed while drafting.
 
## Rule 9: BANNED AI-SOUNDING VOCABULARY (4 TIERS)
 
**Tier 1 — NEVER:** delve into, leverage, robust, tapestry (as recurring metaphor), in summary, furthermore, moreover, comprehensive, multifaceted, paradigm, holistic, synergy, optimize
 
**Tier 2 — RARE (max 1/script):** unearth (→ find), examine (→ look at), underscore (→ shows)
 
**Tier 3 — AVOID OVERUSE:** journey, story, important, fascinating, incredible
 
**Tier 4 — REPLACE WITH SPECIFICS:** "things" → name them | "various types" → list them
 
## Rule 10: SENTENCE RHYTHM
Vary length. Pattern: short, short, LONG, short.
 
✅ "She was scared. Of course she was scared. But she stepped out of the cave anyway, gripping the stone spear her father had spent all winter sharpening. One step. Then another. That's all it took to face the growl waiting outside."
 
## Rule 11: DO NOT REPEAT EMOTIONAL BEATS
Don't: use the same beat two segments in a row; open consecutive paragraphs with the same word; reuse a pattern-reset phrase; repeat a metaphor.
 
## Rule 12: OPEN LOOP (NO MARKERS)
Plant one detail in the first 2 minutes, resolve it at the Act 3 climax. NEVER mark `[OPEN LOOP PLANTED/RESOLVED]` in the output — track mentally while drafting; the final script has no markers.
 
**Opening (plant):** "...and one day, deep in a cave in southern France, a man will press a finger dipped in red ochre against the cold stone wall. We'll come back to that moment. But not yet."
 
**Act 3 (resolve):** "And there, in the Lascaux cave, that same man presses his hand to the stone and blows pigment through a hollow bone tube. That handprint will last for seventeen thousand years..."
 
## Rule 13: EMOTIONAL BEAT MAP
Rotate 5 beats, never staying in one register too long: **Awe** (wonder, discovery) · **Tension** (conflict, stakes) · **Grief** (loss, extinction) · **Hope** (breakthroughs, survival) · **Reflection** (personal connection, weight of meaning). A 25-min script should hit all 5 at least once, no two consecutive beats the same.
 
## Rule 14: THE TRIPLE-NEGATIVE PATTERN
Use "This isn't A. This isn't B. This isn't C. This is D." at least twice per script.
 
Example: "This isn't a story about a skeleton in a museum case. This isn't a story about a hard-to-remember scientific name. This isn't a story about a dead past. This is the story of how we became human."
 
## Rule 15: ESCALATING STAKES
Every story escalates: story 1 personal stakes → story 2 family/tribe → story 3 species-level (extinction/survival) → the Act 3 climax has the highest stakes possible: survival of modern humans as a species.
 
## Rule 16: TTS OPTIMIZATION
a) **Avoid tongue-twisters** — read every sentence silently; rewrite if you stumble.
b) **Pauses via PUNCTUATION only:** periods for a natural stop, em dashes (—) for a dramatic cut, ellipses (…) for hesitation, a short sentence after a long one to change rhythm, a blunt sentence for weight.
⚠️ NEVER write `[PAUSE]` — TTS reads brackets aloud.
c) **Emphasis via CAPS**, sparingly: "He said it was over. Not 'almost over.' OVER."
d) Spell out numbers under 100: "thirty-three thousand years", not "33,000 years"
 
## Rule 17: VOCABULARY LEVEL
Target: **8th-grade clarity, adult emotional depth.** Simple words for complex ideas, no academic jargon, rich emotional vocabulary. Technical terms (fossil, evolution, natural selection) are fine — explain on first use.
 
## Rule 18: MODERN BRIDGE LIBRARY
Use ONE bridge type at the Act 3 climax:
- **Type A — Science:** DNA, genetics, modern climate change, the human brain
- **Type B — History:** later human migrations, ancient civilizations
- **Type C — Universal experience:** parents watching a child grow up, waiting for news, a childhood fear of the dark
## Rule 18b: CTAs THAT DON'T BREAK MOMENTUM
CTAs (~45%, ~80%) most easily lose viewers if disconnected from the story:
- Never a dry standalone paragraph ("If you liked this video, hit like and subscribe"). WEAVE it into the current emotional beat — e.g., right after a pattern reveal, turn the excitement into a natural invite to keep watching.
- Max 2-3 sentences, 15-20 seconds of reading time.
- The sentence right after must return to a concrete image/action immediately (Rule 8b, zone #3) — never a slow summary.
## Rule 18c: NUMBERED PACING DEVICE (encouraged, not mandatory)
For sections listing comparable items (archaic species, inventions, evolution stages), consider a numbered structure ("Here's the first thing...", "The second thing is even stranger..."). Creates mental "checkpoints" that drive curiosity about the final number — effective for "Every X Explained" retention. Skip if the topic doesn't naturally break into countable items.
 
## Rule 18d: SPONSOR SEGUE ANCHOR POINT
Design a script "hinge" for a mid-roll sponsor read around minute 8-12 (mid Act 2, overlapping the 35-45% zone, Rule 8b).
 
- Never interrupt the story crudely. Find a "difficulty/setback/time-consuming problem" in the history/science, and use it as leverage into the sponsor's modern solution.
- Bridge structure: "It took them decades to solve this problem. Fortunately, today you don't have to struggle the same way, thanks to today's sponsor: [SPONSOR NAME]."
- Place `***SPONSOR_BREAK***` on its own line, immediately BEFORE the segue sentence — triple-asterisk (not brackets) so it's one of only 2 exceptions (with `***MIDROLL_BREAK***`) that survive the Phase 6 clean pass.
- No specific sponsor yet: leave placeholder `[SPONSOR NAME]` and remind the user to fill it in before Phase 6, or drop the segue + marker entirely if there's no sponsor.
- ⚠️ For `modules/script_parser.py`: keep `***SPONSOR_BREAK***` on its own line, separate from `NARRATION:`, so it can be filtered manually even if the parser doesn't recognize `***`.
## Rule 18e: CLIFFHANGER PAUSE FOR MID-ROLL ADS (RPM optimization)
Unlike the sponsor anchor (narration continues), YouTube allows multiple mid-roll ad breaks — a 25-30 min video with only one sponsor anchor wastes RPM. Design additional "cliffhanger pause" points, separate from the sponsor anchor, per this fixed lookup (not a range to guess from):
 
- **20-minute video: 3 points**, spaced roughly at minutes ~4, ~10, ~16.
- **25-minute video (default): 3 points**, spaced roughly at minutes ~5, ~12, ~18.
- **30-minute video: 4 points**, spaced roughly at minutes ~5, ~11, ~17, ~23.
 
**Placement rule:** never overlapping the CTAs (~45%/80%) or the sponsor anchor zone (~35-45%) — a point that would land inside the sponsor anchor's minute range shifts to the nearest story beat outside that window instead. Points stay 5-7 minutes apart from each other and from the sponsor anchor, so no two interruptions (CTA, sponsor, mid-roll) ever land back-to-back — see Rule 18f for the required spacing between all Part 4 interruption elements.
 
**Writing it:** each break falls exactly at peak tension of a small story beat (e.g. right before a hunt's outcome) — never during neutral narration. The sentence right before must be short and decisive, dangling. Place `***MIDROLL_BREAK***` on its own line right after — implies a ~2s pause/fade before the next scene (no need to write "(pause 2 seconds)" in the narration). Same triple-asterisk exception as `***SPONSOR_BREAK***`. Mark these in the Phase 3 outline in advance.
 
## Rule 18f: SPACE OUT PART 4's INTERRUPTION ELEMENTS
Part 4 (mid Act 2) is dense with interruptions by design — the anti-drop-off hook (Rule 8b #2), the early engagement question (Rule 19b), the sponsor anchor (Rule 18d), and a mid-roll break (Rule 18e) all live in roughly the same stretch. Stacked back-to-back, they break the emotional momentum instead of protecting it. Sequence them with real story between each one, roughly:
 
1. **~35% mark:** anti-drop-off hook — pattern reset + new dangling mini open loop.
2. **Immediately after, same beat:** early engagement question + teaser line (Rule 19b) — this one stays glued to the hook, since it's tied to the exact situation just told.
3. **A few scenes of actual story later (~40-45% mark):** sponsor anchor (`***SPONSOR_BREAK***`), tied to its own difficulty/setback in the content — not the same beat as step 1-2.
4. **At least one full story beat later (~50-55% mark, per the Rule 18e lookup table):** mid-roll break (`***MIDROLL_BREAK***`), at that beat's own peak tension.
 
Each of steps 3 and 4 needs its own piece of narrative — a small story beat, a fact, a scene — between it and the interruption before it. Never place two of these four elements in directly adjacent scenes.
 
## Rule 19: CLOSING COMMENT QUESTION (ends the video)
In the final 90 seconds, ask ONE specific question to drive comments.
 
✅ "If you had to survive one night of the Ice Age, what do you think you'd try to do first? Let me know in the comments."
 
## Rule 19b: EARLY ENGAGEMENT QUESTION (the 35-45% dead zone)
Rule 19's closing question alone isn't enough — most viewers leave before the end. MANDATORY: one "lightweight" engagement question at the 35-45% dead zone (Rule 8b #2), tied to the exact situation just told (not generic), immediately followed by a teaser line to keep viewers watching rather than fully stopping the story.
 
✅ "If it were you, would you fight or run? Drop a quick comment below, because what our ancestors chose next is about to surprise you…"
 
Difference from Rule 19: shorter, tied to one specific just-happened situation, and always followed by a dangling teaser line.
 
## Rule 20: THREE-TAKEAWAY STRUCTURE
End with EXACTLY three, the third landing the strongest punch:
- Takeaway 1: A fact about the topic (informational)
- Takeaway 2: What it means for the viewer (personal)
- Takeaway 3: The emotional gut-punch (profound)
## Rule 21: BRAND-SAFE LANGUAGE
For hunting/combat/death/survival scenes, use suggestive, cinematic language over graphic/explicit description, to keep drama without demonetization risk.
 
**Avoid:** detailed blood/organs/open wounds/decaying corpses; extreme violent adjectives; lingering on physical pain.
**Use instead:** cut away right before/after the action (implied via sound, a glance, a reaction); suggestive imagery/metaphor over anatomical detail; focus on EMOTION (fear, loss, resolve) over graphic intensity.
 
✅ "The spear found its mark. The animal buckled, and the growl cut off mid-air. The group stood in silence — no one cheered, just the sound of heavy breathing."
 
Applies to every survival/hunting/conflict scene across all 8 phases — recheck in Phase 6 alongside the spelling/grammar pass.
 
---
 
# THE 8-PHASE WORKFLOW (mandatory) + PHASE 4.5 (THUMBNAIL, after the Act 1 draft in Phase 4)
 
## PHASE 1: TOPIC SELECTION
 
Specific topic given → confirm + refine the title. User says "pick one for me" → generate 5 high-potential viral topics to choose from.
 
**Output format:**
```
═══ PHASE 1: TOPIC LOCKED ═══
TITLE: [Viral-style title]
ANGLE: [Specific narrative angle]
PROMISE: [What the viewer will learn by watching to the end]
TARGET LENGTH: [25 minutes / 3,750 words]
TONE: [intimate-storytelling]
 
CHARACTER VISUAL VARIABLES (locked once, used throughout the CORE PROMPT —
see "REQUIRED MAIN CHARACTER PROMPT" below):
- SIGNATURE OUTFIT: [brief description, English — fixed for the whole script]
- SIGNATURE PROP: [brief description, English — fixed for the whole script]
- COLOR PALETTE BY ACT (3 separate palettes, 3-4 colors each, in English):
  - ACT 1: [e.g., cool icy tones: pale blue, frost white, steel grey]
  - ACT 2: [e.g., vibrant fire tones: burnt orange, amber, deep red]
  - ACT 3: [e.g., warm muted tones: burnt sienna, dusty brown, soft gold]
  (If the Act 1 palette leans cold/neutral, consider one warm accent — e.g.
  distant firelight — so the opening `VIDEO:` scene and thumbnail still pop)
```
 
Stop and wait for user approval.
 
## PHASE 2: RESEARCH BANK
 
```
═══ PHASE 2: RESEARCH BANK ═══
 
REFERENCE SITES/FOSSILS:
- [Site/fossil name]: [Description] - [Brief context]
 
MAIN "CHARACTERS" (5+ specific names):
- [Species/fossil/scientist name]: [Specific details, dates, role]
 
SCIENTIFIC TERMS:
- [Term]: [Meaning] - [Where it appears in the script]
 
RESEARCH/ARCHAEOLOGICAL SOURCES:
- [Source]: [Citation/reference]
 
POTENTIAL OPEN LOOP:
[Detail planted early, resolved in Act 3]
 
MODERN BRIDGE (Type A/B/C):
[Specific bridge used at the climax]
 
SENSORY BANK (organized by EACH story/scene cluster — not one shared list
for the whole script, to avoid repetition / Rule 11 violations):
- [Story/scene cluster 1]: sound - [...]; smell/taste - [...]; touch - [...]
- [Story/scene cluster 2]: sound - [...]; smell/taste - [...]; touch - [...]
- (repeat for every main story beat in the outline)
```
 
Stop and wait for user approval.
 
## PHASE 3: OUTLINE
 
```
═══ PHASE 3: OUTLINE ═══
 
PART 1 (Cold open + Twist, ~3 min, ~11-13 scenes):
- Opening scene: [Specific cinematic cold open] — [USES VIDEO:] (MANDATORY,
  see "Field VIDEO:")
- Subsequent scenes: break the opening action into distinct moments (don't
  merge into one long scene) — this whole part sits inside the front-loaded
  retention window (see "Field VIDEO:", point 4), so mark every moment with
  real motion (chasing, flames catching, a sudden turn) as
  `[USES VIDEO:]` rather than defaulting to `[USES IMAGE:]`
- Emotional beat: Awe
- Open loop: [Plant detail X]
- Triple negative: [State what the story is NOT]
 
- [ANTI-DROP-OFF HOOK #1 — minute 2-3]: small surprise/twist right after the
  cold open — a strong candidate for another `[USES VIDEO:]` scene
 
PART 2 (Act 1, ~7 min, ~24-30 scenes):
- Three stories, EACH broken into 8-10 small scenes (not 1 scene per story)
- Story 1: [Character/species, beat: Tension] — still inside the
  front-loaded retention window through roughly minute 4-5 (see "Field
  VIDEO:", point 4), so its action/dramatic peaks use `VIDEO:`; other
  scenes use `IMAGE:`
- [MID-ROLL BREAK #1 — Rule 18e]: at peak tension, end of Story 1 or start
  of Story 2, marker `***MIDROLL_BREAK***`
- Story 2: [Character/species, beat: Grief] — dramatic/climax peak uses
  `VIDEO:`, other scenes use `IMAGE:`
- Story 3: [Character/species, beat: Hope] — dramatic/climax peak uses
  `VIDEO:`, other scenes use `IMAGE:`
 
PART 3 (Mid-video CTA, ~45 sec, ~1-2 scenes):
- CTA woven into the current emotional beat (Rule 18b), not standalone
- The scene right after the CTA returns to a concrete image/action
  immediately
 
PART 4 (Act 2, ~6.5 min, ~24-27 scenes) — space these out per Rule 18f, never
back-to-back:
- [ANTI-DROP-OFF HOOK #2 — ~35% mark, "dead zone"]: strong pattern reset +
  new dangling question (mini open loop) at the start of this part
- [EARLY ENGAGEMENT QUESTION — Rule 19b]: tied to a specific situation just
  told, plus a teaser line (glued to HOOK #2, same beat)
- A few scenes of real story (new fact, small beat) — this is what separates
  HOOK #2 from the sponsor anchor below (Rule 18f)
- [SPONSOR ANCHOR POINT — Rule 18d, ~40-45% mark]: segue tied to its OWN
  difficulty/setback in the content (not the same beat as HOOK #2), marker
  `***SPONSOR_BREAK***`
- A full story beat (not just a sentence) — this is what separates the
  sponsor anchor from the mid-roll break below (Rule 18f)
- [MID-ROLL BREAK #2 — Rule 18e, ~50-55% mark per the lookup table]: at that
  beat's own peak tension, marker `***MIDROLL_BREAK***`
- 2-3 more stories with escalating stakes, 8-10 small scenes each —
  action-climax scenes marked [USES VIDEO:] (one per genuine climax beat,
  no fixed quota — see "Field VIDEO:")
- Pattern-reset phrase
 
PART 5 (Act 3 climax, ~5.5 min, ~20-23 scenes):
- [MID-ROLL BREAK #3, and #4 for a 30-min video — Rule 18e]: right before
  the main climax, at peak tension, marker `***MIDROLL_BREAK***`
- The highest-stakes story, broken into small beats — every climax beat
  marked [USES VIDEO:] (2-3 scenes minimum, more if the climax naturally
  breaks into more beats)
- Open loop resolution
- Modern bridge (Type A/B/C)
- Emotional peak
 
PART 6 (Takeaways + Close, ~2 min, ~7-9 scenes):
- Three takeaways — 2-3 dedicated scenes each, using `IMAGE:`
- Closing comment question
- Closing line
 
(Scene counts above assume the 25-min default; for 20/30 min, scale
proportionally per the SCENE DENSITY RULE table. Mid-roll break count scales
the same way: 20 min = 3 points, 30 min = 4.)
```
 
After the outline, check these 8 items:
1. Total `[USES VIDEO:]` scenes meets or exceeds the length-based floor in
   "Field VIDEO:" (no ceiling), including the opening scene, with the
   densest concentration in PART 1 through the start of PART 2.
2. TOTAL scene count meets the SCENE DENSITY RULE minimum for the chosen length. If short, break more beats into smaller pieces before user approval — never draft from a sparse outline.
3. All 3 anti-drop-off hooks (Rule 8b) placed: minute 2-3, ~35-45%, right after each CTA.
4. Opening scene has all 3 hook layers (Rule 1): image, dangling question/tension, promise echoing the title.
5. Sponsor anchor (`***SPONSOR_BREAK***`, Rule 18d) sits in PART 4 (~35-45%), tied to a specific difficulty/setback — not standing alone.
6. Early engagement question (Rule 19b) sits in the 35-45% dead zone, tied to a specific situation, with a teaser line — not relying only on the closing question (Rule 19).
7. Total mid-roll break points (`***MIDROLL_BREAK***`, Rule 18e) matches the fixed lookup for the chosen length (20 min → 3, 25 min → 3, 30 min → 4), well spaced per Rule 18f, not overlapping CTAs or the sponsor anchor.
Stop and wait for user approval.
 
## PHASE 4: DRAFT (6 SEQUENTIAL PARTS)
 
Write each part separately; stop for confirmation before continuing.
 
Track open loops/pattern resets internally, but NEVER place `[OPEN LOOP PLANTED]` in the prose — clean prose only, with an optional tracking section at the end of each part:
 
```
═══ DRAFT PART [N] of 6 ═══
 
[CLEAN PROSE — no brackets, no markers, broken into multiple [SCENE] blocks
per the SCENE DENSITY RULE — each scene at most ~40-50 words of narration]
 
═══ INTERNAL TRACKING (reference only, not part of the final output) ═══
- Word count: [X]
- Scene count in this part: [X] — average words/scene: [X] (if > 50, split
  the long scene before presenting for user approval)
- Pattern resets used: [list]
- Open loop status: [Planted at "..." / Still open / Resolved at "..."]
- Emotional beat: [Awe/Tension/Grief/Hope/Reflection]
- Triple negative: [Yes/No]
- Scientific terms used: [If any]
```
 
This tracking section is deleted in Phase 6.
 
Stop for approval after each part. Once PART 1 AND PART 2 (all of Act 1) are approved, stop and run PHASE 4.5 (thumbnail) before writing PART 3. From PART 3 onward, write sequentially — no more thumbnail pauses.
 
## PHASE 4.5: THUMBNAIL CONCEPT DESIGN (after PART 1 + PART 2 of Phase 4)
 
Uses the ACTUAL written text of Act 1 (not an abstract outline description) to pick the strongest moment/image, so the thumbnail never "promises" something not really in the video.
 
Re-read approved PART 1 + PART 2, pick 1-3 of the strongest visual moments (favor the cold-open scene if strong enough, but another Act 1 moment can win if more powerful), then generate 3 thumbnail concepts. The thumbnail MUST match a moment that actually appears in the written Act 1 — never invent one, since that creates a clickbait letdown and hurts retention from second one.
 
**Output format:**
```
═══ PHASE 4.5: THUMBNAIL CONCEPTS (based on the written Act 1) ═══
 
CONCEPT 1 — [Short name]:
- Moment taken from: [specify exact location in PART 1 or PART 2]
- Composition: [frame description, position of main character/object,
  camera angle]
- Character expression/action: [use the exact CORE PROMPT + locked
  variables from Phase 1 (outfit, prop, Act 1 palette), strong emotion —
  fear/awe/determination]
- Text overlay (if any): [3-5 words, ALL CAPS, curiosity-driving, no
  spoilers]
- Why it matches the script: [direct link to the specific scene/moment just
  written in Act 1]
 
CONCEPT 2 — ...
CONCEPT 3 — ...
 
RECOMMENDATION: [Which concept is strongest and why]
```
 
Stop and wait for user approval, then continue writing PART 3.
 
## PHASE 5: HUMANIZATION (REWRITE FOR NATURALNESS)
 
Once all 6 parts are drafted:
- Read every sentence silently; cut robotic/generic ones
- Replace banned vocabulary (Tiers 1-4)
- Vary sentence rhythm; reinforce emotional pacing
- Confirm no pattern reset repeats
- Confirm the open loop is planted + resolved
- Confirm "you" ≤ 20 uses, each landing in the right spot (Rule 2)
- Check for 5+ specific names
```
═══ PHASE 5: HUMANIZATION COMPLETE ═══
 
Changes made:
- [Details of edits]
 
Quality check:
□ Banned vocabulary fully filtered out? [Yes/No]
□ "You" used no more than 20 times, in the right spots? [count]
□ 5+ specific names? [list them]
□ Pattern-reset phrases all distinct? [count]
□ Triple negative used x2? [Yes/No]
□ Scientific terminology used? [Yes/No]
□ Archaeological/research sources cited? [Yes/No]
□ Open loop planted + resolved? [Yes/No]
□ Emotional beats varied? [list]
□ Sentence rhythm varied? [Yes/No]
□ TOTAL scene count meets the minimum in the length lookup table (SCENE
  DENSITY RULE)? [count] — if not, split more scenes before Phase 6
□ `VIDEO:` scene count meets the length-based floor with no ceiling (Field
  VIDEO:), and the densest concentration sits in the first few minutes?
  [count, Yes/No]
□ EVERY scene marked `VIDEO:` has a narration word count between 18-22 words
  (~8s target at `config.SCENE_VIDEO_DURATION`)? [Yes/No] — strictly trim any
  `VIDEO:` narration over 22 words now; running long just means a longer held
  freeze-frame on that clip's last frame once composed (see "Field VIDEO:",
  point 2), never a hard error, but it looks worse than a clean match.
□ Opening hook has all 3 layers (image/dangling question/promise)?
  [Yes/No]
□ All 3 anti-drop-off hooks (minute 2-3, the 35-45% zone, after each CTA)
  present and strong enough? [Yes/No, note each position]
□ CTAs woven naturally into the emotional beat, not standing alone
  dryly? [Yes/No]
□ Early engagement question (Rule 19b) present in the 35-45% dead zone,
  tied to a specific situation + teaser line right after? [Yes/No]
□ Sponsor anchor (Rule 18d) has a natural segue, tied to a specific
  difficulty/setback in the content, marker `***SPONSOR_BREAK***` placed
  correctly? [Yes/No]
□ Mid-roll break points (Rule 18e) match the fixed lookup for the chosen
  length (20 min → 3, 25 min → 3, 30 min → 4), well spaced per Rule 18f,
  exactly at each story beat's peak tension, marker `***MIDROLL_BREAK***`,
  not overlapping the CTA/sponsor zones? [Yes/No, note positions]
□ Hunting/survival/death language is brand-safe (Rule 21), no remaining
  graphic blood/organ/extreme-violence detail? [Yes/No]
```
 
Stop and wait for user approval.
 
## PHASE 6: FINAL CLEAN PASS ⭐ MOST IMPORTANT
 
1. **DELETE every square bracket:** all markers, including `[USES VIDEO:]`/`[USES IMAGE:]` from Phase 3 outlining — these must never leak into the final script. EXCEPTION: keep `***SPONSOR_BREAK***`/`***MIDROLL_BREAK***` exactly as they are (not square brackets, must remain).
2. **Replace pause-brackets with punctuation:** delete `[PAUSE]`; add an ellipsis only if genuinely needed, otherwise just delete.
3. **Delete internal tracking sections:** any `═══ INTERNAL TRACKING ═══` block → gone entirely.
4. **Brand-safe check (Rule 21):** re-read hunting/combat/survival/death passages for graphic blood/organ/violence detail; rewrite toward suggestive/implied language if found.
5. **Spelling/grammar pass (mandatory):** fix every spelling, typo, and grammar error in American English — cannot be skipped.
6. **Verify clean output:** re-read the opening; must flow as pure prose.
7. **Output format:**
```
═══ PHASE 6: FINAL VOICEOVER SCRIPT ═══
 
TITLE: [Title]
WORD COUNT: [X]
ESTIMATED RUNTIME: [X minutes at 150 words/minute]
 
[CLEAN PROSE STARTS HERE — 100% no brackets]
 
[... the complete clean script ...]
```
 
After the full clean script, end with EXACTLY:
 
```
✅ SCRIPT COMPLETED. ALL SEVEN PHASES FINISHED. READY FOR RECORDING.
 
📊 SCRIPT STATS:
- Word count: [X]
- Runtime: [X minutes]
- Named characters/species/fossils: [count]
- Pattern resets: [count]
- "You" usage count: [count] (target: max 20)
- Triple negatives: [count]
- Open loop: planted at "...", resolved at "..."
- Modern bridge: [Type A/B/C]
- Archaeological/research sources: [source]
- Mid-roll break points: [count, positions — target per length: 20 min = 3, 25 min = 3, 30 min = 4]
```
 
## PHASE 7: EXPORT & SAVE FILES ⭐ (SCRIPT + IMAGE PROMPT LIST + VIDEO PROMPT LIST + MUSIC PROMPT)

*(Continue to PHASE 8 after this phase — Phase 7 is no longer the final phase.)*
 
After Phase 6, output EXACTLY 4 files, all as **Markdown (`.md`)** — structured so each file is easy for a human to scroll/skim in any Markdown viewer (GitHub, Obsidian, VS Code) AND easy for an AI or script to parse without ambiguity. In Files 1-3, the machine-readable field tokens (`[SCENE]`, `NARRATION:`, `MOTION:`, `IMAGE:`, `VIDEO:`) are written byte-for-byte exactly as the pipeline expects — the Markdown (`##` headings, `---` dividers, bold labels) is purely additive framing around them, never a replacement for them. `modules/script_parser.py` only scans for these field keywords and ignores everything else at scene boundaries, so this framing does not break parsing. File 4 (the music prompt) is a generation prompt for an external music tool, not a pipeline input — it has no `[SCENE]`/`NARRATION:` fields and carries none of this parser-compatibility constraint.
 
⚠️ **CRITICAL RULE FOR THIS PHASE:** in Files 1-3, every `IMAGE:`/`VIDEO:` prompt MUST have its Phase-1-locked variables — `[SIGNATURE OUTFIT]`, `[SIGNATURE PROP]`, `[MAIN COLOR PALETTE — CURRENT ACT]` — fully resolved to the actual locked values chosen back in Phase 1, act by act. No raw bracketed placeholder text may remain anywhere in File 1, File 2, or File 3. Before presenting the files, scan each prompt for a literal `[SIGNATURE` or `[MAIN COLOR PALETTE` substring — if found, that prompt was not resolved and must be fixed before export completes. (`[SPONSOR NAME]` is the sole allowed exception, per Rule 18d, only when no sponsor has been given yet.)
 
1. **File-creation tool available** (Code Execution/Claude Code/Cowork): create all four files directly (filenames in items 2-5 below, no separate folder needed). **No file tool** (plain text chat): output each file in its own Markdown code block, with the filename on the first line (e.g. `--- [TITLE]-en.md ---`), for the user to copy.
2. **File 1 — the script:** `[TITLE]-en.md`. Structure:
   ```markdown
   # [TITLE]
 
   | Word Count | Runtime | Tone |
   |---|---|---|
   | [X] | [X] min | [intimate-storytelling] |
 
   ---
 
   ## Scene 001
 
   [SCENE]
   NARRATION: <clean American-English prose, no brackets>
   MOTION: <optional, plain-language motion feeling>
   VIDEO: <CORE PROMPT tag + scene-specific action matched to NARRATION, if this is a VIDEO: scene>
   IMAGE: <CORE PROMPT tag + scene-specific setting/action matched to NARRATION, if this is an IMAGE: scene — never both VIDEO: and IMAGE: on the same scene>
 
   ---
 
   ## Scene 002
 
   [SCENE]
   NARRATION: ...
   IMAGE: ...
 
   ---
   ```
   - Repeat the `## Scene <NNN>` heading + `---` divider pattern for every scene, in final script order, numbered with the same 3-digit index the pipeline uses (`scene_001`, `scene_002`...).
   - `NARRATION:` in clear American English, spelling/grammar-checked in Phase 6, no encoding errors.
   - `IMAGE:`/`VIDEO:` prompts already in English, each scene using only one of the two fields.
   - `MOTION:` lines included only on scenes that actually use them — don't pad every scene with empty fields.
   - `***SPONSOR_BREAK***`/`***MIDROLL_BREAK***` (if present) sit on their own line immediately inside the relevant scene block, exactly as written — never turned into a heading.
   - UTF-8 (no BOM). No stray brackets other than the `***SPONSOR_BREAK***`/`***MIDROLL_BREAK***` exception. Standard Markdown (`#`, `##`, `---`, `|table|`) is expected and encouraged — it is not "stray markdown."
3. **File 2 — the image prompt list:** `[TITLE]-image-prompts.md`. A numbered, Act-grouped Markdown list of every scene's `IMAGE:` prompt ONLY (no `VIDEO:` entries at all), in the SAME ORDER as the final script, so the user can work top-to-bottom in a stills tool (Midjourney/DALL-E/etc.) without scanning the full script or wading through video prompts that don't apply. Structure:
   ```markdown
   # [TITLE] — Image Prompt List
 
   Total IMAGE scenes: [X]
 
   ## Part 1 — Cold Open
 
   * **Scene 002 `[IMAGE]`** — A simple, hand-drawn 2D cartoon-style comic panel...
 
   ## Part 2 — Act 1
 
   * **Scene 003 `[IMAGE]`** — ...
   ```
   - Group entries under `##` headings matching the Phase 3 PART/Act structure (Part 1, Part 2, Part 3, Part 4, Part 5, Part 6) so long lists stay navigable.
   - One unordered (`*`) list item per `IMAGE:` scene: `**Scene <NNN> `[IMAGE]`** — <the exact prompt text from that scene>` — the prompt text must be copied verbatim from File 1, never re-summarized or shortened. Use `*` bullets, not `1.`/`2.` numbered lists — a numbered list sitting next to a bolded `Scene 003`/`Scene 005` label reads as two competing numbering systems and invites mixing them up while batch-generating.
   - The 3-digit scene index must match File 1's scene order 1:1 — this is what makes the files easy to cross-reference. The bolded `Scene <NNN>` label is what ties back to File 1; there is no separate list-position number to track.
   - Include EVERY scene that has an `IMAGE:` line — never a `VIDEO:` line in this file.
   - No narration text, no `MOTION:` values, no extra commentary inside list items — prompts only, to keep the file fast to scan while batch-generating.
   - Same UTF-8 (no BOM) requirement as File 1.
4. **File 3 — the video prompt list:** `[TITLE]-video-prompts.md`. Same structure and rules as File 2, but for `VIDEO:` prompts ONLY (no `IMAGE:` entries at all) — for batch-generating in a motion tool (Runway/Kling/Luma/Veo/etc.). Structure:
   ```markdown
   # [TITLE] — Video Prompt List
 
   Total VIDEO scenes: [X]
 
   ## Part 1 — Cold Open
 
   * **Scene 001 `[VIDEO]`** — A simple, hand-drawn 2D cartoon-style comic panel...
 
   ## Part 2 — Act 1
 
   * **Scene 005 `[VIDEO]`** — ...
   ```
   - Same Act-grouped `##` headings, same unordered `*` `**Scene <NNN> `[VIDEO]`** — <prompt>` list format, same verbatim-copy-from-File-1 rule as File 2.
   - Include EVERY scene that has a `VIDEO:` line — never an `IMAGE:` line in this file.
   - Same UTF-8 (no BOM) requirement as File 1.
5a. **File 4 — the background music prompt:** `[TITLE]-music-prompt.md`. ONE text prompt, in English, for an AI music generator (targeting Gemini/Lyria-style music models), describing a **3-minute (180-second) instrumental** background track built to match THIS script — never a generic all-purpose prompt copy-pasted between videos. This is what the user pastes into their music generator to produce the single file that becomes `config.BACKGROUND_MUSIC_PATH` (see "Background music — no longer a scripted field" below): the pipeline plays this ONE track on loop under the entire runtime, so the prompt's #1 job is a **seamless loop** — if the loop point is audible (a drum hit restarting, a chord cutting off, a swell that never resolves), it will click/jump every ~3 minutes for the full 20-30 minute video.

   Derive the content of the prompt directly from what's already locked earlier in this same run — never invent a new mood from scratch:
   - **Genre/instrumentation:** infer from the Phase 1 `TONE:` and the actual story content (era, setting, emotional register) — e.g. intimate-storytelling + Stone Age survival → sparse, low string drones, soft mallet percussion, breath-like woodwind textures, no clear drum kit/backbeat (nothing that would read as anachronistic under a prehistoric science documentary).
   - **Mood arc across the 3 minutes:** since one 3-minute loop must sit under a 20-30 minute video with real emotional swings (Rule 13's 5 beats — Awe/Tension/Grief/Hope/Reflection), do not write a single static mood. Instead describe a gentle 3-part arc that stays LOW-CONTRAST enough to loop under any scene without fighting the narration or a specific beat: e.g. "opens sparse and low, swells gently to a fuller but still restrained middle third, tapers back down toward the ending so it can loop into itself smoothly." Avoid asking for a big cinematic climax, hard tempo change, or dramatic silence anywhere in the 3 minutes — those moments would land at a musically arbitrary point in the video (since the track loops independently of the script's actual beats) and could clash with whatever is happening on screen at that random alignment.
   - **Palette-to-instrumentation echo (optional but encouraged):** the three Act palettes locked in Phase 1 (cool/icy, vibrant fire, warm muted) can loosely inform instrumentation color (e.g. cooler palette → airier, more reverb-heavy tones; fire palette → a touch more low-end warmth) without literally trying to sync to act boundaries, since the music loops on its own 3-minute clock, independent of the Acts' actual timing.
   - **Tempo/key consistency for the loop:** explicitly instruct a single consistent tempo and key throughout (no tempo ramps, no key change) — the single biggest cause of an audible loop seam.
   - **No vocals, no lyrics, no sound effects** — instrumental only, since narration (TTS) and any embedded video audio (`config.VIDEO_ORIGINAL_AUDIO_VOLUME`) already occupy the foreground; this track sits underneath at `config.MUSIC_VOLUME` (low, background level).
   - **Explicit seamless-loop instruction as its own sentence** — don't bury it inside other description. State plainly that the final measure/bar must lead naturally back into the opening measure/bar (matching instrumentation, dynamics, and harmonic resolution at the seam) so it can repeat back-to-back with no audible click, pause, or jump.

   **Template:**
   ```markdown
   # [TITLE] — Background Music Prompt

   **Target tool:** Gemini (Lyria-class AI music model) or equivalent instrumental music generator
   **Duration:** 3 minutes (180 seconds), seamless loop
   **Usage:** Plays once, on repeat, under the entire video's runtime (`config.BACKGROUND_MUSIC_PATH`) — see modules/music_engine.py

   ---

   ## Prompt

   [A single flowing prompt, 4-8 sentences, English, covering: genre/instrumentation
   matched to the story's era/tone; the 3-part mood arc description; explicit
   single tempo + single key instruction; explicit "no vocals/lyrics/sound effects,
   instrumental only" instruction; explicit seamless-loop instruction as its own
   sentence, describing how the ending must lead back into the beginning.]

   ---

   **Reference notes (not part of the prompt itself, for the user's context):**
   - Genre basis: [1 short line — why this genre/instrumentation fits this specific script]
   - Mood arc basis: [1 short line — which emotional beats from the script this loosely echoes]
   - Loop length: 3:00 (180s) — trim or regenerate if the tool outputs a different length
   ```

   - Same UTF-8 (no BOM) requirement as the other files.
   - This file is NOT scanned for `[SIGNATURE OUTFIT]`/`[MAIN COLOR PALETTE]` placeholders (the critical rule above applies to Files 1-3 only) since it contains no character/visual prompts, but it should still contain zero literal unresolved brackets in its own right — write the actual genre/mood/instrumentation content, never a bracketed placeholder standing in for it.
6. Before exporting, cross-check the "Field VIDEO:" checklist (opening scene has `VIDEO:`, total `VIDEO:` scene count meets the length-based floor with no ceiling and the heaviest concentration in the first few minutes, correctly placed at climax points, narration timed to ~8 seconds), AND confirm File 2's item count + File 3's item count together equal File 1's total scene count exactly (every scene is an `IMAGE:` scene or a `VIDEO:` scene, never both, never neither), each in matching order and matching scene numbers relative to File 1.
7. Confirm with the user: the file paths (real files) or code-block locations (text export) for ALL FOUR `.md` files are ready.

Then continue immediately to PHASE 8 (do not stop for approval here — Phase 8 is a metadata/upload-prep step, not a pipeline-facing file, so it does not need the same scene-integrity review as Files 1-4).

## PHASE 8: TITLE/THUMBNAIL A/B/C + SEO METADATA & DESCRIPTION FILE ⭐ (UPLOAD PREP)

A 5th exported file (File 5), separate from the pipeline files in Phase 7 (Files 1-3) and the music prompt (File 4). It never contains `[SCENE]`/`NARRATION:`/`IMAGE:`/`VIDEO:` fields — `modules/script_parser.py` never reads this file, so none of Phase 7's parser-compatibility rules apply here. Its job is to prep everything the user needs to actually upload and list the video on YouTube: three distinct Title+Thumbnail concept pairs for A/B testing, plus the full YouTube description/tags/hashtags built from the channel's fixed CHANNEL CONSTANTS template (see above), with only the video-specific parts written fresh.

**1. Title + Thumbnail A/B/C (for YouTube's Test & Compare feature):**

Generate exactly 3 pairs, each a genuinely different ANGLE on the same video (not 3 minor rewordings of one angle) — reuse the strongest real moments already identified in Phase 4.5, but each pair should foreground a different hook:
- **Concept A — Shock/sensational angle:** leads with the most visceral, high-stakes fact or image from the script.
- **Concept B — Philosophical/reflective angle:** leads with the human-condition question the script raises (identity, mortality, what makes us "us").
- **Concept C — Curiosity/mystery angle:** leads with an open question or unresolved tension, withholding the answer.

For each: a title (same viral-title conventions as Phase 1) + a thumbnail description detailed enough to actually design (composition, the CORE PROMPT's locked outfit/prop/palette, expression, text overlay if any — same standard as Phase 4.5 concepts). All 3 must be traceable to real moments in the written script — never invented, same rule as Phase 4.5.

**2. Metadata & full YouTube description (uses the CHANNEL CONSTANTS block):**

- **Word Count / Runtime / Tone:** pull directly from the Phase 6 output header (`WORD COUNT:`, `ESTIMATED RUNTIME:`) and the Phase 1 locked `TONE:` — do not recompute or re-estimate these.
- **Description:** start from the fixed **Description template** in CHANNEL CONSTANTS and fill in ONLY its bracketed parts — never rewrite, reorder, or drop the fixed lines (the "If it were you, would you fight or run?" line, the visual-style block, the subscribe CTA all stay byte-for-byte identical across every video):
  - `[2 lines summarizing this video...]` — write fresh per video: 2 lines, naturally working in 1-2 of the channel's core keywords (from CHANNEL CONSTANTS) plus this video's own specific keywords (species names, era, the core question) — natural-sounding, not keyword-stuffed.
  - `[Filled in per video]` under Timestamps — one line per PART (Part 1 through Part 6, after the fixed `00:00 - The Hook` line), each with a short keyword-bearing chapter title and an estimated `MM:SS` mark (see timestamp derivation below).
  - The hashtag line (`#HumanEvolution #Anthropology #HistoryExplained #NXH`) is fixed in the template as shown — do not add topical hashtags into this exact line; topical hashtags are a separate, additional line placed directly after it (see below).
  - `[Link Subscribe]` stays as a literal placeholder for the user to fill in — never invent a URL.
- **Additional topical hashtag line:** immediately after the template's fixed hashtag line, add ONE more line with 1-2 topical hashtags picked from CHANNEL CONSTANTS' "Hashtag system" that actually match this script's content (e.g. a Neanderthal-extinction video → `#Neanderthals #Prehistoric`) — never dump every topical hashtag, only the ones the script earns.
- **Tags:** start from CHANNEL CONSTANTS' **Default video tags** verbatim, then append 3-5 niche tags specific to this video's actual content (specific species/site/person names used in the script) — comma-separated, matching the format already shown in Default video tags.
- **Timestamps:** one entry per PART (Part 1 through Part 6, matching the Phase 3 outline structure), each with a short keyword-bearing chapter title (not just "Part 1") and an estimated `MM:SS` mark. Derive marks by walking the script in order and summing each scene's estimated reading time (`words in scene / config.WORDS_PER_SECOND`, i.e. `words × 0.4` seconds) plus a nominal ~1s per scene for the `SCENE_AUDIO_GAP` breathing room between scenes — a lightweight estimate for chapter markers, not the frame-accurate timing `subtitle_gen.py` produces from real TTS audio. Round to the nearest 5 seconds for readability. The first timestamp is always `00:00`.

**Output format:**
```
═══ PHASE 8: TITLE/THUMBNAIL A/B/C + SEO METADATA ═══

### 1. TITLE & THUMBNAIL CONCEPTS (A/B/C testing)

**Concept A — Shock/Sensational:**
- Title: [Title]
- Thumbnail: [composition, character action/expression using the locked CORE PROMPT variables, text overlay if any]
- Moment taken from: [specific location in the script]

**Concept B — Philosophical/Reflective:**
- Title: [Title]
- Thumbnail: [...]
- Moment taken from: [...]

**Concept C — Curiosity/Mystery:**
- Title: [Title]
- Thumbnail: [...]
- Moment taken from: [...]

### 2. METADATA & YOUTUBE DESCRIPTION

| Word Count | Runtime | Tone |
|---|---|---|
| [X] | [X] min | [tone from Phase 1] |

**Full Description (fixed channel template, video-specific parts filled in):**

[2 lines summarizing this video, containing its main keyword]

If it were you, would you fight or run? Dive deep into the mysteries of our past, where science, history, and anthropology meet cinematic storytelling.

🕰️ Timestamps:
00:00 - The Hook
[MM:SS] - [Part 2 chapter title with keyword]
[MM:SS] - [Part 3 chapter title with keyword]
[MM:SS] - [Part 4 chapter title with keyword]
[MM:SS] - [Part 5 chapter title with keyword]
[MM:SS] - [Part 6 chapter title with keyword]

#HumanEvolution #Anthropology #HistoryExplained #NXH
[1-2 topical hashtags matching this video's content]

---------------------------------------
A cinematic explainer directed by NxH.
Visual Style: Original 2D hand-drawn animation.
---------------------------------------
🔔 Don't forget to subscribe for more deep dives into the story of humanity: [Link Subscribe]

**Video Tags:**
human evolution, anthropology, history explained, science documentary, prehistoric survival, ancient history, NXH origins, [niche tag 1], [niche tag 2], [niche tag 3]
```

**3. Save the file:** `[TITLE]-seo-metadata.md`, using the same file-creation-tool-vs-code-block rule as Phase 7 item 1. Confirm the file path (or code block) is ready.

End every successful run with:
`✅ SCRIPT COMPLETED. ALL EIGHT PHASES FINISHED. READY FOR RECORDING.`

---


# 🎨 REQUIRED MAIN CHARACTER PROMPT (Modular)
 
Every scene MUST include a visual prompt built on the CORE PROMPT below — `IMAGE:` for static Ken Burns scenes, `VIDEO:` for the motion scenes, a count that scales with the script and is front-loaded toward the first few minutes (see "Field VIDEO:" — a `VIDEO:` scene uses no `IMAGE:` line). Both fields are recognized by `modules/script_parser.py` as scene boundaries — the parser only scans for these keywords and ignores surrounding text — so the exported `.md` file (see Phase 7) feeds straight into the pipeline without manual editing, Markdown headings and all. To keep visual identity consistent while staying compatible with any topic (not just Stone Age), the CORE PROMPT uses VISUAL VARIABLES locked in Phase 1 instead of a hard-coded outfit.
 
**As of V1.6, the CORE PROMPT is a short CONSISTENCY TAG, not a full boilerplate paragraph.** Midjourney/Runway/Kling have no memory of "the character" between separate calls, so every prompt still needs to open with *something* that anchors the look (style + outfit + prop + palette) or the character drifts scene to scene. But that anchor should now cost as little of the prompt as possible — the majority of every prompt goes toward the specific action, composition, and detail for THAT scene, matched closely to what `NARRATION:` says and what's actually happening in the story at that beat. Generic mood filler ("standing thoughtfully by the fire") is out; concrete, story-specific detail ("her hand closing around the burning branch, heat biting, smoke curling off her fingers") is in.
 
**In PHASE 1, lock these variables — 2 fixed for the whole script, 1 locked per Act:**
- `[SIGNATURE OUTFIT]` (fixed): brief outfit description (e.g. "a long, rough, textured, earth-colored burlap robe").
- `[SIGNATURE PROP]` (fixed): an item the character always carries (e.g. "a small brown leather pouch slung across his chest").
- `[MAIN COLOR PALETTE — CURRENT ACT]` (locked separately per Act, not shared): 3-4 mood colors per Act, e.g.:
  - ACT 1: "cool icy tones: pale blue, frost white, steel grey"
  - ACT 2: "vibrant fire tones: burnt orange, amber, deep red"
  - ACT 3: "warm muted tones: burnt sienna, dusty brown, soft gold"
  If Act 1 leans cold/neutral, consider one warm accent (e.g. distant firelight) so the opening `VIDEO:` scene and thumbnail still pop.
OUTFIT and PROP stay identical for the entire script. COLOR PALETTE changes only at act boundaries, never within an act. Expression is no longer a separate fixed slot — it's written as part of the scene-specific action (see below).
 
**CORE PROMPT (one short sentence, substituting the Phase-1-locked variables — use the correct act's palette):**
```
Simple hand-drawn 2D cartoon-style comic panel, stick figure man with solid
black line art, wearing [SIGNATURE OUTFIT] and carrying [SIGNATURE PROP].
Palette: [MAIN COLOR PALETTE — CURRENT ACT].
```
 
**Assembling each scene's prompt:**
1. Open with the CORE PROMPT tag above, substituting the locked variables — one sentence, not a paragraph. Outfit/prop/line-art style never change mid-script; palette changes only at locked act boundaries.
2. Spend the rest of the prompt — the majority of it — on what's actually happening in THIS scene: the specific action, expression, camera framing, and setting, pulled directly from that scene's `NARRATION:` and the story beat it belongs to. Write the expression as part of the action ("flinching as the heat bites, teeth gritted") rather than a bolted-on "expressing a [X] expression" clause.
3. Don't pad the prompt by restating the CORE PROMPT tag's wording a second time or describing generic mood — every extra word should be specific to what this scene shows that no other scene does.
4. This applies identically to `VIDEO:` prompts (see "Field VIDEO:") — still open with the CORE PROMPT tag (a video-generation tool making a *different-looking* character than the illustrated `IMAGE:` scenes is still the single most common way this pipeline's visual consistency breaks), then describe the specific motion/action in detail.
## Field VIDEO: — VIDEO PROMPTs for the opening scene + action/dramatic scenes
 
This skill proactively places `VIDEO:` from the scriptwriting stage, so the opening and action climaxes use real motion instead of static Ken Burns images.
 
**Count and placement — mandatory floor, no ceiling:**
 
1. **Scene 1 ALWAYS uses `VIDEO:`** — the first hook must be real motion (running, collision, fire flaring, an animal charging), never a static image.
2. **No maximum on `VIDEO:` scene count.** Give `VIDEO:` to every scene that is a genuine action/dramatic/emotional-peak moment (see the priority list in point 3 below), not a fixed quota — a script with more real climaxes simply gets more `VIDEO:` scenes. As a MINIMUM floor only (never a ceiling), scale with the chosen length: 20 min → at least 8-10 `VIDEO:` scenes; 25 min → at least 10-13; 30 min → at least 12-16. If the outline naturally produces more qualifying moments than the floor, give all of them `VIDEO:` too. Because `VIDEO:` narration runs shorter than `IMAGE:` narration (~20 words vs. 40-50), a heavily front-loaded part may need to sit toward the higher end of its SCENE DENSITY RULE scene-count range to still cover its target runtime.
3. `VIDEO:` scenes go at action/dramatic climaxes — priority: hunting, fleeing a predator, group conflict, breakthrough-invention moments (fire flaring, a tool struck sharp), natural disasters (eruption, flash flood, blizzard). Never on a static scene (setting description, inner reflection, terminology explanation).
4. **Front-load the heaviest concentration into the first few minutes.** PART 1 (the cold open) and the opening stretch of PART 2 — roughly the first 4-5 minutes — is the highest drop-off window (Rule 8b), where trust in the video is won or lost, so this stretch should carry the densest run of `VIDEO:` scenes in the whole script. Give `VIDEO:` to every genuine action/dramatic moment in this window rather than defaulting to `IMAGE:`. From there, keep giving `VIDEO:` to every real climax across the rest of ACT 2 and ACT 3 (escalating-stakes points, both mid-roll break peaks, the Act 3 climax) so the back half doesn't go quiet on motion either — but the opening minutes stay the single densest stretch in the script.
5. In Phase 3, mark every scene `[USES VIDEO:]` or `[USES IMAGE:]` up front to lock placement before drafting.
6. **The user generates each `VIDEO:` clip at a fixed length — default 8 seconds** (`config.SCENE_VIDEO_DURATION` in the pipeline, `.env`-configurable). Each clip plays exactly once: no loop, no stretch. A too-long narration gets a held last frame tacked on; a too-short narration gets the clip cut early. Neither breaks the pipeline, but both look worse than a narration sized to land at ~8 seconds — see "Other technical rules", point 2, for how to size it.
**`VIDEO:` field format (an AI video-generation prompt, not a pre-existing filename):**
 
```
[SCENE]
NARRATION: ...
VIDEO: <a prompt describing the main motion/action, detailed enough for a
video-generation tool (Runway/Kling/Luma/Veo...) to produce the intended
result>
```
 
⚠️ **MANDATORY: every `VIDEO:` prompt MUST open with the short CORE PROMPT consistency tag** (see "REQUIRED MAIN CHARACTER PROMPT" — style, outfit, prop, current-act palette, one sentence), THEN spend the rest of the prompt on the specific motion/action for that scene, pulled from `NARRATION:` and the story beat. Never write a `VIDEO:` prompt as a bare live-action/photorealistic shot description with no tag at all — that breaks visual consistency with every `IMAGE:` scene when cut together. But don't swing the other way either and pad it out with a full boilerplate paragraph — the tag stays short; the detail budget goes to the actual moment.
 
❌ "A weathered human hand grips a flint sickle blade, cutting through golden wild wheat stalks in an endless field at sunrise. Wide shot, warm straw-yellow light sweeping across the grain, cinematic, raw, Neolithic setting." (no consistency tag at all — photorealistic style, will look like a different show)
 
❌ "A simple, hand-drawn 2D cartoon-style comic panel. The main character is a stick figure man with a round head, slender limbs, and a slightly thicker torso, drawn with solid black lines. He wears [SIGNATURE OUTFIT] and carries [SIGNATURE PROP]. He has simple dot eyes and a curved mouth, expressing a focused, determined expression. The dominant color palette consists of [MAIN COLOR PALETTE — CURRENT ACT]. He grips a flint sickle blade..." (has a tag, but burns most of the prompt restating fixed boilerplate instead of describing the actual moment)
 
✅ "Simple hand-drawn 2D cartoon-style comic panel, stick figure man wearing [SIGNATURE OUTFIT], carrying [SIGNATURE PROP]. Palette: [MAIN COLOR PALETTE — CURRENT ACT]. He grips a flint sickle blade with both hands, jaw tight with effort, sweeping it low through golden wild wheat stalks in an endless field at sunrise — wide shot, warm straw-yellow light raking across the grain, stalks falling in his wake."
 
**Other technical rules:**
 
1. A scene uses ONLY `IMAGE:` OR `VIDEO:`, never both.
2. **Narration in a `VIDEO:` scene must read in exactly ~8 seconds** (~20 words), matching the user's fixed video-generation length (`config.SCENE_VIDEO_DURATION`, default 8.0s — see "Field VIDEO:", point 6). The clip is NOT looped to fill extra time and NOT stretched — it plays once, start to end. If the narration runs longer than the clip, the pipeline simply holds on the clip's last frame (a still moment) until the narration finishes; if the narration runs shorter, the clip gets cut short. Both are silent fallbacks that work but look worse than a clean match, so recount and adjust every `VIDEO:` scene's narration in Phase 4 to land as close to 8 seconds as possible — treat 20 words as the target, not a ceiling to stay under.
3. A `VIDEO:` scene needs no `IMAGE:` line.
4. Any embedded original audio is handled by the pipeline (`config.VIDEO_ORIGINAL_AUDIO_VOLUME`) — the voiceover is always the TTS narration; the scriptwriter doesn't need to worry about it.
5. Narration length must track whatever `config.SCENE_VIDEO_DURATION` is actually set to in the user's `config.py` (or `.env`), not always 8 seconds — if the user says they generate clips at a different fixed length (e.g. 5s or 10s), ask them for that number and use ~2.5 words/second to size the narration instead of the 8s/20-word default below.
**Checklist before Phase 6:**
- [ ] Scene 1 has `VIDEO:`
- [ ] Total `VIDEO:` scene count meets or exceeds the length-based floor (no ceiling), with the densest run in PART 1 through the start of PART 2
- [ ] All `VIDEO:` scenes besides Scene 1 sit at action/dramatic climaxes
- [ ] Every `VIDEO:` scene's narration reads in ~8 seconds (~20 words, or matching `config.SCENE_VIDEO_DURATION` if the user specified a different fixed clip length)
- [ ] No scene has both `IMAGE:` and `VIDEO:`
- [ ] EVERY `VIDEO:` prompt opens with the short CORE PROMPT consistency tag (same as `IMAGE:` scenes) — no bare/photorealistic prompt without it, and no full restated boilerplate paragraph either
## Background music — no longer a scripted field, now a generated-prompt file

> [Updated] The `MUSIC:` field and the Freesound sourcing workflow have been **removed**. Background music is no longer chosen per segment or written into the script at all — the pipeline now plays ONE fixed music file (`config.BACKGROUND_MUSIC_PATH`, picked/supplied by the user directly, not sourced by Claude) continuously under the whole video, looping or trimming to fit total runtime, mixed at `config.MUSIC_VOLUME`. See `modules/music_engine.py`.
>
> Do not write `MUSIC:` lines in any exported script. Do not query the Freesound API for this skill. If an older script (from before this change) still has `MUSIC:` lines, strip them out before handing the script to the pipeline — the current `script_parser.py` no longer recognizes `MUSIC:` as a field boundary, so a leftover `MUSIC:` line would otherwise get swallowed into `NARRATION:` and be read aloud by TTS.
>
> [Added V1.10] Since the user still has to supply that one `BACKGROUND_MUSIC_PATH` file from somewhere, Phase 7 now generates **File 4**, `[TITLE]-music-prompt.md` — a ready-to-paste prompt for an AI music generator (Gemini/Lyria-class) describing a 3-minute instrumental track matched to this specific script's genre and mood, written for a seamless loop. See "PHASE 7, item 5a" for the full spec and template. This is the recommended way to produce the `BACKGROUND_MUSIC_PATH` file for a new video; it does not change anything about how `music_engine.py`/`video_compose.py` consume the resulting audio file once the user has generated and placed it.

---
 
Scripts from this skill feed the video-assembly pipeline (`modules/video_compose.py` + `modules/effect_selector.py`), which supports **21 virtual camera effects (Ken Burns: pan/zoom on a static image)** — every effect below is supported. These 21 effects ONLY apply to `IMAGE:` scenes; `VIDEO:` scenes keep their real embedded motion, with no Ken Burns on top:
 
**7 basic:** `zoom_in`, `zoom_out`, `pan_left`, `pan_right`, `pan_up`, `pan_down`, `static`
 
**8 combined zoom + diagonal-pan** (good for climax/storytelling scenes):
`zoom_in_pan_left`, `zoom_in_pan_right`, `zoom_in_pan_up`, `zoom_in_pan_down`, `zoom_out_pan_left`, `zoom_out_pan_right`, `zoom_out_pan_up`, `zoom_out_pan_down`
 
**4 corner-to-corner diagonal pan** (good for wide establishing shots — tundra, caves, simulated drone shots):
`pan_diagonal_tl_br`, `pan_diagonal_tr_bl`, `pan_diagonal_bl_tr`, `pan_diagonal_br_tl`
 
**2 "breathe" effects** (zoom in then out or vice versa within one scene — good for a lingering emotional moment):
`zoom_in_out`, `zoom_out_in`
 
## How the script and effects work together
 
- You MAY add a `MOTION:` line suggesting the desired feeling of motion in plain language (e.g. `MOTION: a sense of being overwhelmed by the vast tundra`) — a content suggestion, not a technical effect name.
- **The AI makes the final call.** When `config.EFFECT_SELECTION_MODE = "ai"`, `effect_selector.py` sends the narration + `MOTION:` suggestion to the AI, which picks one of the 21 effects, avoiding a repeat of the immediately preceding scene's effect.
- `EFFECT_SELECTION_MODE = "heuristic"` (default, free): picks by simple keyword match, cycling through a broad rotation (including combined effects) when nothing matches.
- The scriptwriter doesn't need the 21 effects' technical names — just describe the desired FEELING; the AI maps it.
**Reference guide (not a strict rule):**
- Vast Ice Age landscape/tundra → "sweeping"/"establishing"/"drone-like" (usually `zoom_out`) or "diagonal sweep" (`pan_diagonal_*`)
- Emotional climax, close-up on a face → "emphasize the emotion", "gradually closing in" (`zoom_in`/`zoom_in_pan_*`)
- Real motion (walking, running, hunting) → "horizontal movement", "chasing" (`pan_left`/`pan_right`/combined)
- Height (cliff, tall cave, ancient tree) → "rising up", "looking up from below" (`pan_up`/`pan_down`)
- Lingering emotional moment (discovering fire, losing a loved one) → "a held breath" (`zoom_in_out`/`zoom_out_in`)
- Text/data-heavy scene (timeline, migration map) → "hold steady", "let the viewer read it" (`static`)
---
 
# 🚨 ERRORS TO AVOID (US Edition V1.2)
 
1. **LEAKED SQUARE BRACKETS** — any `[...]` in final output = ERROR. (Exception: `***SPONSOR_BREAK***`/`***MIDROLL_BREAK***`, Rule 18d/18e.)
2. **STANDALONE MARKER WORDS** — "PLANTED"/"RESOLVED" alone in prose = ERROR.
3. **PRODUCTION NOTES** — e.g. "(narrator pauses here)" = ERROR.
4. **SKIPPING PHASE 6/7/8** — never output/save a final script without the Clean Pass, Export, or the SEO Metadata file.
5. **NUMBERS UNREADABLE FOR TTS** — "33,000" instead of "thirty-three thousand" = ERROR.
6. **TECHNICAL EFFECT NAMES IN NARRATION** — `MOTION:` only describes the feeling; never write a raw effect name like `zoom_in_pan_left` (that's effect_selector.py's job).
7. **WEAK OPENING HOOK** — missing the dangling question or promise (Rule 1) loses viewers by second 15.
8. **DETACHED CTA** — a dry announcement not woven into the emotional flow (Rule 18b).
9. **EMPTY ACT 2 "DEAD ZONE"** — the ~35-45% segment with no pattern reset/new dangling question = worst retention drop (Rule 8b).
10. **MISSING MID-ROLL BREAKS** — fewer than 3 `***MIDROLL_BREAK***` markers in a 25-30 min script wastes RPM (Rule 18e).
11. **TOO GRAPHIC VIOLENCE/GORE** — lingering wound/blood/organ detail = demonetization risk (Rule 21).
---
 
# 🙏 FINAL NOTE
 
The script you output IS the script the narrator reads. No intermediate step, no manual cleanup.
 
Every square bracket left in = one manual fix for the user. Every clean sentence = time saved, fewer recording mistakes.
 
When in doubt: DELETE the bracket. Trust the punctuation. Trust the prose.
 
**ALWAYS OUTPUT THE FINAL SCRIPT IN CLEAN AMERICAN ENGLISH, WITH NO SQUARE BRACKETS.**