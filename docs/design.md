# Planned processing pipeline

## Input

- The input will be Middle Korean texts encoded in Hanyang PUA.
- The repository itself does need to contain the original corpus.
- The program is designed to run on either a single text file or a folder with multiple txt files, specified via command-line arguments. 

## Basic idea

- Parse the input text, tokenize it, and keep track of:
    - source ID (from markup)
    - token index
    - the original Hanyang PUA form
- Convert Hanyang PUA to Yale romanization,
- Perform regex search over the Yale representation.
- For each matched token, output a tuple containing:
    - the Yale form
    - the token index
    - the source ID
    - the original Hanyang PUA form
    - (optionally) a Unicode compatible form derived from PUA

## Parser Behavior

This section documents how the current parser processes Middle Korean text encoded in Hanyang PUA.

### 1. Input assumptions
- Each source block begins with a marker such as `<釋詳3:1a>`.
- Notes are marked by `[note]` and `[/note]`. 
- Structural markup such as `[head] ... [/head]` and `[add] ... [/add]` may appear, but their contents remain part of the main text. 

### 2. Tokenization pipeline
Given a line such as:

<釋詳3:1a> [head] 釋譜詳節第三 [/head] 淨飯王이 相  사 五百 大寶殿에 뫼호아 太子 뵈더시니 모다  出家시면 成佛시고 [note] 成佛은 부텻 道理 일우실 씨라 [/note] 지븨 겨시면 輪王이 외시리로소다   香山ㅅ 阿私陁 仙人이 외$다

the parser performs the following steps:

1. **Source detection.**
The prefix `<釋詳3:1a>` is detected.
- `source_id` is set to `釋詳3:1a`.
- `token_index` resets to 0.

2. **Structural tag removal.**
`[head]`, `[add]` tags are stripped while their inner text is preserved. 
Note flags are not removed but handled specially in the next step.

3. **Note tracking.**
When `[note]` is encountered, the parser enters `inside_note = True`.
Upon `[/note]`, it returns to `inside_note = False`.

4. **Whitespace tokenization.**
Each text segment is split by whitespace into tokens.
Each token becomes a `Token` object with:
- `source_id` (e.g., `釋詳3:1a`)
- `token_index` (growing within the source block)
- `pua` (raw PUA string)
- `is_note` (True for tokens inside `[note] ... [/note]`)

### 3. Example output
--- SOURCE 釋詳3:1a ---
釋詳3:1a | 1 | MAIN | 釋譜詳節第三
釋詳3:1a | 2 | MAIN | 淨飯王이
...
釋詳3:1a | 14 | MAIN | 成佛ꥠ시고

釋詳3:1a | 15 | NOTE | 成佛은
釋詳3:1a | 16 | NOTE | 부텻
...

釋詳3:1a | 20 | MAIN | 지븨
...

--- SOURCE 釋詳3:1b ---
釋詳3:1b | 1 | MAIN | 그
釋詳3:1b | 2 | MAIN | 仙人이
...

### 4. Design notes
- `token_index` resets for each new source block, since each block corresponds to a distinct textual location.
- Notes are fully preserved to allow later filtering or separate analysis.
- The parser produces PUA forms untouched; Unicode normalization or Yale conversion is applied in later stages.