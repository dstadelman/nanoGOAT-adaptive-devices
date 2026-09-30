"""Checks the KiCad schematic's netlist against HARDWARE.md §7.

    kicad-cli sch export netlist -o adaptive-controller.net adaptive-controller.kicad_sch
    python check_netlist.py adaptive-controller.net

Reads the §7 table straight from ../_specs/HARDWARE.md, so the spec stays the
only statement of the netlist. The table below only translates the spec's pin
words ("SW1 common", "J1 tip", "C2 −") into symbol pin numbers.
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
SPEC = HERE.parent / "_specs" / "HARDWARE.md"

# Spec pin word -> (ref, symbol pin number). U1 and K1 pins are matched by pin name.
PIN_WORDS = {
    ("BT1", "+"): "1", ("BT1", "−"): "2",
    ("SW1", "common"): "2", ("SW1", "outer pin A"): "1", ("SW1", "outer pin B"): "3",
    ("LED1", "anode"): "2", ("LED1", "cathode"): "1",
    ("C2", "+"): "1", ("C2", "−"): "2",
    ("J1", "sleeve"): "S", ("J1", "tip"): "T", ("J1", "tip switch"): "TN",
}
BY_NAME = {"U1", "K1"}  # spec uses the symbol's pin names (BAT+, D10, VCC, COM, ...)


def sexpr(text):
    tokens = re.findall(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+', text)
    stack = [[]]
    for t in tokens:
        if t == "(":
            stack.append([])
        elif t == ")":
            done = stack.pop()
            stack[-1].append(done)
        else:
            stack[-1].append(t[1:-1].replace('\\"', '"') if t.startswith('"') else t)
    return stack[0][0]


def field(node, key):
    for c in node[1:]:
        if isinstance(c, list) and c and c[0] == key:
            return c[1]
    return None


def load_netlist(path):
    root = sexpr(Path(path).read_text(encoding="utf-8"))
    nets = {}
    for sec in root[1:]:
        if isinstance(sec, list) and sec[0] == "nets":
            for net in sec[1:]:
                name = field(net, "name").lstrip("/")
                nodes = set()
                for n in net[1:]:
                    if isinstance(n, list) and n[0] == "node":
                        ref, pin = field(n, "ref"), field(n, "pin")
                        func = field(n, "pinfunction") or ""
                        # KiCad reports pinfunction as "<name>_<number>" when names repeat; strip it
                        func = re.sub(r"_" + re.escape(pin) + r"$", "", func)
                        nodes.add((ref, pin, func))
                nets[name] = nodes
    return nets


def resolve(token, name_index):
    token = token.strip()
    m = re.match(r"^(\w+)\.(\w+)$", token)  # R1.1
    if m:
        return (m.group(1), m.group(2))
    ref, word = token.split(" ", 1)
    word = word.strip()
    if ref in BY_NAME:  # symbol pin names are ASCII: BAT- for the spec's BAT−
        return (ref, name_index[(ref, word.replace("−", "-"))])
    return (ref, PIN_WORDS[(ref, word)])


def load_spec():
    md = SPEC.read_text(encoding="utf-8")
    sec = md.split("## 7. Netlist", 1)[1].split("\n## ", 1)[0]
    nets, nc = {}, []
    for line in sec.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 2 or cells[0] in ("Net", "") or set(cells[0]) <= set("-"):
            continue
        tokens = [t.strip() for t in cells[1].split("·")]
        if cells[0] == "No connect":
            nc = tokens
        else:
            nets[cells[0]] = tokens
    return nets, nc


def main(path):
    kinets = load_netlist(path)
    name_index = {}
    for nodes in kinets.values():
        for ref, pin, func in nodes:
            if func:
                name_index[(ref, func)] = pin
    spec_nets, spec_nc = load_spec()
    ok = True
    used = set()
    for net, tokens in spec_nets.items():
        want = {resolve(t, name_index) for t in tokens}
        got = {(r, p) for r, p, _ in kinets.get(net, set())}
        used |= want
        if net not in kinets:
            print(f"FAIL {net}: no net with this name in the schematic")
            ok = False
        elif want != got:
            print(f"FAIL {net}: missing {sorted(want - got)} extra {sorted(got - want)}")
            ok = False
        else:
            print(f"ok   {net:<11} {len(want)} pins")
    # every other net must be a single unconnected pin
    for net, nodes in kinets.items():
        if net in spec_nets:
            continue
        if len(nodes) != 1:
            print(f"FAIL extra net {net}: {sorted(nodes)}")
            ok = False
    unconnected = {(r, p) for net, nodes in kinets.items() if net not in spec_nets for r, p, _ in nodes}
    nc_ok = True
    for t in spec_nc:
        rp = resolve(t, name_index)
        if rp not in unconnected:
            print(f"FAIL no-connect {t} {rp} is connected")
            nc_ok = ok = False
    if nc_ok:
        print(f"ok   No connect: {', '.join(spec_nc)}")
    others = sorted(unconnected - {resolve(t, name_index) for t in spec_nc})
    bad = [rp for rp in others if rp[0] != "U1"]
    if bad:
        print(f"FAIL unconnected pins outside U1: {bad}")
        ok = False
    print("     unused U1 pins (HARDWARE §2):",
          ", ".join(f for (r, p, f) in sorted(
              {n for nodes in kinets.values() for n in nodes if (n[0], n[1]) in others},
              key=lambda n: int(n[1]))))
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else HERE / "adaptive-controller.net"))
