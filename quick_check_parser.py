# quick_check_parser.py

from src.midkrregextool.parser import parse_file

def main():
    # 1. Parse the sample excerpt file
    tokens = parse_file("tests/fixtures/sample_sekpo_excerpt.txt")

    # 2. Print the first 30 tokens for inspection
    for t in tokens[:30]:
        print(t)

    # 3. Print the first 30 pua tokens
    for t in tokens[:10]:
        print(t.pua, [hex(ord(ch)) for ch in t.pua])

if __name__ == "__main__":
    main()
