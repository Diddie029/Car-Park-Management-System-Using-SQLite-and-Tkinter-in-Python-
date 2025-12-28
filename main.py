import sqlite3, math
from tkinter import *
from tkinter import ttk, messagebox
from datetime import datetime

# ================= DATABASE =================
db = sqlite3.connect("carpark.db")
cur = db.cursor()

cur.execute("""CREATE TABLE IF NOT EXISTS parking(
id INTEGER PRIMARY KEY,
plate TEXT UNIQUE,
type TEXT,
floor TEXT,
slot INTEGER,
time_in TEXT)""")

cur.execute("""CREATE TABLE IF NOT EXISTS settings(
slots INTEGER,
rate INTEGER,
floors INTEGER)""")

cur.execute("""CREATE TABLE IF NOT EXISTS transactions(
plate TEXT,
floor TEXT,
slot INTEGER,
hours INTEGER,
amount INTEGER,
date TEXT)""")

cur.execute("SELECT COUNT(*) FROM settings")
if cur.fetchone()[0] == 0:
    cur.execute("INSERT INTO settings VALUES(10,50,3)")
db.commit()

# ================= HELPERS =================
def get_settings():
    cur.execute("SELECT * FROM settings")
    return cur.fetchone()

def get_used_slots(floor):
    cur.execute("SELECT slot FROM parking WHERE floor=?", (floor,))
    return [r[0] for r in cur.fetchall()]

def clear_inputs():
    plate_entry.delete(0, END)
    type_entry.delete(0, END)

# ================= DASHBOARD =================
def update_dashboard():
    slots, _, floors = get_settings()
    dash_tree.delete(*dash_tree.get_children())

    for f in range(1, floors + 1):
        floor_name = f"Floor {f}"
        used = len(get_used_slots(floor_name))
        dash_tree.insert("", END,
            values=(floor_name, slots, used, slots - used))

# ================= SLOT VISUAL =================
def render_slots(highlight=None):
    for w in slot_frame.winfo_children():
        w.destroy()

    slots, _, _ = get_settings()
    used = get_used_slots(floor_var.get())
    cols = 5

    for i in range(1, slots + 1):
        color = "red" if i in used else "green"
        btn = Button(slot_frame, text=f"Slot {i}",
                     bg=color, fg="white",
                     width=12, height=2,
                     command=lambda s=i: slot_info(s))
        btn.grid(row=(i-1)//cols, column=(i-1)%cols, padx=5, pady=5)

        if highlight == i:
            animate_slot(btn, color)

def animate_slot(widget, base_color):
    widget.after(0, lambda: widget.config(bg="yellow"))
    widget.after(300, lambda: widget.config(bg=base_color))

def slot_info(slot):
    cur.execute("""SELECT plate, type, time_in
                   FROM parking
                   WHERE floor=? AND slot=?""",
                (floor_var.get(), slot))
    data = cur.fetchone()
    if not data:
        messagebox.showinfo("Slot Info", "Slot is empty")
    else:
        messagebox.showinfo(
            "Slot Info",
            f"Plate: {data[0]}\nType: {data[1]}\nTime In: {data[2]}"
        )

# ================= CORE =================
def park_vehicle():
    plate = plate_entry.get()
    vtype = type_entry.get()
    floor = floor_var.get()

    if not plate or not vtype:
        return messagebox.showwarning("Error", "All fields required")

    slots, _, _ = get_settings()
    used = get_used_slots(floor)

    if len(used) >= slots:
        return messagebox.showerror("Full", "Floor is full")

    for s in range(1, slots + 1):
        if s not in used:
            slot = s
            break

    try:
        cur.execute("""INSERT INTO parking
                       VALUES(NULL,?,?,?,?,?)""",
                    (plate, vtype, floor, slot,
                     datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        db.commit()
        clear_inputs()
        refresh(slot)
    except:
        messagebox.showerror("Error", "Vehicle already parked")

def exit_vehicle():
    sel = tree.selection()
    if not sel:
        return

    data = tree.item(sel)["values"]
    time_in = datetime.strptime(data[5], "%Y-%m-%d %H:%M:%S")
    hours = math.ceil((datetime.now() - time_in).seconds / 3600)
    rate = get_settings()[1]
    fee = hours * rate

    cur.execute("DELETE FROM parking WHERE id=?", (data[0],))
    cur.execute("""INSERT INTO transactions
                   VALUES(?,?,?,?,?,?)""",
                (data[1], data[3], data[4],
                 hours, fee, datetime.now().strftime("%Y-%m-%d")))
    db.commit()

    messagebox.showinfo("Receipt",
        f"Plate: {data[1]}\nFloor: {data[3]}\nSlot: {data[4]}"
        f"\nHours: {hours}\nFee: ₱{fee}")
    refresh(data[4])

def refresh(highlight=None):
    tree.delete(*tree.get_children())
    cur.execute("SELECT * FROM parking")
    for r in cur.fetchall():
        tree.insert("", END, values=r)

    render_slots(highlight)
    update_dashboard()

# ================= GUI =================
root = Tk()
root.title("Car Park Management System")
root.geometry("1100x700")

notebook = ttk.Notebook(root)
notebook.pack(expand=True, fill="both")

# ---------- TAB 1: PARKING ----------
tab1 = Frame(notebook)
notebook.add(tab1, text="🚗 Parking")

Label(tab1, text="Plate Number").grid(row=0, column=0, pady=10)
plate_entry = Entry(tab1)
plate_entry.grid(row=0, column=1)

Label(tab1, text="Vehicle Type").grid(row=1, column=0)
type_entry = Entry(tab1)
type_entry.grid(row=1, column=1)

Label(tab1, text="Floor").grid(row=2, column=0)
floor_var = StringVar(value="Floor 1")
floor_combo = ttk.Combobox(tab1, textvariable=floor_var,
                           values=["Floor 1", "Floor 2", "Floor 3"],
                           state="readonly")
floor_combo.grid(row=2, column=1)
floor_combo.bind("<<ComboboxSelected>>", lambda e: render_slots())

Button(tab1, text="Park Vehicle", width=15, command=park_vehicle)\
    .grid(row=3, column=0, pady=10)
Button(tab1, text="Clear Fields", width=15, command=clear_inputs)\
    .grid(row=3, column=1)

Label(tab1, text="Parking Slots",
      font=("Arial",11,"bold")).grid(row=4, columnspan=2, pady=10)

slot_frame = Frame(tab1)
slot_frame.grid(row=5, columnspan=2)

# ---------- TAB 2: RECORDS ----------
tab2 = Frame(notebook)
notebook.add(tab2, text="📋 Records")

tree = ttk.Treeview(tab2,
    columns=("ID","Plate","Type","Floor","Slot","Time"),
    show="headings")
for col in ("ID","Plate","Type","Floor","Slot","Time"):
    tree.heading(col, text=col)
    tree.column(col, width=150)
tree.pack(expand=True, fill="both", padx=10, pady=10)

Button(tab2, text="Exit Selected Vehicle",
       command=exit_vehicle).pack(pady=5)

# ---------- TAB 3: DASHBOARD ----------
tab3 = Frame(notebook)
notebook.add(tab3, text="📊 Dashboard")

dash_tree = ttk.Treeview(tab3,
    columns=("Floor","Total","Occupied","Available"),
    show="headings")
for col in ("Floor","Total","Occupied","Available"):
    dash_tree.heading(col, text=col)
    dash_tree.column(col, width=200, anchor="center")
dash_tree.pack(expand=True, fill="both", padx=20, pady=20)

refresh()
root.mainloop()
