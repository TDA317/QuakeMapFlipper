import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import re
import os

# --- Regular Expressions ---
# Matches entity key-value pairs like "origin" "x y z"
entity_origin_re = re.compile(r'^\s*("origin")\s*("(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)")\s*$')

# Matches brush plane definitions: ( v1 ) ( v2 ) ( v3 ) tex offset_x offset_y rotation scale_x scale_y
# Updated to capture texture details more specifically
plane_re = re.compile(
    r'^\s*'
    # Vertex 1 (x, y, z)
    r'\(\s*(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s*\)\s*'
    # Vertex 2 (x, y, z)
    r'\(\s*(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s*\)\s*'
    # Vertex 3 (x, y, z)
    r'\(\s*(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s*\)\s*'
    # Texture Name (allow non-whitespace chars)
    r'([^\s]+)\s+'
    # Offset X, Offset Y, Rotation (float or int)
    r'(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s+'
    # Scale X, Scale Y (float or int)
    r'(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s*$'
)

# Helper to format numbers (int if whole, else float)
def format_num(val):
    """Formats a number, preferring integer representation if possible."""
    try:
        if float(val) == int(float(val)):
            return str(int(float(val)))
        else:
            # Format floats reasonably, avoid excessive precision unless needed
            return "{:.4f}".format(float(val)).rstrip('0').rstrip('.')
    except ValueError:
        return str(val) # Return original string if conversion fails

def process_map_file(input_path, output_path, flip_x, flip_y, flip_z):
    """Reads the input map, flips coordinates/textures, and writes to output path."""
    if not (flip_x or flip_y or flip_z):
        messagebox.showerror("Error", "Please select at least one axis to flip.")
        return False

    try:
        with open(input_path, 'r') as infile, open(output_path, 'w') as outfile:
            brace_level = 0
            in_brush = False
            flip_axis_count = sum([flip_x, flip_y, flip_z])
            reverse_winding = (flip_axis_count % 2 != 0)

            line_num = 0
            for line in infile:
                line_num += 1
                stripped_line = line.strip()

                # Preserve empty/comment lines (basic // check)
                if not stripped_line or stripped_line.startswith("//"):
                    outfile.write(line)
                    continue

                # Track brace levels
                if stripped_line == "{":
                    brace_level += 1
                    if brace_level == 2: # Heuristic: Brush starts at level 2
                        in_brush = True
                    outfile.write(line)
                    continue
                elif stripped_line == "}":
                    if brace_level == 2:
                        in_brush = False
                    brace_level = max(0, brace_level - 1)
                    outfile.write(line)
                    continue

                processed_line = line # Default to original line

                # --- Process Entity Origin ---
                if not in_brush and brace_level == 1:
                    origin_match = entity_origin_re.match(line)
                    if origin_match:
                        key = origin_match.group(1)
                        x, y, z = map(float, [origin_match.group(3), origin_match.group(4), origin_match.group(5)])

                        new_x = -x if flip_x else x
                        new_y = -y if flip_y else y
                        new_z = -z if flip_z else z

                        # Use formatting helper
                        processed_line = f'  "{key}" "{format_num(new_x)} {format_num(new_y)} {format_num(new_z)}"\n'

                # --- Process Brush Plane ---
                elif in_brush and brace_level == 2:
                    plane_match = plane_re.match(line)
                    if plane_match:
                        try:
                            # Extract vertices
                            v1x, v1y, v1z = map(float, plane_match.group(1, 2, 3))
                            v2x, v2y, v2z = map(float, plane_match.group(4, 5, 6))
                            v3x, v3y, v3z = map(float, plane_match.group(7, 8, 9))

                            # Extract texture info
                            tex_name = plane_match.group(10)
                            off_x, off_y, rot = map(float, plane_match.group(11, 12, 13))
                            scale_x, scale_y = map(float, plane_match.group(14, 15))

                            # --- Flip Vertices ---
                            nv1x, nv1y, nv1z = (-v1x if flip_x else v1x, -v1y if flip_y else v1y, -v1z if flip_z else v1z)
                            nv2x, nv2y, nv2z = (-v2x if flip_x else v2x, -v2y if flip_y else v2y, -v2z if flip_z else v2z)
                            nv3x, nv3y, nv3z = (-v3x if flip_x else v3x, -v3y if flip_y else v3y, -v3z if flip_z else v3z)

                            # Format vertices
                            fmt_v = lambda x,y,z: " ".join(map(format_num, [x,y,z]))
                            v1_str = fmt_v(nv1x, nv1y, nv1z)
                            v2_str = fmt_v(nv2x, nv2y, nv2z)
                            v3_str = fmt_v(nv3x, nv3y, nv3z)

                            # --- Flip Texture Parameters (Heuristic) ---
                            new_rot = -rot # Always negate rotation

                            # Flip offsets based on corresponding axis flips
                            new_off_x = -off_x if flip_x else off_x
                            new_off_y = -off_y if flip_y else off_y
                            # Note: flip_z does not affect offsets in this heuristic

                            # Scales remain unchanged
                            new_scale_x = scale_x
                            new_scale_y = scale_y

                            # Format texture parameters
                            tex_info_str = (f"{tex_name} {format_num(new_off_x)} {format_num(new_off_y)} "
                                            f"{format_num(new_rot)} {format_num(new_scale_x)} {format_num(new_scale_y)}")

                            # --- Reconstruct Line ---
                            # Reverse winding order if an odd number of axes are flipped
                            if reverse_winding:
                                processed_line = f"( {v1_str} ) ( {v3_str} ) ( {v2_str} ) {tex_info_str}\n"
                            else:
                                processed_line = f"( {v1_str} ) ( {v2_str} ) ( {v3_str} ) {tex_info_str}\n"

                        except ValueError as e:
                            print(f"Warning: Could not parse plane data on line {line_num}: {line.strip()}. Error: {e}. Skipping line.")
                            # Keep original line if parsing fails
                        except Exception as e:
                            print(f"Warning: Unexpected error processing line {line_num}: {line.strip()}. Error: {e}. Skipping line.")
                            # Keep original line for other unexpected errors

                outfile.write(processed_line)

        return True

    except FileNotFoundError:
        messagebox.showerror("Error", f"Input file not found:\n{input_path}")
        return False
    except Exception as e:
        messagebox.showerror("Error", f"An unexpected error occurred during processing:\n{e}")
        # Consider logging the full traceback here for debugging
        import traceback
        traceback.print_exc()
        return False

# --- GUI Setup (Identical to previous version) ---
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

        # Action Button & Status
        self.status_label = ttk.Label(master, text="Note: Texture flipping is experimental.")
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

        # Update status before processing
        self.status_label.config(text="Processing... Texture flipping is experimental.")
        self.master.update_idletasks()

        success = process_map_file(
            in_file,
            out_file,
            self.flip_x.get(),
            self.flip_y.get(),
            self.flip_z.get()
        )

        if success:
            final_msg = f"Map successfully flipped!\nOutput saved to:\n{out_file}\n\nRemember to check texture alignment in an editor."
            self.status_label.config(text=f"Success! Output: {out_file}. Check textures.")
            messagebox.showinfo("Success", final_msg)
        else:
             self.status_label.config(text="Processing failed. See error message.")
        # No need for explicit error message here as process_map_file shows message boxes


if __name__ == "__main__":
    root = tk.Tk()
    app = MapFlipperApp(root)
    root.mainloop()
