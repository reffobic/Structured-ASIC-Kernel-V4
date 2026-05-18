# makes the graphs for the report 

import csv
import random
from pathlib import Path

import matplotlib.pyplot as plt

from Placer import parse_netlist
from Placement import global_placement, placement
from SA import SA_loop

random.seed(42)

here = Path(__file__).parent
out_dir = here / "graphs"
data_dir = out_dir / "data"

designs = [
    "design_1_small.txt",
    "design_2_medium.txt",
    "design_3_large.txt",
    "design_4_dense.txt",
    "design_5_extreme.txt",
]

crs = [0.75, 0.8, 0.85, 0.9, 0.95]


def run_design(netlist, cr, log_steps=False):
    g = parse_netlist(netlist)
    global_placement(g)
    placement(g)
    history = [] if log_steps else None
    before, after, acc, rej = SA_loop(cr, g, history=history)
    return before, after, history


def main():
    out_dir.mkdir(exist_ok=True)
    data_dir.mkdir(exist_ok=True)

    # temp vs twl at CR 0.95 (handout) + hpwl vs step plots
    cr_plot = 0.95
    temp_runs = []

    print("CR =", cr_plot, "runs...")
    for fname in designs:
        path = here / fname
        if not path.exists():
            continue
        print(" ", fname)
        before, after, hist = run_design(path, cr_plot, log_steps=True)
        name = fname.replace(".txt", "")
        temp_runs.append((name, cr_plot, hist))

        # save numbers to csv
        csv_path = data_dir / ("temp_vs_twl_%s_CR%.2f.csv" % (name, cr_plot))
        with csv_path.open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["step", "temperature", "twl"])
            for step, T, twl, best in hist:
                w.writerow([step, T, twl])

        # hpwl over steps (prof style)
        steps = [row[0] for row in hist]
        cur = [row[2] for row in hist]
        best = [row[3] for row in hist]
        plt.figure()
        plt.plot(steps, cur, color="gray", label="current")
        plt.plot(steps, best, label="best so far")
        plt.xlabel("step")
        plt.ylabel("HPWL")
        plt.title(name + " CR=" + str(cr_plot))
        plt.legend()
        plt.savefig(out_dir / ("hpwl_steps_%s.png" % name))
        plt.close()

        # temp vs twl (linear axis, handout)
        temps = [row[1] for row in hist]
        twls = [row[2] for row in hist]
        plt.figure()
        plt.plot(temps, twls, "b.-")
        plt.xlabel("temperature")
        plt.ylabel("TWL")
        plt.title(name + " CR=" + str(cr_plot))
        plt.savefig(out_dir / ("temp_vs_twl_%s.png" % name))
        plt.close()

    # CR vs final twl
    print("CR sweep...")
    cr_log = data_dir / "cr_vs_final_twl.csv"
    with cr_log.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["design", "cr", "twl_before", "twl_after"])
        for fname in designs:
            path = here / fname
            if not path.exists():
                continue
            for cr in crs:
                print(" ", fname, cr)
                before, after, _ = run_design(path, cr, log_steps=False)
                w.writerow([fname, cr, before, after])

    # one plot for all designs
    rows = []
    with cr_log.open() as f:
        r = csv.DictReader(f)
        for line in r:
            rows.append(line)

    plt.figure()
    for fname in designs:
        pts = [(float(r["cr"]), float(r["twl_after"])) for r in rows if r["design"] == fname]
        if not pts:
            continue
        pts.sort()
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        plt.plot(xs, ys, "o-", label=fname.replace(".txt", ""))
    plt.xlabel("CR")
    plt.ylabel("final TWL")
    plt.legend()
    plt.savefig(out_dir / "cr_vs_final_twl.png")
    plt.close()

    print("done - check graphs/")


if __name__ == "__main__":
    main()
