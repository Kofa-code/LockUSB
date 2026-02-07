import os
import sys
import ctypes
import subprocess
import customtkinter as ctk
from tkinter import messagebox

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# Get the correct path for the icon
if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS  # PyInstaller temp folder
else:
    base_path = os.path.abspath(".")

icon_path = os.path.join(base_path, "lockusb.ico")

def get_filtered_drives():
    drives = []
    bitmask = ctypes.windll.kernel32.GetLogicalDrives()
    
    for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
        if bitmask & 1:
            drive_path = f"{letter}:\\"
            drive_type = ctypes.windll.kernel32.GetDriveTypeW(drive_path)
            
            # Skip unwanted drive types
            if drive_type in (4, 5, 6):  # Skip network, CD-ROM, and RAM disks
                continue
            if letter in ('A', 'B'):     # Skip floppy disks
                continue
                
            # Check if drive is accessible
            try:
                os.listdir(drive_path)
                drives.append((drive_path, drive_type))
            except:
                continue
        bitmask >>= 1
    return drives

def is_write_protected(drive):
    test_path = os.path.join(drive, "test.txt")
    try:
        with open(test_path, 'w') as f:
            f.write("test")
        os.remove(test_path)
        return False
    except PermissionError:
        return True
    except:
        return False

class DriveProtectionApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("LockUSB")
        self.geometry("450x350")
        self.resizable(False, False)
        self.iconbitmap(icon_path)
        self.selected_drive = None
        self.selected_frame = None

        # Main UI components
        self.create_widgets()
        self.refresh_drives_list()

    def create_widgets(self):
        self.top_frame = ctk.CTkFrame(self, bg_color="transparent")
        self.top_frame.pack(fill="x", padx=15, pady=10)

        # Label
        self.label = ctk.CTkLabel(self.top_frame, text="Available Storage Drives", font=("Arial", 14, "bold"))
        self.label.pack(side="left", padx=10)

        # About app button
        self.protect_btn = ctk.CTkButton(
            self.top_frame, 
            text="About",
            command=self.about_app,
            width=70,
        )
        self.protect_btn.pack(side="right", padx=10, pady=10)


        # Scrollable frame for drives list
        self.scroll_frame = ctk.CTkScrollableFrame(self, width=400, height=200)
        self.scroll_frame.pack()

        # Protection buttons
        self.protect_btn = ctk.CTkButton(
            self, 
            text="Enable Write\n  Protection",
            command=self.enable_protection,
            fg_color="#2aa52c",
            hover_color="#207a22"
        )
        self.protect_btn.pack(side="left", padx=40, pady=10)

        self.unprotect_btn = ctk.CTkButton(
            self,
            text="Remove Write\n  Protection",
            command=self.disable_protection,
            fg_color="#a52a2a",
            hover_color="#7a2020"
        )
        self.unprotect_btn.pack(side="right", padx=40, pady=10)

    def refresh_drives_list(self):
        # Clear existing entries
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        # Get current drives
        drives = get_filtered_drives()
        if not drives:
            label = ctk.CTkLabel(self.scroll_frame, text="No compatible drives detected")
            label.pack()
            return

        # Create drive entries
        for idx, (drive_path, drive_type) in enumerate(drives):
            frame = ctk.CTkFrame(self.scroll_frame, height=35, corner_radius=5)
            frame.pack(fill="x", pady=2)

            # Store drive info
            frame.drive = drive_path
            frame.is_protected = is_write_protected(drive_path)

            # Configure grid
            frame.grid_columnconfigure((0, 1, 2), weight=1)

            # Labels
            ctk.CTkLabel(frame, text=f"{idx+1}", width=50).grid(row=0, column=0, padx=10)
            ctk.CTkLabel(frame, text=drive_path, width=200).grid(row=0, column=1, padx=10)
            status = "Protected" if frame.is_protected else "Not Protected"
            status_color = "#2aa52c" if frame.is_protected else "#a52a2a"
            ctk.CTkLabel(frame, text=status, text_color=status_color, width=100).grid(row=0, column=2, padx=10)

            # Bind click events
            frame.bind("<Button-1>", lambda e, f=frame: self.select_drive(f))
            for child in frame.winfo_children():
                child.bind("<Button-1>", lambda e, f=frame: self.select_drive(f))

    def select_drive(self, frame):
        if self.selected_frame == frame:
            if self.selected_frame.winfo_exists():
                frame.configure(fg_color="transparent")
            self.selected_frame = None
            self.selected_drive = None
        else:
            if self.selected_frame and self.selected_frame.winfo_exists():
                self.selected_frame.configure(fg_color="transparent")
            frame.configure(fg_color="#1f6aa5")
            self.selected_frame = frame
            self.selected_drive = frame.drive

    def enable_protection(self):
        if not self.selected_drive:
            messagebox.showwarning("LockUSB", "Please select a drive first!")
            return
        
        drive_letter = self.selected_drive[0]
        response = messagebox.askyesno("LockUSB", f"Enable Write Protection on Drive: {drive_letter}\\")
        if response:
            script = f"""
            select volume {drive_letter}
            attributes volume set readonly
            exit
            """
            
            if self.execute_diskpart(script):
                messagebox.showinfo("LockUSB", "Write protection enabled successfully!")
                self.refresh_drives_list()
            else:
                messagebox.showerror("LockUSB", "Failed to enable write protection!\nRun as Administrator.")
        else:
            return

    def disable_protection(self):
        if not self.selected_drive:
            messagebox.showwarning("LockUSB", "Please select a drive first!")
            return
        
        drive_letter = self.selected_drive[0]
        response = messagebox.askyesno("LockUSB", f"Remove Write Protection from Drive: {drive_letter}\\")
        if response:
            script = f"""
            select volume {drive_letter}
            attributes volume clear readonly
            exit
            """
            
            if self.execute_diskpart(script):
                messagebox.showinfo("LockUSB", "Write protection removed successfully!")
                self.refresh_drives_list()
            else:
                messagebox.showerror("LockUSB", "Failed to remove write protection!\nRun as Administrator.")
        else:
            return

    def execute_diskpart(self, script):
        try:
            with open("temp_script.txt", "w") as f:
                f.write(script.strip())
            
            result = subprocess.run(
                ["diskpart", "/s", "temp_script.txt"],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
                timeout=10
            )
            return "successfully" in result.stdout
        except:
            return False
        finally:
            if os.path.exists("temp_script.txt"):
                os.remove("temp_script.txt")

    def about_app(self):
        for widget in self.winfo_children():
            widget.destroy()
        
        self.top_frame = ctk.CTkFrame(self, bg_color="transparent")
        self.top_frame.pack(fill="x", padx=15, pady=10)

        self.label = ctk.CTkLabel(self.top_frame, text="About LockUSB", font=("Arial", 14, "bold"))
        self.label.pack(side="left", padx=10)

        # About app button
        self.protect_btn = ctk.CTkButton(
            self.top_frame, 
            text="Back",
            command=self.back_to_main,
            width=70,
        )
        self.protect_btn.pack(side="right", padx=10, pady=10)

        self.scroll_frame = ctk.CTkScrollableFrame(self, width=400, height=250)
        self.scroll_frame.pack()

        content = """LockUSB - Version 1.0

Features:
- View available storage drives
- Enable/disable write protection
- Simple one-click interface
- Drive status monitoring

Developed using Python and customtkinter
Requires Windows and administrator privileges

Warning: Improper use may lead to data loss.
Always backup important data before modifying drive settings.

🔹 License: Free
🔹 Date Developed: Feb 2025
🔹 Developer: David Kofa
🔹 Email: davidkofa07@gmail.com"""

        ctk.CTkLabel(self.scroll_frame, text=content, justify="left",
                    font=("Arial", 12)).pack(pady=20, padx=20)

    def back_to_main(self):
        for widget in self.winfo_children():
            widget.destroy()

        # Main UI components
        self.create_widgets()
        self.refresh_drives_list()

if __name__ == "__main__":
    if ctypes.windll.shell32.IsUserAnAdmin():
        app = DriveProtectionApp()
        app.mainloop()
    else:
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, None, 1
        )