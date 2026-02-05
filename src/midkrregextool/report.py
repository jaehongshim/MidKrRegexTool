# midkrregextool/report.py

from __future__ import annotations      # Interpret type hints later
from .model import Token
from pathlib import Path


DEFAULT_OUTPUT_ENCODING = "utf-16"



def format_hit(tok: Token) -> str:
    if tok.context is not None:
        return(
            f"{tok.source_id} {tok.token_index} {tok.is_note} [{tok.path}]\n"
            f"\t[TOKEN]\t\t{tok.unicode_form}\n"
            f"\t[TAGGED-FORM]\t{tok.tagged_form}\n"
            f"\t[MATCHED-PART]\t{tok.matched_part}\n"
            f"\t[CONTEXT]\t{tok.context}"
        )
    else:
        return(
            f"{tok.source_id} {tok.token_index} {tok.is_note} [{tok.path}]\n"
            f"\t[TOKEN]\t\t{tok.unicode_form}\n"
            f"\t[TAGGED-FORM]\t{tok.tagged_form}\n"
            f"\t[MATCHED-PART]\t{tok.matched_part}\n"
        )

def format_bigram(a: Token, b: Token) -> str:
    if a.context is not None:
        return (
            f"{a.source_id} {a.token_index}-{b.token_index} {a.is_note} [{a.path}]\n"
            f"\t[TOKEN]\t\t{a.unicode_form} {b.unicode_form}\n"
            f"\t[TAGGED-FORM]\t{a.tagged_form} {b.tagged_form}\n"
            f"\t[MATCHED_PART]\t{a.matched_part}\n"
            f"\t[CONTEXT]\t{a.context}"
        )
    else:
        return (
            f"{a.source_id} {a.token_index}-{b.token_index} {a.is_note} [{a.path}]\n"
            f"\t[TOKEN]\t\t{a.unicode_form} {b.unicode_form}\n"
            f"\t[TAGGED-FORM]\t{a.tagged_form} {b.tagged_form}\n"
            f"\t[MATCHED_PART]\t{a.matched_part}\n"
        )
    # Comment the following out if you need PUA forms.
    # return f"{a.source_id} {a.token_index}-{b.token_index} {a.is_note} {a.pua} {b.pua} {a.unicode_form} {b.unicode_form} {a.yale} {b.yale}"

# Report on the command line

def report_hits(hits: list[tuple[Token, ...]], bigram_flag: bool = False) -> None:
    
    # For bigram searches
    if bigram_flag:
        for (a,b) in hits:
            print(format_bigram(a, b))
    else:
        for (tok,) in hits:
            print(format_hit(tok))

# def report_bigram_hits(hits: list[tuple[Token, ...]], *, pattern: str, comment: str | None = None) -> None:
#     print(f"[INFO] pattern={pattern!r} hits={len(hits)} comments={comment!r}")
#     print("-" * 70)

#     for (a,b) in hits:
#         print(format_bigram(a, b))

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

def format_monogram_results(tok: Token) -> str:
    if tok.context is not None:
        return f"{tok.path}\t{tok.source_id} {tok.token_index} {tok.is_note}\t{tok.unicode_form}\t{tok.tagged_form}\t{tok.matched_part}\t{tok.context}"
    else:
        return f"{tok.path}\t{tok.source_id} {tok.token_index} {tok.is_note}\t{tok.unicode_form}\t{tok.tagged_form}\t{tok.matched_part}\t\t"

def format_bigram_results(a: Token, b: Token) -> str:
    if a.context is not None:
        return f"{a.path}\t{a.source_id} {a.token_index}-{b.token_index} {a.is_note}\t{a.unicode_form} {b.unicode_form}\t{a.tagged_form} {b.tagged_form}\t{a.matched_part}\t{a.context}"
    else:
        return f"{a.path}\t{a.source_id} {a.token_index}-{b.token_index} {a.is_note}\t{a.unicode_form} {b.unicode_form}\t{a.tagged_form} {b.tagged_form}\t{a.matched_part}\t\t"
    # Comment the following out if you need PUA forms.
    # return f"{a.source_id} {a.token_index}-{b.token_index} {a.is_note} {a.pua} {b.pua} {a.unicode_form} {b.unicode_form} {a.yale} {b.yale}"

# Save the results file.
def write_hits(path: Path, hits: list[tuple[Token, ...]], *, pattern: str, purpose: str | None = None, note: str | None = None) -> None:
    with open(path, "w", encoding=DEFAULT_OUTPUT_ENCODING, newline="\n") as f:
        f.write(f"FILE_PATH\tSOURCE\tTOKEN\tTAGGED-FORM\tMATCHED-PART\tCONTEXT\tNOTE\t# pattern={pattern!r} hits={len(hits)} purpose={purpose!r} note={note!r}\n")
        if " " in pattern:
            for a, b in hits:
                f.write(format_bigram_results(a,b) + "\n")
        else:
            for (tok,) in hits:
                f.write(format_monogram_results(tok) + "\n")

# def write_bigram_hits(path: Path, hits: list[tuple[Token, ...]], *, pattern: str, comment: str | None = None) -> None:
#     with open(path, "w", encoding=DEFAULT_OUTPUT_ENCODING, newline="\n") as f:
#         f.write(f"# pattern={pattern!r} hits={len(hits)} comment={comment!r}\n")
#         for a, b in hits:
#             f.write(format_bigram(a,b) + "\n")

def maybe_save_hits(hits: list[tuple[Token, ...]], *, pattern: str, purpose: str | None = None) -> None:
    if not hits:
        print("[INFO] No hits to save.")
        return
    
    if not ask_yes_no("Save these results to a file?"):
        return
    
    path = ask_output_path()
    if not confirm_overwrite(path):
        print("[INFO] Cancelled.")
        return
    
    note = input("Enter note for the current search (or press Enter to skip): ").strip()
    
    write_hits(path, hits, pattern=pattern, purpose=purpose, note=note)
    print(f"[INFO] Saved to: {path}")