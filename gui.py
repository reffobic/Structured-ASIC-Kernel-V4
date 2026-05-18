# GUI for placement viewer - DD2 project
# run with: python gui.py

import copy
import random
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from Placer import netlist_error, parse_netlist
from Placement import global_placement, placement
from SA import SA_loop

random.seed(42)  # so SA is reproducible when testing

# colors for drawing 
PERIM_COLOR = "#9a9a9a"
PIN_COLOR = "#b33"
SITE_COLORS = {
    "T0": "#ebe6df",
    "T1": "#e0ebe6",
    "T2": "#e6e0eb",
    "T3": "#ebebe0",
}
CELL_COLORS = {"T0": "#3d5a80", "T1": "#4a7c59", "T2": "#7c4a6a", "T3": "#7c6a4a"}

# stages we save after each step of the pipeline
STAGES = ["parsed", "global", "legalized", "after SA"]
STAGE_NAMES = {
    "parsed": "Loaded (pins only)",
    "global": "After global placement",
    "legalized": "After placement",
    "after SA": "After simulated annealing",
}


class PlacementApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Placement viewer")
        self.root.minsize(640, 480)

        self.netlist_path = None
        self.stage_grids = {}  # stage name -> grid copy
        self.cell_px = 10
        self.busy = False

        self.setup_widgets()
        self.try_load_default_file()

    def setup_widgets(self):
        # top row - file picker
        top = ttk.Frame(self.root, padding=8)
        top.pack(fill=tk.X)

        ttk.Button(top, text="Open netlist...", command=self.open_file).pack(side=tk.LEFT)
        self.file_label = tk.StringVar(value="(no file)")
        ttk.Label(top, textvariable=self.file_label).pack(side=tk.LEFT, padx=8)

        # controls row
        row2 = ttk.Frame(self.root, padding=(8, 0, 8, 8))
        row2.pack(fill=tk.X)

        ttk.Label(row2, text="Stage:").pack(side=tk.LEFT)
        self.stage_combo = ttk.Combobox(
            row2,
            values=[STAGE_NAMES[s] for s in STAGES],
            state="readonly",
            width=30,
        )
        self.stage_combo.set(STAGE_NAMES["after SA"])
        self.stage_combo.pack(side=tk.LEFT, padx=4)
        self.stage_combo.bind("<<ComboboxSelected>>", self.when_stage_changes)

        ttk.Label(row2, text="CR:").pack(side=tk.LEFT, padx=(12, 0))
        self.cr_entry = tk.StringVar(value="0.75")
        ttk.Entry(row2, textvariable=self.cr_entry, width=6).pack(side=tk.LEFT, padx=4)

        self.run_button = ttk.Button(row2, text="Run", command=self.run_placement)
        self.run_button.pack(side=tk.LEFT, padx=8)

        self.status = tk.StringVar(value="Open a netlist and press Run.")
        ttk.Label(self.root, textvariable=self.status, padding=(8, 0)).pack(anchor=tk.W)

        # canvas area
        frame = ttk.Frame(self.root, padding=8)
        frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(frame, bg="#f5f5f5", highlightthickness=1, highlightbackground="#ccc")
        sb_x = ttk.Scrollbar(frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        sb_y = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=sb_x.set, yscrollcommand=sb_y.set)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        sb_y.grid(row=0, column=1, sticky="ns")
        sb_x.grid(row=1, column=0, sticky="ew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        # little legend at bottom
        leg = ttk.Frame(self.root, padding=(8, 4))
        leg.pack(fill=tk.X)
        for txt, col in [
            ("perimeter", PERIM_COLOR),
            ("pin", PIN_COLOR),
            ("T0", CELL_COLORS["T0"]),
            ("T1", CELL_COLORS["T1"]),
            ("T2", CELL_COLORS["T2"]),
            ("T3", CELL_COLORS["T3"]),
        ]:
            c = tk.Canvas(leg, width=14, height=14, highlightthickness=0)
            c.create_rectangle(0, 0, 14, 14, fill=col, outline="#666")
            c.pack(side=tk.LEFT, padx=2)
            ttk.Label(leg, text=txt).pack(side=tk.LEFT, padx=(0, 10))

    def try_load_default_file(self):
        folder = Path(__file__).parent
        for fname in ["design_1_small.txt", "design_2_medium.txt"]:
            p = folder / fname
            if p.exists():
                self.netlist_path = p
                self.file_label.set(fname)
                break

    def open_file(self):
        folder = Path(__file__).parent
        path = filedialog.askopenfilename(
            title="Pick netlist",
            initialdir=folder,
            filetypes=[("txt files", "*.txt"), ("everything", "*")],
        )
        if not path:
            return
        self.netlist_path = Path(path)
        self.file_label.set(self.netlist_path.name)
        self.stage_grids = {}
        self.status.set("Loaded " + self.netlist_path.name)

    def get_stage_key(self):
        # combobox shows the nice label we need the internal key
        label = self.stage_combo.get()
        for k, v in STAGE_NAMES.items():
            if v == label:
                return k
        return "after SA"

    def when_stage_changes(self, event=None):
        key = self.get_stage_key()
        if key in self.stage_grids:
            self.draw(self.stage_grids[key])

    def run_placement(self):
        if self.busy:
            return
        if self.netlist_path is None:
            messagebox.showinfo("oops", "need to open a netlist first")
            return

        try:
            cr = float(self.cr_entry.get())
            if cr <= 0 or cr >= 1:
                raise ValueError
        except ValueError:
            messagebox.showerror("CR", "CR should be between 0 and 1 (like 0.75)")
            return

        self.busy = True
        self.run_button["state"] = "disabled"
        self.status.set("running placement...")

        def do_work():
            try:
                grid = parse_netlist(self.netlist_path)
                self.stage_grids["parsed"] = copy.deepcopy(grid)

                global_placement(grid)
                self.stage_grids["global"] = copy.deepcopy(grid)
                self.root.after(0, lambda: self.draw(self.stage_grids["global"]))

                placement(grid)
                self.stage_grids["legalized"] = copy.deepcopy(grid)
                self.root.after(0, lambda: self.draw(self.stage_grids["legalized"]))

                hpwl_before, hpwl_after, acc, rej = SA_loop(cr, grid)
                self.stage_grids["after SA"] = grid

                def finish():
                    self.status.set(
                        "done! HPWL %.0f -> %.0f  (+%d / -%d moves)"
                        % (hpwl_before, hpwl_after, acc, rej)
                    )
                    self.stage_combo.set(STAGE_NAMES["after SA"])
                    self.draw(grid)
                    self.busy = False
                    self.run_button["state"] = "normal"

                self.root.after(0, finish)

            except netlist_error as e:
                def show_err():
                    messagebox.showerror("netlist error", str(e))
                    self.busy = False
                    self.run_button["state"] = "normal"
                    self.status.set(str(e))

                self.root.after(0, show_err)

        t = threading.Thread(target=do_work, daemon=True)
        t.start()

    def draw(self, g):
        # redraw everything on the canvas
        self.canvas.delete("all")
        nx, ny = g.nx, g.ny
        px = self.cell_px

        # shrink cells if grid is huge so it fits on screen
        if max(nx, ny) > 40:
            px = max(6, min(10, 480 // max(nx, ny)))
        self.cell_px = px

        w = nx * px
        h = ny * px
        self.canvas.config(scrollregion=(0, 0, w, h))

        for y in range(ny):
            for x in range(nx):
                site = g.site_at(x, y)
                x1 = x * px
                y1 = y * px
                x2 = x1 + px
                y2 = y1 + px

                if site.is_perimeter:
                    color = PERIM_COLOR
                else:
                    st = site.site_type or ""
                    color = SITE_COLORS.get(st, "#dddddd")

                self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="#bbbbbb")

                if site.fixed_pin_id is not None:
                    # draw pin as circle
                    m = max(2, px // 5)
                    self.canvas.create_oval(x1 + m, y1 + m, x2 - m, y2 - m, fill=PIN_COLOR, outline="")
                elif site.cell_id is not None:
                    comp = g.components[site.cell_id]
                    ctype = comp.cell_type
                    if ctype is None:
                        ctype = "?"
                    m = max(1, px // 6)
                    fill = CELL_COLORS.get(ctype, "#555555")
                    self.canvas.create_rectangle(x1 + m, y1 + m, x2 - m, y2 - m, fill=fill, outline="")
                    # label only if cell is big enough
                    if px >= 14 and len(ctype) > 0:
                        self.canvas.create_text(
                            x1 + px // 2,
                            y1 + px // 2,
                            text=ctype[-1],
                            fill="white",
                            font=("Helvetica", max(7, px // 2)),
                        )


def main():
    root = tk.Tk()
    PlacementApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
