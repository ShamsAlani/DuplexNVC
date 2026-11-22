#!/usr/bin/env python3
"""Compare two .aus bitstreams access unit by access unit (same clip, same settings, two chips).

  python3 au_cmp.py <a.aus> <b.aus> [label]

Prints how many access units exist on each side, how many of the common ones are byte-identical, the first
differing index, and the size of each stream. Identical streams mean the two chips' encoders are bit-exact.
"""
import struct, sys


def load(path):
    aus, data, i = [], open(path, "rb").read(), 0
    while i + 4 <= len(data):
        n = struct.unpack_from("<I", data, i)[0]
        aus.append(data[i + 4:i + 4 + n]); i += 4 + n
    return aus


a, b = load(sys.argv[1]), load(sys.argv[2])
label = sys.argv[3] if len(sys.argv) > 3 else "A vs B"
n = min(len(a), len(b))
same = [x == y for x, y in zip(a[:n], b[:n])]
first = next((i for i, s in enumerate(same) if not s), None)
sa, sb = sum(map(len, a)), sum(map(len, b))
print(f"{label}: access units {len(a)} vs {len(b)}; compared {n}; identical {sum(same)}; "
      f"first difference at index {first if first is not None else 'none'}; bytes {sa} vs {sb} ({100.0 * (sb - sa) / sa:+.2f} %)")
print("bitstreams identical across chips: " + ("YES" if first is None and len(a) == len(b) else "no"))
