import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import re
import os
import math

# --- Regular Expressions ---
entity_origin_re = re.compile(r'^\s*("origin")\s*("(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)")\s*$')
entity_angle_re = re.compile(r'^\s*("angle")\s*("(-?\d+)")\s*$')
entity_angles_re = re.compile(r'^\s*("angles")\s*("(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)")\s*$')
# Added: Regex for classname
entity_classname_re = re.compile(r'^\s*("classname")\s*("([^"]*)")\s*$')
# Added: Regex for message and map keys (match content inside quotes)
entity_message_re = re.compile(r'^\s*("message")\s*("([^"]*)")\s*$')
entity_map_re = re.compile(r'^\s*("map")\s*("([^"]*)")\s*$')
# Plane definition (same as before)
plane_re = re.compile(
    r'^\s*'
    r'\(\s*(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s*\)\s*'
    r'\(\s*(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s*\)\s*'
    r'\(\s*(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s*\)\s*'
    r'([^\s]+)\s+'
    r'(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s+'
    r'(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s*$'
)

# Helper to format numbers
def format_num(val):
    try:
        f_val = float(val)
        if f_val == int(f_val): return str(int(f_val))
        else: return "{:.4f}".format(f_val).rstrip('0').rstrip('.')
    except ValueError: return str(val)

# Normalize angle
def normalize_angle(angle):
    return angle % 360

def process_map_file(input_path, output_path, flip_x, flip_y, flip_z):
    if not (flip_x or flip_y or flip_z):
        messagebox.showerror("Error", "Please select at least one axis to flip.")
        return False

    try:
        with open(input_path, 'r') as infile, open(output_path, 'w') as outfile:
            brace_level = 0
            in_brush = False
            current_classname = None # Added: Track current entity classname
            flip_axis_count = sum([flip_x, flip_y, flip_z])
            reverse_winding = (flip_axis_count % 2 != 0)

            line_num = 0
            for line in infile:
                line_num += 1
                stripped_line = line.strip()
                processed_line = line # Default to original line

                # Preserve empty/comment lines
                if not stripped_line or stripped_line.startswith("//"):
                    outfile.write(processed_line)
                    continue

                # Track brace levels and reset classname on entity start/end
                if stripped_line == "{":
                    brace_level += 1
                    if brace_level == 1: current_classname = None # Reset on new entity
                    if brace_level == 2: in_brush = True
                    outfile.write(processed_line)
                    continue
                elif stripped_line == "}":
                    if brace_level == 2: in_brush = False
                    # Reset classname *after* processing potential end brace of level 1 entity
                    # No, reset should happen when brace_level drops *to* 0, handled implicitly by next loop
                    brace_level = max(0, brace_level - 1)
                    if brace_level == 0: current_classname = None # Exiting top-level entity
                    outfile.write(processed_line)
                    continue

                line_processed = False # Flag to check if we handled the line

                # --- Process Entity Properties (when not inside a brush, level 1) ---
                if not in_brush and brace_level == 1:
                    # --- Get Classname (should be the first property) ---
                    if current_classname is None: # Only check if not already found
                         classname_match = entity_classname_re.match(line)
                         if classname_match:
                             current_classname = classname_match.group(3)
                             # Don't set line_processed=True yet, just store classname
                             # and let the original line be written below if nothing else matches.

                    # --- Worldspawn Message ---
                    if current_classname == "worldspawn":
                        message_match = entity_message_re.match(line)
                        if message_match:
                            key = message_match.group(1)
                            value = message_match.group(3)
                            new_value = value + " Flipped"
                            processed_line = f'	{key} "{new_value}"\n' # Use tab for standard formatting
                            line_processed = True

                    # --- Trigger_Changelevel Map ---
                    elif current_classname == "trigger_changelevel":
                         map_match = entity_map_re.match(line)
                         if map_match:
                             key = map_match.group(1)
                             value = map_match.group(3)
                             new_value = value + "_flipped"
                             processed_line = f'	{key} "{new_value}"\n' # Use tab
                             line_processed = True

                    # --- Origin ---
                    # Check only if not already processed above
                    if not line_processed:
                        origin_match = entity_origin_re.match(line)
                        if origin_match:
                            key = origin_match.group(1)
                            x, y, z = map(float, [origin_match.group(3), origin_match.group(4), origin_match.group(5)])
                            new_x, new_y, new_z = (-x if flip_x else x, -y if flip_y else y, -z if flip_z else z)
                            processed_line = f'	{key} "{format_num(new_x)} {format_num(new_y)} {format_num(new_z)}"\n'
                            line_processed = True

                    # --- Angle ---
                    if not line_processed:
                        angle_match = entity_angle_re.match(line)
                        if angle_match:
                            key = angle_match.group(1)
                            current_angle = int(angle_match.group(3))
                            new_angle = float(current_angle)
                            if current_angle < 0: # Up/Down
                                if flip_z: new_angle = -1.0 if current_angle == -2 else -2.0
                            else: # Direction/Facing
                                if flip_x: new_angle = 180.0 - new_angle
                                if flip_y: new_angle = -new_angle
                                new_angle = normalize_angle(new_angle)
                            processed_line = f'	{key} "{int(round(new_angle))}"\n'
                            line_processed = True

                    # --- Angles (Pitch Yaw Roll) ---
                    if not line_processed:
                        angles_match = entity_angles_re.match(line)
                        if angles_match:
                            key = angles_match.group(1)
                            pitch, yaw, roll = map(float, [angles_match.group(3), angles_match.group(4), angles_match.group(5)])
                            new_pitch, new_yaw, new_roll = pitch, yaw, roll
                            if flip_x: new_yaw, new_roll = 180.0 - new_yaw, -new_roll
                            if flip_y: new_yaw, new_roll = -new_yaw, -new_roll
                            if flip_z: new_pitch = -new_pitch
                            new_yaw = normalize_angle(new_yaw)
                            processed_line = f'	{key} "{format_num(new_pitch)} {format_num(new_yaw)} {format_num(new_roll)}"\n'
                            line_processed = True

                # --- Process Brush Plane (when inside a brush, level 2) ---
                elif in_brush and brace_level == 2:
                    plane_match = plane_re.match(line)
                    if plane_match:
                        try:
                            # (Vertex and Texture processing logic - unchanged)
                            v1x, v1y, v1z = map(float, plane_match.group(1, 2, 3))
                            v2x, v2y, v2z = map(float, plane_match.group(4, 5, 6))
                            v3x, v3y, v3z = map(float, plane_match.group(7, 8, 9))
                            tex_name = plane_match.group(10)
                            off_x, off_y, rot = map(float, plane_match.group(11, 12, 13))
                            scale_x, scale_y = map(float, plane_match.group(14, 15))
                            # Flip Vertices
                            nv1x, nv1y, nv1z = (-v1x if flip_x else v1x, -v1y if flip_y else v1y, -v1z if flip_z else v1z)
                            nv2x, nv2y, nv2z = (-v2x if flip_x else v2x, -v2y if flip_y else v2y, -v2z if flip_z else v2z)
                            nv3x, nv3y, nv3z = (-v3x if flip_x else v3x, -v3y if flip_y else v3y, -v3z if flip_z else v3z)
                            fmt_v = lambda x,y,z: " ".join(map(format_num, [x,y,z]))
                            v1_str, v2_str, v3_str = fmt_v(nv1x,nv1y,nv1z), fmt_v(nv2x,nv2y,nv2z), fmt_v(nv3x,nv3y,nv3z)
                            # Flip Texture Params
                            new_rot = -rot
                            new_off_x = -off_x if flip_x else off_x
                            new_off_y = -off_y if flip_y else off_y
                            new_scale_x, new_scale_y = scale_x, scale_y
                            tex_info_str = (f"{tex_name} {format_num(new_off_x)} {format_num(new_off_y)} "
                                            f"{format_num(new_rot)} {format_num(new_scale_x)} {format_num(new_scale_y)}")
                            # Reconstruct Line
                            if reverse_winding: processed_line = f" ( {v1_str} ) ( {v3_str} ) ( {v2_str} ) {tex_info_str}\n"
                            else: processed_line = f" ( {v1_str} ) ( {v2_str} ) ( {v3_str} ) {tex_info_str}\n"
                            line_processed = True # Mark plane line as processed
                        except ValueError as e: print(f"Warning: Plane parse error line {line_num}: {stripped_line}. {e}")
                        except Exception as e: print(f"Warning: Plane process error line {line_num}: {stripped_line}. {e}")

                # Write the (potentially modified) line
                outfile.write(processed_line)

        return True

    except FileNotFoundError:
        messagebox.showerror("Error", f"Input file not found:\n{input_path}")
        return False
    except Exception as e:
        messagebox.showerror("Error", f"An unexpected error occurred:\n{e}")
        import traceback
        traceback.print_exc()
        return False


# --- GUI Setup (Identical GUI Code as before) ---
class MapFlipperApp:
    def __init__(self, master):
        self.master = master
        master.title("Quake .map Flipper")
        master.geometry("500x310") # Slightly taller for notes

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
        self.status_label = ttk.Label(master, text="Ready. Remember to test the flipped map.")
        self.status_label.pack(pady=(0,5))
        self.note_label = ttk.Label(master, text="Note: Texture/Angle flipping is heuristic. Message/Map names updated.")
        self.note_label.pack(pady=(0,5))

        process_button = ttk.Button(master, text="Flip Map", command=self.run_flip)
        process_button.pack(pady=5)

    def browse_input(self):
        filename = filedialog.askopenfilename(title="Select Quake Map File", filetypes=(("Quake Map Files", "*.map"), ("All Files", "*.*")))
        if filename:
            self.input_path.set(filename)
            if not self.output_path.get():
                base, ext = os.path.splitext(filename)
                self.output_path.set(f"{base}_flipped{ext}")

    def browse_output(self):
        filename = filedialog.asksaveasfilename(title="Save Flipped Quake Map File As...", filetypes=(("Quake Map Files", "*.map"), ("All Files", "*.*")), defaultextension=".map")
        if filename:
            self.output_path.set(filename)

    def run_flip(self):
        in_file = self.input_path.get()
        out_file = self.output_path.get()
        if not in_file or not out_file:
            messagebox.showerror("Error", "Please specify both input and output files.")
            return

        self.status_label.config(text="Processing...")
        self.note_label.config(text="Note: Texture/Angle flipping is heuristic. Message/Map names updated.")
        self.master.update_idletasks()

        success = process_map_file(in_file, out_file, self.flip_x.get(), self.flip_y.get(), self.flip_z.get())

        if success:
            final_msg = f"Map successfully flipped!\nOutput saved to:\n{out_file}\n\nWorldspawn message and changelevel maps were updated.\nRemember to test thoroughly!"
            self.status_label.config(text=f"Success! Output: {out_file}")
            self.note_label.config(text="Remember to test thoroughly.")
            messagebox.showinfo("Success", final_msg)
        else:
             self.status_label.config(text="Processing failed.")
             self.note_label.config(text="See error message / console output.")


if __name__ == "__main__":
    root = tk.Tk()
    app = MapFlipperApp(root)
    root.mainloop()
