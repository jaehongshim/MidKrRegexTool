# MidKrRegexTool

A tool for searching Middle Korean texts (encoded in Hanyang PUA) using regular expressions.

## Input

- The tool does not require any corpus to be stored inside the repository. Instead, it always takes one or more external Middle Korean text files (or folders) as input.

## Project Status
The first working version of the parser has been implemented.
It reads Hanyang PUA-encoded Middle Korean text, detects source markers, tokenizes both main text and notes, and assigns metadata to each token.
Yale conversion and regex-based search will be added next.