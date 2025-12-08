import os
import subprocess
import tkinter as tk
from tkinter import filedialog, ttk, messagebox

class FLACVolumeAdjuster:
    def __init__(self, root):
        self.root = root
        self.root.title("FLAC Volume Adjuster")

        self.main_frame = ttk.Frame(root)
        self.main_frame.pack(padx=20, pady=20)

        self.gain_label = ttk.Label(self.main_frame, text="Gain Value (dB):")
        self.gain_label.grid(row=0, column=0, padx=10, pady=10, sticky="e")

        self.gain_entry = ttk.Entry(self.main_frame)
        self.gain_entry.grid(row=0, column=1, padx=10, pady=10)

        self.select_button = ttk.Button(self.main_frame, text="Select FLAC Files", command=self.select_files)
        self.select_button.grid(row=1, column=0, columnspan=2, padx=10, pady=10)

        self.file_list_frame = ttk.Frame(self.main_frame)
        self.file_list_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=10)

        self.file_listbox = tk.Listbox(self.file_list_frame, selectmode=tk.MULTIPLE, width=50)
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH)

        self.scrollbar = ttk.Scrollbar(self.file_list_frame, orient=tk.VERTICAL, command=self.file_listbox.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.file_listbox.config(yscrollcommand=self.scrollbar.set)

        self.adjust_button = ttk.Button(self.main_frame, text="Adjust Selected FLAC Volume", command=self.adjust_flac_volume)
        self.adjust_button.grid(row=3, column=0, columnspan=2, padx=10, pady=10)

    def select_files(self):
        directory = filedialog.askdirectory()
        if directory:
            self.file_listbox.delete(0, tk.END)  # Clear the listbox
            for filename in os.listdir(directory):
                if filename.endswith(".flac"):
                    self.file_listbox.insert(tk.END, os.path.join(directory, filename))

    def adjust_flac_volume(self):
        gain_value = self.gain_entry.get()
        if not gain_value:
            messagebox.showwarning("Input Error", "Please enter a gain value.")
            return

        try:
            gain_value = float(gain_value)
        except ValueError:
            messagebox.showwarning("Input Error", "Gain value must be a number.")
            return

        selected_indices = self.file_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Selection Error", "Please select at least one FLAC file.")
            return

        for index in selected_indices:
            flac_file = self.file_listbox.get(index)
            output_file = flac_file.replace(".flac", "_adjusted.flac")
            # Run the FLAC command to adjust the volume
            subprocess.run(["flac", "--gain", str(gain_value), "--output-file", output_file, flac_file])

        messagebox.showinfo("Volume Adjustment", "Selected FLAC files adjusted successfully!")

if __name__ == "__main__":
    root = tk.Tk()
    app = FLACVolumeAdjuster(root)
    root.mainloop()