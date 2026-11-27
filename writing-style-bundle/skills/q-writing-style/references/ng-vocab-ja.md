# Japanese (ja): words to drop or replace, and the self-check

Read for any Japanese text you write, edit or translate into (with `style-guide.md` § 2). Adapted for project documents from `reference/ng-vocab.md` and `reference/checklist.md` of the skill `japanese-tech-writing` (MIT; its word list is itself adapted from `stop-ai-slop-jp`, MIT) — notices at the end.

## How to use

- Never delete by search-and-replace. For each hit, ask: **does the word carry information here?** If not, cut it or replace it with the concrete fact (condition, number, name). If it is used as a precise technical term, keep it.
- **Facts only from the source**: the number, condition, actor or mechanism used as a replacement must appear in the source. If it does not, keep the general expression (or drop pure filler) and note 「要確認」 at the end; keep a passive sentence when the actor is not stated.
- **The project glossary wins**: katakana terms fixed in the project glossary (the `glossary` key of the config) stay as they are, even if a group below lists them.
- 「必ず」「常に」 stay when they state a requirement (spec, design, procedure); drop them only when they are emphasis.
- Cannot decide → do not change; point the place out to the requester.
- Groups 1, 2 and 7 do the most harm in technical documents: check them first.

## Word groups

| # | Group | Examples | Replace with |
|---|---|---|---|
| 1 | Empty lead-in / attitude only | 「重要なのは〜である」「ここで押さえておきたいのは」「結論から言うと」「正直に言うと」「実は」「正面から扱う／向き合う」「本質的に」「多角的に分析すると」 | Delete the lead-in; write the statement itself |
| 2 | Translation-style verbs that hide the actor | 「〜を示唆している」「〜を物語っている」「〜が浮かび上がる」「〜に収斂する」「〜と対比をなしている」 | Name who / what did what, active voice: 「この結果から X だとわかる」「測定値が X であることから、Y と判断できる」 |
| 3 | Inflated kanji words | 「真理」「宿命」「境地」「極致」「美学」「重厚」「結晶」「凝縮」 | State the fact plainly |
| 4 | IT words used as metaphors | 「思考の OS をアップデートする」「習慣をインストールする」「知識をハックする」 | The literal action (「考え方を変える」「習慣をつける」); IT words only for the IT thing |
| 5 | Unneeded katakana / business jargon | 「アライメント」「インテグリティ」「レバレッジを効かせる」「アラインする」「ディープダイブする」「ピボットする」「コミットする」(meeting sense) | The usual term of the field (整合, 整合性, …) — **unless the project glossary fixes the katakana term**; established compounds (「コンテキスト長」) stay |
| 6 | Mood / texture words | 「泥臭い」「手触り」「肌感覚」「熱量」「腹落ち」「解像度が上がる」「血の通った」 | What exactly became concrete: 「どの条件で成り立つかが区別できるようになる」 |
| 7 | Avoiding a conclusion | 「ケースバイケース」「一概には言えない」「メリットもあればデメリットもある」「時と場合による」 | Which condition gives which result; if truly uncertain, say where the uncertainty is and why |
| 8 | Intensity adverbs | 「非常に」「とても」「きわめて」「圧倒的に」「〜すぎる」 (overused) | A number or a condition: 「従来比でおよそ 3 倍速い」 |

## Japanese self-check (before handing over)

Read the whole text once, list the problems, then fix. Japanese register and 敬語 rules: `style-guide.md` § 2.

1. **Rigour** — no unfounded guess, but real uncertainty kept; no two different things equated; no several causes reduced to one; a definition means the same in every section; cause → effect explained down to the mechanism.
2. **Actor** — active voice with the actor as subject; role names, not あなた; no vague「AI」「ツール」「システム」 where a name exists.
3. **Terms** — one term = one word throughout; glossary term used; field-standard translation otherwise.
4. **Paragraphs** — one topic per paragraph; first sentence says the topic; the line of argument runs one way; the conclusion is said once; a point readers often misread is denied explicitly before it is explained.
5. **No dramatisation** — no rhetorical question, build-up or dramatic closing line; bold only against misreading or for the conclusion; no ambiguous metaphor or twisted idiom.
6. **Words** — no word from the groups above that carries no information; no empty words such as「不可欠」「核心的」「掘り下げる」「〜において」used only for tone.
7. **No redundancy** — no restated point, no summary straight after a description, parallel facts in one sentence, no sentence that only connects or judges, no imagined Q&A, no 「〜という発想である」 framing.
8. **Format** — register fits the document type (`style-guide.md` § 2); spacing rule for new documents only; code, logs and commands in code blocks.

Not taken from the source skill: one sentence per line, bold first use of a term then 「」, avoiding proper names (project documents need module, file and ID names), the 6-axis × 10-point score (only when the requester asks for a score).

## Third-party notices

This file adapts content from the following works, both under the MIT License.

`japanese-tech-writing` — Copyright (c) 2026 Yasunari Hikima. Its rules are based on k16shikano「日本語技術文書の文章規範」.

`stop-ai-slop-jp` (word list, via `japanese-tech-writing`) — Copyright (c) 2026 Daichi Nagashima (iKora128).

MIT License text (applies to each work above):

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
