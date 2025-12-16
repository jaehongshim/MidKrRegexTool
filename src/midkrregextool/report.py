# midkrregextool/report.py

from __future__ import annotations      # Interpret type hints later
from .model import Token
from pathlib import Path

# Formatting how to report the result either on the command line or in a separate file.

def format_hit(tok: Token) -> str:
    note_flag = "NOTE" if tok.is_note else "MAIN"
    return f"{tok.source_id} {tok.token_index} {note_flag} {tok.pua} {tok.unicode_form} {tok.yale}"

# Report on the command line

def report_hits(hits: list[Token], *, pattern: str) -> None:
    print(f"[INFO] pattern={pattern!r} hits={len(hits)}")
    for tok in hits:
        print(format_hit(tok))

# Ask a yes/no question and return True or False.
def ask_yes_no(msg: str) -> bool:
    while True:
        ans = input(f"{msg} (y/n) ").strip().lower()                
        # Clean up user input:
        #   - remove extra spaces
        #   - ignore upper/lower case differences

        if ans in ("y", "yes"):
            return True
        if ans in ("n", "no"):
            return False
        
        print("Please type 'y' or 'n'.")

# Receive the file name, and check if another file with the same name exists.

def ask_output_path() -> Path:
    while True:
        name = input(
            "Output file name with extension (e.g., results.txt): "
            ).strip()
        
        if ".txt" in name:         # Accept only file names that end with '.txt'
            return Path(name)
        
        print("Please enter a file name including an extension (e.g., results.txt).")

def confirm_overwrite(path: Path) -> bool:
    if not path.exists():
        return True
    return ask_yes_no(f"[WARN] '{path}' already exists. Overwrite?")

# Save the results file.
def write_hits(path: Path, hits: list[Token], *, pattern: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# pattern={pattern!r} hits={len(hits)}\n")
        for tok in hits:
            f.write(format_hit(tok) + "\n")

def maybe_save_hits(hits: list[Token], *, pattern: str) -> None:
    if not hits:
        print("[INFO] No hits to save.")
        return
    
    if not ask_yes_no("Save these results to a file?"):
        return
    
    path = ask_output_path()
    if not confirm_overwrite(path):
        print("[INFO] Cancelled.")
        return
    
    write_hits(path, hits, pattern=pattern)
    print(f"[INFO] Saved to: {path}")