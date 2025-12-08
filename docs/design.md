# Planned processing pipeline

## Input

- The input will be Middle Korean texts encoded in Hanyang PUA.
- The repository itself does not contain the original corpus.
- The program will run on either a txt file or a folder with multiple txt files. 
- The tool will always accept the file path as a command-line argument (e.g. `--input path/to/file`)

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
