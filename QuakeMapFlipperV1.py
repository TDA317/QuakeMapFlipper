import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import re
import os

# Regular expressions to find coordinates
# Matches entity key-value pairs like "origin" "x y z"
entity_origin_re = re.compile(r'^\s*("origin")\s*("(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)")\s*$')
# Matches brush plane definitions: ( v1x v1y v1z ) ( v2x v2y v2z ) ( v3x v3y v3z ) texture_info
plane_re = re.compile(
    r'^\s*'
    r'\(\s*(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s*\)\s*' # Vertex 1 (x, y, z)
    r'\(\s*(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s*\)\s*' # Vertex 2 (x, y, z)
    r'\(\s*(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s*\)\s*' # Vertex 3 (x, y, z)
    r'(.*)$' # Rest of the line (texture info etc.)
)

def flip_coordinate(coord_str, flip_x, flip_y, flip_z):
    """Flips a single coordinate value based on selected axes."""
    val = float(coord_str)
    if flip_x:
        val = -val # Assuming X flip negates X
    # Add Y and Z logic if needed, assuming simple negation for now
    # This function might need refinement based on exact flip axis definition
    # For simplicity now, we'll flip components directly in main logic
    return val # This helper isn't used directly below, logic is inline

def process_map_file(input_path, output_path, flip_x, flip_y, flip_z):
    """Reads the input map, flips coordinates, and writes to output path."""
    if not (flip_x or flip_y or flip_z):
        messagebox.showerror("Error", "Please select at least one axis to flip.")
        return False

    try:
        with open(input_path, 'r') as infile, open(output_path, 'w') as outfile:
            brace_level = 0
            in_brush = False # Crude check: are we inside the *first* level of braces within an entity?
                            # More robust parsing might track entity types.
            flip_axis_count = sum([flip_x, flip_y, flip_z])
            reverse_winding = (flip_axis_count % 2 != 0)

            for line in infile:
                stripped_line = line.strip()

                if not stripped_line: # Preserve empty lines
                    outfile.write(line)
                    continue

                # Track brace levels to identify entities and brushes
                if stripped_line == "{":
                    brace_level += 1
                    # Heuristic: brushes start at brace_level 2 (inside an entity)
                    if brace_level == 2:
                         in_brush = True
                    outfile.write(line)
                    continue
                elif stripped_line == "}":
                    if brace_level == 2:
                        in_brush = False
                    brace_level = max(0, brace_level - 1) # Prevent going below 0
                    outfile.write(line)
                    continue

                processed_line = line # Default to original line

                # Check for entity origin line (only process if not inside a brush)
                if not in_brush and brace_level == 1:
                    origin_match = entity_origin_re.match(line)
                    if origin_match:
                        key = origin_match.group(1)
                        # quote_val = origin_match.group(2) # full quoted value "x y z"
                        x, y, z = map(float, [origin_match.group(3), origin_match.group(4), origin_match.group(5)])

                        new_x = -x if flip_x else x
                        new_y = -y if flip_y else y
                        new_z = -z if flip_z else z

                        # Preserve original formatting as much as possible (integer if possible)
                        fmt = lambda v: int(v) if v == int(v) else v
                        processed_line = f'  "{key}" "{fmt(new_x)} {fmt(new_y)} {fmt(new_z)}"\n'
                        # print(f"Flipping Origin: ({x},{y},{z}) -> ({new_x},{new_y},{new_z})") # Debug

                # Check for brush plane definition (only if inside a brush)
                elif in_brush and brace_level == 2:
                    plane_match = plane_re.match(line)
                    if plane_match:
                        v1x, v1y, v1z = map(float, plane_match.group(1, 2, 3))
                        v2x, v2y, v2z = map(float, plane_match.group(4, 5, 6))
                        v3x, v3y, v3z = map(float, plane_match.group(7, 8, 9))
                        texture_info = plane_match.group(10).strip() # Preserve texture part

                        # Flip coordinates for each vertex
                        nv1x, nv1y, nv1z = (-v1x if flip_x else v1x, -v1y if flip_y else v1y, -v1z if flip_z else v1z)
                        nv2x, nv2y, nv2z = (-v2x if flip_x else v2x, -v2y if flip_y else v2y, -v2z if flip_z else v2z)
                        nv3x, nv3y, nv3z = (-v3x if flip_x else v3x, -v3y if flip_y else v3y, -v3z if flip_z else v3z)

                        # Format vertices (try to keep integers if they were integers)
                        fmt_v = lambda x,y,z: " ".join(map(lambda v: str(int(v)) if v == int(v) else str(v), [x,y,z]))

                        v1_str = fmt_v(nv1x, nv1y, nv1z)
                        v2_str = fmt_v(nv2x, nv2y, nv2z)
                        v3_str = fmt_v(nv3x, nv3y, nv3z)

                        # Reverse winding order if an odd number of axes are flipped
                        if reverse_winding:
                            processed_line = f"( {v1_str} ) ( {v3_str} ) ( {v2_str} ) {texture_info}\n"
                            # print("Flipping Plane & Reversing Winding") # Debug
                        else:
                            processed_line = f"( {v1_str} ) ( {v2_str} ) ( {v3_str} ) {texture_info}\n"
                            # print("Flipping Plane") # Debug

                outfile.write(processed_line)

        return True

    except FileNotFoundError:
        messagebox.showerror("Error", f"Input file not found:\n{input_path}")
        return False
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred during processing:\n{e}")
        return False

# --- GUI Setup ---
class MapFlipperApp:
    def __init__(self, master):
        self.master = master
        master.title("Quake .map Flipper")
        master.geometry("500x300")

        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.flip_x = tk.BooleanVar()
        self.flip_y = tk.BooleanVar()
        self.flip_z = tk.BooleanVar()

        # Input File Section
        input_frame = ttk.LabelFrame(master, text="Input Map File", padding=(10, 5))
        input_frame.pack(padx=10, pady=5, fill=tk.X)

        input_entry = ttk.Entry(input_frame, textvariable=self.input_path, width=50)
        input_entry.pack(side=tk.LEFT, padx=(0, 5), expand=True, fill=tk.X)

        input_button = ttk.Button(input_frame, text="Browse...", command=self.browse_input)
        input_button.pack(side=tk.LEFT)

        # Output File Section
        output_frame = ttk.LabelFrame(master, text="Output Map File", padding=(10, 5))
        output_frame.pack(padx=10, pady=5, fill=tk.X)

        output_entry = ttk.Entry(output_frame, textvariable=self.output_path, width=50)
        output_entry.pack(side=tk.LEFT, padx=(0, 5), expand=True, fill=tk.X)

        output_button = ttk.Button(output_frame, text="Browse...", command=self.browse_output)
        output_button.pack(side=tk.LEFT)

        # Axis Selection Section
        axis_frame = ttk.LabelFrame(master, text="Flip Axis (-coord = coord * -1)", padding=(10, 10))
        axis_frame.pack(padx=10, pady=10, fill=tk.X)

        ttk.Checkbutton(axis_frame, text="Flip X Axis", variable=self.flip_x).pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(axis_frame, text="Flip Y Axis", variable=self.flip_y).pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(axis_frame, text="Flip Z Axis", variable=self.flip_z).pack(side=tk.LEFT, padx=5)

        # Action Button
        self.status_label = ttk.Label(master, text="")
        self.status_label.pack(pady=5)

        process_button = ttk.Button(master, text="Flip Map", command=self.run_flip)
        process_button.pack(pady=10)


    def browse_input(self):
        filename = filedialog.askopenfilename(
            title="Select Quake Map File",
            filetypes=(("Quake Map Files", "*.map"), ("All Files", "*.*"))
        )
        if filename:
            self.input_path.set(filename)
            # Suggest an output filename based on input
            if not self.output_path.get():
                base, ext = os.path.splitext(filename)
                self.output_path.set(f"{base}_flipped{ext}")

    def browse_output(self):
        filename = filedialog.asksaveasfilename(
            title="Save Flipped Quake Map File As...",
            filetypes=(("Quake Map Files", "*.map"), ("All Files", "*.*")),
            defaultextension=".map"
        )
        if filename:
            self.output_path.set(filename)

    def run_flip(self):
        in_file = self.input_path.get()
        out_file = self.output_path.get()

        if not in_file or not out_file:
            messagebox.showerror("Error", "Please specify both input and output files.")
            return

        self.status_label.config(text="Processing...")
        self.master.update_idletasks() # Update GUI to show status

        success = process_map_file(
            in_file,
            out_file,
            self.flip_x.get(),
            self.flip_y.get(),
            self.flip_z.get()
        )

        if success:
            self.status_label.config(text=f"Map successfully flipped to:\n{out_file}")
            messagebox.showinfo("Success", f"Map successfully flipped!\nOutput saved to:\n{out_file}")
        else:
             self.status_label.config(text="Processing failed. See error message.")
        # No need for explicit error message here as process_map_file shows message boxes


if __name__ == "__main__":
    root = tk.Tk()
    app = MapFlipperApp(root)
    root.mainloop()
