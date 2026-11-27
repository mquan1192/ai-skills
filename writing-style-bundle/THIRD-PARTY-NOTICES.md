# Third-party notices — writing-style-bundle

The bundle itself is licensed under the Apache License 2.0 (`LICENSE`). From version 1.1.0 (and more from 1.2.0), the files below contain material adapted from third-party works under the MIT License. The MIT License requires the copyright notice and the permission notice to be kept in all copies or substantial portions; both are reproduced in full below.

| Bundle file | Material used | Source work |
|---|---|---|
| `skills/q-writing-style/references/ng-vocab-ja.md` | Japanese word groups to drop or replace, Japanese self-check (selected and adapted) | `japanese-tech-writing` (which adapts the word list of `stop-ai-slop-jp`) |
| `skills/q-writing-style/references/style-guide.md` § 0, § 2 | Writing principles (rigour, named actor, one term per concept, paragraph structure, no dramatisation, no repetition, Japanese spacing) — restated in our own words | `japanese-tech-writing` |
| `skills/q-writing-style/references/ai-tells.md` | Groups and strength order of AI-writing patterns, the "when not to act" and "keep the writer's voice" rules — restated in Vietnamese with new VI / JA examples | `humanizer` (v4.0.0) |
| `skills/q-writing-style/references/plain-language.md`, `references/ng-vocab-en.md` § "Plain swaps" | Plain-English rules (procedural vs descriptive, sentence limits, can / will / must, condition before command), use-case patterns, word swaps — selected and adapted | `SimpleEnglish` (v2.1.2) |
| `skills/q-writing-style/references/vietnamese-register.md` | Register matrix, B2B address, code-switching rule, calque list, NFC and tone-mark rules, localisation notes — selected and adapted | `vietnamese-language-skill` |

General idea only, no text: `skills/q-writing-style/references/voice-profile.md` shares the idea of building a reusable voice profile from several of the author's texts with `writing-dna-skill` (https://github.com/larashero3-dotcom/writing-dna-skill); its five parts, questions and template were written for this bundle. The "when not to act" and voice rules in `ai-tells.md` are adapted from `humanizer` (MIT), not from `writing-dna-skill` or its `lieflat-less-ai-tone` skill. That work is under the PolyForm Noncommercial License 1.0.0, which is not compatible with this bundle's license, so no sentence, template or file of it is included.

The MIT notices of `humanizer`, `SimpleEnglish` and `vietnamese-language-skill` are reproduced below and also in `skills/q-writing-style/NOTICES.md`, which is installed with the skill.

The rules of `japanese-tech-writing` are based on k16shikano, 「日本語技術文書の文章規範」 (gist). Only ideas are used from that work; no sentence of it is copied into this bundle.

---

## japanese-tech-writing

https://github.com/hikimay/japanese-tech-writing (version 1.1.0)

MIT License

Copyright (c) 2026 Yasunari Hikima

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

---

## stop-ai-slop-jp

https://github.com/iKora128/stop-ai-slop-jp

Copyright (c) 2026 Daichi Nagashima

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

---

## humanizer

https://github.com/blader/humanizer

MIT License

Copyright (c) 2025 Siqi Chen

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

---

## SimpleEnglish

https://github.com/AminBlg/SimpleEnglish

MIT License

Copyright (c) 2026 AminBlg

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

---

## vietnamese-language-skill

https://github.com/trussary/vietnamese-language-skill

MIT License

Copyright (c) 2026 vietnamese-language-skill contributors

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
