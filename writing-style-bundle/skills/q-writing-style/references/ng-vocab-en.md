# English (en): words to drop or replace, and the self-check

Read for any English text you write, edit or translate into (with `style-guide.md` § 3). The groups below follow the same frame as `ng-vocab-ja.md` and `ng-vocab-vi.md`; the examples are written for this skill.

## How to use

- No mechanical find-and-replace: read each hit in context; if the English word adds nothing, delete it or state the concrete fact (condition, number, name); keep it when it is the precise term.
- **Only facts the source has**: "replace with a number / condition / actor / mechanism" means one the source gives. If the source has none, keep the general wording (or cut a pure filler word) and flag "needs a figure" at the end; keep the passive when the actor is unknown.
- **Glossary over this list**: a term defined in the project glossary (`glossary` key of the config) is kept as defined, even when a group below lists a similar word.
- "Must", "shall" and "must not" stay in specifications, designs and procedures; drop them only when they are emphasis.
- In doubt → leave the word and flag the location to the requester.
- Start with groups 1, 2 and 6: in English technical text they most often hide the actor or the conclusion.

## Word groups

| # | Group | Examples | Replace with |
|---|---|---|---|
| 1 | Empty lead-in | "It is worth noting that", "Needless to say", "To be honest", "At the end of the day", "It goes without saying", "Importantly,", "In today's fast-moving world", "First and foremost" | Delete the lead-in; write the statement itself |
| 2 | Verbs that hide the actor | "is leveraged by", "serves as", "plays a pivotal role in", "sheds light on", "speaks to", "underscores the importance of", "paints a picture of", "is utilized to" | Name who did what, active voice: "The test team ran 48 cases", "The measurements show the error appears above 200 requests per second" |
| 3 | Inflated words | "game-changing", "revolutionary", "seamless", "robust", "cutting-edge", "unparalleled", "transformative", "best-in-class" | State the fact: what changed, by how much, compared with what |
| 4 | IT words used as metaphors for people and habits | "upgrade your mindset", "rewire the team", "debug the meeting", "reboot the plan", "install a habit", "hack your productivity" | The literal action ("change the review order", "write notes after every meeting"); IT words only for the IT thing |
| 5 | Unneeded business jargon | "synergy", "leverage" (as a verb), "circle back", "touch base", "deep dive", "move the needle", "low-hanging fruit", "operationalize", "ideate" | The plain word ("combined effect", "use", "return to", "contact", "close look", "ship") — **unless the project glossary fixes the term**; established technical words (API, pipeline, benchmark) stay |
| 6 | Avoiding a conclusion | "it depends", "there are pros and cons", "no one-size-fits-all", "time will tell", "many factors are at play", "results may vary" | Which condition gives which result; if it is truly uncertain, say where the uncertainty is and why |
| 7 | Intensity adverbs | "very", "extremely", "highly", "really", "significantly", "drastically", "vastly" (overused) | A number or a condition: "from 2.1 s to 0.4 s", "after three reruns" |
| 8 | Connecting or summarising sentences that add nothing | "In conclusion," straight after one paragraph, "As mentioned above", "In other words," plus a repeat, "Let's dive in", "Here is an overview of what follows", "Overall, this shows that" | Delete; keep the sentence that holds the new fact |

## Plain swaps

Use in Plain mode and for procedures, error messages and prompts (`plain-language.md`). Selected and adapted from `references/word-swaps.md` of the skill `SimpleEnglish` (MIT; notice in `NOTICES.md` of the skill). If the word carries no fact, delete it instead of swapping.

| Instead of | Write |
|---|---|
| leverage, utilize, harness | use |
| in order to | to |
| prior to | before |
| ensure, verify, validate (as verbs, same meaning) | make sure that — keep the word when it names a different operation |
| it is worth noting that, it's important to | (delete, then state the fact) |
| simply, just, easily, seamlessly, effortlessly | (delete) |
| robust, powerful, comprehensive, performant | (delete, or give the measured property) |
| functionality | function, feature |
| enables you to, allows you to | you can |
| is designed to, aims to | (say what it does) |
| facilitate | help, make possible |
| when it comes to | for |
| in the event that | if |
| due to the fact that | because |
| as needed, as necessary | (state the condition if the source gives it; otherwise keep) |
| and/or | "X, or Y, or both" |
| e.g. / i.e. / etc. | for example / that is / (name the items only if the source lists them all; otherwise "and others") |
| gracefully handles | (say what it does: "retries three times, then stops") |
| out of the box | by default |
| under the hood | internally |
| streamline | make simpler, make faster |
| plethora, myriad | many |
| intricate | complex |
| showcase, underscore, emphasize | show |
| foster, empower, bolster | help, support |
| enhance / elevate | improve / increase |
| furthermore, moreover | also |
| embark on, endeavor | start, try |
| that being said, notwithstanding | but |

## English self-check (before handing over)

Read the whole text once, list the problems, then fix. Register for English: `style-guide.md` § 3.

1. **Rigour** (`style-guide.md` § 0 item 1) — hedge only where the uncertainty is real; never claim without a source; keep distinct things distinct; do not let one cause stand for several; explain how each cause produces its effect.
2. **Actor** — active voice with the actor as subject; role names, not "you"; no vague "the system", "the tool", "AI" where a name exists.
3. **Terms** — one English word per concept from start to end; no elegant variation; the glossary term first.
4. **Paragraphs** — a topic sentence opens each paragraph; one topic per paragraph; the argument moves forward; the conclusion appears once; common misreadings are ruled out before the explanation.
5. **No dramatisation** — no questions asked for effect, no suspense, no punchline ending; bold only for the conclusion or a likely misreading.
6. **Words** — no word from the groups above that carries no information; no filler used only for tone ("crucial", "key", "deep", "optimal" without a measure).
7. **No redundancy** — each point said once, no recap after a description, related facts combined, no sentence that only links or comments.
8. **Format** — register fits the document type (specification and slides: short noun-style lines; reports: full sentences); code, logs and commands in code blocks.

Not taken as rules: a fixed sentence length, no proper names (project documents need module, file and ID names), or a numeric score.
