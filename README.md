# MidKrRegexTool

A regex-based search tool for Middle Korean texts, designed to support research on morphosyntactic patterns. 

The tool operates over Middle Korean texts encoded in the Hanyang PUA format, converts them into Unicode and Yale romanized forms, and performs a regex search over the Yale romanized forms. The program currently supports the monogram and bigram searches. 

## Pipeline overview

The current processing pipeline is as follows:

```
excerpt text
↓
parser.py → list[Token] 
↓
yale.py → tokens with unicode_form and yale
↓
search.py → search hits (monogram or bigram)
↓
report.py → command-line output / optional file output
```

## Regex search behavior

### Monogram search
- Applied when the regex does not span whitespace.
- Matches against `token.yale`.
- N.B. Non-whitespace characters must be written as `[^\s]`, not `[^ ]`

### Bigram search
- Applied when the regex pattern **contains a literal space character (`" "`)**. 
- Matches are evaluated against the concatenation of two adjacent tokens.

## Output
Search results are printed to the command line with a header indicating:
- the regex pattern
- the number of hits

Users are then prompted to optionally save the results as a UTF-8 text file.

## Current limitations
- Bigram results are not yet saved as a separate UTF-8 text file (to be implemented).
- Only single-file processing is currently supported.

## Planned extensions
- Batch processing of multiple input files.
- An optional user-provided `comment` field attached to search results, allowing researchers to record the intent of a given regex search.
