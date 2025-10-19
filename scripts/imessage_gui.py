#!/usr/bin/env python3
"""
GUI version of the iMessage History Export Tool
A user-friendly desktop application for exporting iMessage conversations.
"""

import asyncio
import sqlite3
import tkinter as tk
from datetime import datetime, timedelta
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

# Import the core functionality
try:
    from .constants import OUTPUT_DIR, TMP_PATH
    from .format_new import (
        ChunkConfig,
        ChunkStrategy,
        ContactManager,
        DatabaseManager,
        ExportConfig,
        ExportManager,
        MessageProcessor,
    )
    from .utils import is_date_in_future
except ImportError:
    try:
        from constants import OUTPUT_DIR, TMP_PATH
        from format_new import (
            ChunkConfig,
            ChunkStrategy,
            ContactManager,
            DatabaseManager,
            ExportConfig,
            ExportManager,
            MessageProcessor,
        )
        from utils import is_date_in_future
    except ImportError:
        # Fallback defaults if modules aren't found
        from pathlib import Path

        OUTPUT_DIR = Path.home() / "txt_history_output"
        TMP_PATH = Path.home() / "imessage-export"

        def is_date_in_future(date_str: str) -> bool:
            from datetime import datetime

            try:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                return date_obj > datetime.now()
            except ValueError:
                return False


class LoadingWindow(tk.Toplevel):
    """A loading/progress window to show during export."""

    def __init__(self, parent, title: str = "Exporting Messages..."):
        super().__init__(parent)
        self.title(title)
        self.geometry("400x150")
        self.resizable(False, False)

        # Center the window
        self.transient(parent)
        self.grab_set()

        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            self, variable=self.progress_var, maximum=100, mode="indeterminate"
        )
        self.progress_bar.pack(pady=20, padx=20, fill=tk.X)

        # Status label
        self.status_var = tk.StringVar(value="Initializing...")
        self.status_label = tk.Label(
            self, textvariable=self.status_var, font=("Arial", 10)
        )
        self.status_label.pack(pady=10)

        # Cancel button
        self.cancelled = False
        self.cancel_button = tk.Button(
            self, text="Cancel", command=self.cancel, width=10
        )
        self.cancel_button.pack(pady=10)

        # Start progress animation
        self.progress_bar.start()

    def cancel(self):
        """Cancel the export operation."""
        self.cancelled = True
        self.status_var.set("Cancelling...")
        self.cancel_button.config(state=tk.DISABLED)

    def update_status(self, message: str):
        """Update the status message."""
        self.status_var.set(message)

    def close(self):
        """Close the loading window."""
        self.progress_bar.stop()
        self.grab_release()
        self.destroy()


class IMessageExporterGUI:
    """Main GUI application for iMessage export."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("iMessage History Exporter")
        self.root.geometry("600x700")
        self.root.resizable(False, False)

        # Initialize core components
        self.db_manager = None
        self.contact_manager = None
        self.processor = None
        self.export_manager = None

        # Current contacts being managed
        self.contacts = {}

        self.setup_ui()
        self.initialize_components()

    def setup_ui(self):
        """Set up the user interface."""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = tk.Label(
            main_frame, text="iMessage History Exporter", font=("Arial", 16, "bold")
        )
        title_label.pack(pady=(0, 20))

        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 20))

        # Export tab
        self.export_frame = ttk.Frame(self.notebook, padding="20")
        self.notebook.add(self.export_frame, text="Export Messages")

        # Contacts tab
        self.contacts_frame = ttk.Frame(self.notebook, padding="20")
        self.notebook.add(self.contacts_frame, text="Manage Contacts")

        # Settings tab
        self.settings_frame = ttk.Frame(self.notebook, padding="20")
        self.notebook.add(self.settings_frame, text="Settings")

        # Setup each tab
        self.setup_export_tab()
        self.setup_contacts_tab()
        self.setup_settings_tab()

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = tk.Label(
            main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W
        )
        status_bar.pack(fill=tk.X, pady=(10, 0))

        # Bottom buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        self.export_button = tk.Button(
            button_frame,
            text="🚀 Start Export",
            command=self.start_export,
            font=("Arial", 12, "bold"),
            bg="#4CAF50",
            fg="white",
            relief=tk.RAISED,
            borderwidth=2,
        )
        self.export_button.pack(side=tk.RIGHT, padx=(10, 0))

        self.quit_button = tk.Button(
            button_frame,
            text="❌ Quit",
            command=self.root.quit,
            font=("Arial", 10),
            bg="#f44336",
            fg="white",
        )
        self.quit_button.pack(side=tk.RIGHT)

    def setup_export_tab(self):
        """Set up the export tab UI."""
        # Contact selection
        contact_frame = ttk.LabelFrame(
            self.export_frame, text="Select Contacts", padding="10"
        )
        contact_frame.pack(fill=tk.X, pady=(0, 20))

        self.contact_listbox = tk.Listbox(
            contact_frame, selectmode=tk.MULTIPLE, height=4, font=("Arial", 10)
        )
        self.contact_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        scrollbar = ttk.Scrollbar(
            contact_frame, orient=tk.VERTICAL, command=self.contact_listbox.yview
        )
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.contact_listbox.config(yscrollcommand=scrollbar.set)

        # Buttons for contact management
        button_subframe = ttk.Frame(contact_frame)
        button_subframe.pack(side=tk.RIGHT)

        ttk.Button(
            button_subframe, text="Add Contact", command=self.add_contact_dialog
        ).pack(fill=tk.X, pady=(0, 5))
        ttk.Button(
            button_subframe, text="Remove", command=self.remove_selected_contacts
        ).pack(fill=tk.X)

        # Date range selection
        date_frame = ttk.LabelFrame(
            self.export_frame, text="Date Range (Optional)", padding="10"
        )
        date_frame.pack(fill=tk.X, pady=(0, 20))

        # Start date
        start_frame = ttk.Frame(date_frame)
        start_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(start_frame, text="From:").pack(side=tk.LEFT)
        self.start_date_var = tk.StringVar()
        start_entry = ttk.Entry(start_frame, textvariable=self.start_date_var, width=12)
        start_entry.pack(side=tk.LEFT, padx=(10, 0))

        # End date
        end_frame = ttk.Frame(date_frame)
        end_frame.pack(fill=tk.X)

        ttk.Label(end_frame, text="To:").pack(side=tk.LEFT)
        self.end_date_var = tk.StringVar()
        end_entry = ttk.Entry(end_frame, textvariable=self.end_date_var, width=12)
        end_entry.pack(side=tk.LEFT, padx=(10, 0))

        # Set today as default end date
        today = datetime.now().strftime("%Y-%m-%d")
        self.end_date_var.set(today)

        # Quick date buttons
        quick_frame = ttk.Frame(date_frame)
        quick_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(
            quick_frame,
            text="Last 30 Days",
            command=lambda: self.set_quick_date_range(30),
        ).pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(
            quick_frame,
            text="Last 90 Days",
            command=lambda: self.set_quick_date_range(90),
        ).pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(
            quick_frame,
            text="Last Year",
            command=lambda: self.set_quick_date_range(365),
        ).pack(side=tk.LEFT)

        # Export options
        options_frame = ttk.LabelFrame(
            self.export_frame, text="Export Options", padding="10"
        )
        options_frame.pack(fill=tk.X, pady=(0, 20))

        # Output format
        format_frame = ttk.Frame(options_frame)
        format_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(format_frame, text="Format:").pack(side=tk.LEFT)
        self.format_var = tk.StringVar(value="both")
        format_combo = ttk.Combobox(
            format_frame,
            textvariable=self.format_var,
            values=["csv", "txt", "both"],
            state="readonly",
            width=10,
        )
        format_combo.pack(side=tk.LEFT, padx=(10, 0))

        # One-side messages only
        self.one_side_var = tk.BooleanVar()
        one_side_check = ttk.Checkbutton(
            options_frame,
            text="Only contact messages (not my replies)",
            variable=self.one_side_var,
        )
        one_side_check.pack(anchor=tk.W, pady=(0, 10))

        # Chunking options
        chunk_frame = ttk.LabelFrame(
            options_frame, text="Chunking (Optional)", padding="5"
        )
        chunk_frame.pack(fill=tk.X, pady=(0, 10))

        self.chunk_var = tk.StringVar(value="none")

        none_radio = ttk.Radiobutton(
            chunk_frame,
            text="No chunking (single file)",
            variable=self.chunk_var,
            value="none",
        )
        none_radio.pack(anchor=tk.W, pady=(0, 5))

        size_radio = ttk.Radiobutton(
            chunk_frame, text="By size (MB):", variable=self.chunk_var, value="size"
        )
        size_radio.pack(anchor=tk.W)

        self.size_var = tk.StringVar(value="0.05")
        size_entry = ttk.Entry(chunk_frame, textvariable=self.size_var, width=8)
        size_entry.pack(anchor=tk.W, padx=(20, 0))

        count_radio = ttk.Radiobutton(
            chunk_frame,
            text="By message count:",
            variable=self.chunk_var,
            value="count",
        )
        count_radio.pack(anchor=tk.W, pady=(5, 0))

        self.count_var = tk.StringVar(value="1000")
        count_entry = ttk.Entry(chunk_frame, textvariable=self.count_var, width=8)
        count_entry.pack(anchor=tk.W, padx=(20, 0))

        # Refresh contact list
        self.refresh_contact_list()

    def setup_contacts_tab(self):
        """Set up the contacts management tab."""
        # Instructions
        instr_label = tk.Label(
            self.contacts_frame,
            text="Manage your contacts and their phone numbers/emails for iMessage export:",
            font=("Arial", 10, "italic"),
        )
        instr_label.pack(pady=(0, 20))

        # Contact list
        list_frame = ttk.Frame(self.contacts_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        # Create treeview for contacts
        columns = ("name", "phone", "email")
        self.contacts_tree = ttk.Treeview(
            list_frame, columns=columns, show="headings", height=10
        )

        self.contacts_tree.heading("name", text="Name")
        self.contacts_tree.heading("phone", text="Phone")
        self.contacts_tree.heading("email", text="Email")

        self.contacts_tree.column("name", width=150)
        self.contacts_tree.column("phone", width=120)
        self.contacts_tree.column("email", width=150)

        scrollbar = ttk.Scrollbar(
            list_frame, orient=tk.VERTICAL, command=self.contacts_tree.yview
        )
        self.contacts_tree.config(yscrollcommand=scrollbar.set)

        self.contacts_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Buttons
        button_frame = ttk.Frame(self.contacts_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(
            button_frame, text="➕ Add Contact", command=self.add_contact_dialog
        ).pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(
            button_frame, text="✏️ Edit", command=self.edit_selected_contact
        ).pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(
            button_frame, text="🗑️ Remove", command=self.remove_selected_contact
        ).pack(side=tk.LEFT)

        # Load contacts
        self.load_contacts()

    def setup_settings_tab(self):
        """Set up the settings tab."""
        # Database path
        db_frame = ttk.LabelFrame(
            self.settings_frame, text="Database Settings", padding="10"
        )
        db_frame.pack(fill=tk.X, pady=(0, 20))

        ttk.Label(db_frame, text="Database Path:").pack(anchor=tk.W)

        self.db_path_var = tk.StringVar()
        db_entry = ttk.Entry(db_frame, textvariable=self.db_path_var, width=50)
        db_entry.pack(fill=tk.X, pady=(5, 0))

        # Set default database path
        default_db = Path(__file__).parent / "contacts.db"
        self.db_path_var.set(str(default_db))

        ttk.Button(db_frame, text="Browse...", command=self.browse_db_path).pack(
            anchor=tk.W, pady=(5, 0)
        )

        # Output directory
        output_frame = ttk.LabelFrame(
            self.settings_frame, text="Output Settings", padding="10"
        )
        output_frame.pack(fill=tk.X, pady=(0, 20))

        ttk.Label(output_frame, text="Output Directory:").pack(anchor=tk.W)

        self.output_dir_var = tk.StringVar(value=str(OUTPUT_DIR))
        output_entry = ttk.Entry(
            output_frame, textvariable=self.output_dir_var, width=50
        )
        output_entry.pack(fill=tk.X, pady=(5, 0))

        ttk.Button(output_frame, text="Browse...", command=self.browse_output_dir).pack(
            anchor=tk.W, pady=(5, 0)
        )

        # About section
        about_frame = ttk.LabelFrame(self.settings_frame, text="About", padding="10")
        about_frame.pack(fill=tk.X)

        about_text = """
iMessage History Exporter v2.0

A user-friendly tool for exporting your iMessage conversations.

Features:
• Export messages from specific contacts
• Filter by date range
• Multiple output formats (CSV, TXT, or both)
• Automatic chunking for large exports
• Persistent contact management

Note: Requires iMessage Exporter tool to be installed.
        """

        about_label = tk.Label(
            about_frame, text=about_text, justify=tk.LEFT, font=("Arial", 9)
        )
        about_label.pack()

    def initialize_components(self):
        """Initialize the core application components."""
        try:
            db_path = Path(self.db_path_var.get()) if self.db_path_var.get() else None
            self.db_manager = DatabaseManager(db_path)
            self.contact_manager = ContactManager(self.db_manager)
            self.processor = MessageProcessor(self.db_manager)
            self.export_manager = ExportManager(self.db_manager, self.processor)
            self.status_var.set("Ready - Components initialized")
        except Exception as e:
            self.status_var.set(f"Error initializing components: {e}")
            messagebox.showerror(
                "Initialization Error", f"Failed to initialize components:\n\n{e}"
            )

    def refresh_contact_list(self):
        """Refresh the contact list in the export tab."""
        self.contact_listbox.delete(0, tk.END)
        try:
            if self.db_manager and self.db_manager.db_path.exists():
                # Get all contacts from database
                with sqlite3.connect(self.db_manager.db_path) as conn:
                    cursor = conn.execute("SELECT name FROM contacts ORDER BY name")
                    contacts = cursor.fetchall()
                    
                if contacts:
                    for (name,) in contacts:
                        self.contact_listbox.insert(tk.END, name)
                else:
                    self.contact_listbox.insert(tk.END, "No contacts found - add some in the Contacts tab")
            else:
                self.contact_listbox.insert(tk.END, "Database not initialized")
        except Exception as e:
            self.contact_listbox.insert(tk.END, f"Error loading contacts: {e}")

    def load_contacts(self):
        """Load contacts into the contacts management treeview."""
        # Clear existing items
        for item in self.contacts_tree.get_children():
            self.contacts_tree.delete(item)

        try:
            if self.db_manager and self.db_manager.db_path.exists():
                with sqlite3.connect(self.db_manager.db_path) as conn:
                    cursor = conn.execute("SELECT name, phone, email FROM contacts ORDER BY name")
                    contacts = cursor.fetchall()
                    
                if contacts:
                    for name, phone, email in contacts:
                        self.contacts_tree.insert("", tk.END, values=(name, phone or "", email or ""))
                else:
                    self.contacts_tree.insert("", tk.END, values=("No contacts found", "", ""))
            else:
                self.contacts_tree.insert("", tk.END, values=("Database not initialized", "", ""))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load contacts: {e}")

    def add_contact_dialog(self):
        """Show dialog to add a new contact."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Contact")
        dialog.geometry("300x200")
        dialog.resizable(False, False)

        # Center dialog
        dialog.transient(self.root)
        dialog.grab_set()

        # Form fields
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="Name:").pack(anchor=tk.W, pady=(0, 5))
        name_var = tk.StringVar()
        name_entry = ttk.Entry(main_frame, textvariable=name_var, width=30)
        name_entry.pack(fill=tk.X, pady=(0, 10))
        name_entry.focus()

        ttk.Label(main_frame, text="Phone:").pack(anchor=tk.W, pady=(0, 5))
        phone_var = tk.StringVar()
        phone_entry = ttk.Entry(main_frame, textvariable=phone_var, width=30)
        phone_entry.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(main_frame, text="Email (optional):").pack(anchor=tk.W, pady=(0, 5))
        email_var = tk.StringVar()
        email_entry = ttk.Entry(main_frame, textvariable=email_var, width=30)
        email_entry.pack(fill=tk.X)

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))

        def save_contact():
            name = name_var.get().strip()
            phone = phone_var.get().strip()
            email = email_var.get().strip() or None

            if not name:
                messagebox.showerror("Error", "Contact name is required")
                return

            if not phone and not email:
                messagebox.showerror("Error", "At least phone or email is required")
                return

            try:
                self.contact_manager.save_contact(name, phone, email)
                self.load_contacts()
                self.refresh_contact_list()
                dialog.destroy()
                self.status_var.set(f"Contact '{name}' added successfully")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save contact: {e}")

        ttk.Button(button_frame, text="Save", command=save_contact).pack(
            side=tk.RIGHT, padx=(5, 0)
        )
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(
            side=tk.RIGHT
        )

        # Bind Enter key to save
        dialog.bind("<Return>", lambda e: save_contact())

    def edit_contact_dialog(self, current_name: str, current_phone: str, current_email: str):
        """Show dialog to edit an existing contact."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Edit Contact")
        dialog.geometry("300x200")
        dialog.resizable(False, False)

        # Center dialog
        dialog.transient(self.root)
        dialog.grab_set()

        # Form fields
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="Name:").pack(anchor=tk.W, pady=(0, 5))
        name_var = tk.StringVar(value=current_name)
        name_entry = ttk.Entry(main_frame, textvariable=name_var, width=30)
        name_entry.pack(fill=tk.X, pady=(0, 10))
        name_entry.focus()

        ttk.Label(main_frame, text="Phone:").pack(anchor=tk.W, pady=(0, 5))
        phone_var = tk.StringVar(value=current_phone)
        phone_entry = ttk.Entry(main_frame, textvariable=phone_var, width=30)
        phone_entry.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(main_frame, text="Email (optional):").pack(anchor=tk.W, pady=(0, 5))
        email_var = tk.StringVar(value=current_email)
        email_entry = ttk.Entry(main_frame, textvariable=email_var, width=30)
        email_entry.pack(fill=tk.X)

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))

        def save_contact():
            name = name_var.get().strip()
            phone = phone_var.get().strip()
            email = email_var.get().strip() or None

            if not name:
                messagebox.showerror("Error", "Contact name is required")
                return

            if not phone and not email:
                messagebox.showerror("Error", "At least phone or email is required")
                return

            try:
                with sqlite3.connect(self.db_manager.db_path) as conn:
                    # Update the contact
                    conn.execute(
                        "UPDATE contacts SET name = ?, phone = ?, email = ? WHERE name = ?",
                        (name, phone, email, current_name)
                    )
                self.load_contacts()
                self.refresh_contact_list()
                dialog.destroy()
                self.status_var.set(f"Contact '{name}' updated successfully")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to update contact: {e}")

        ttk.Button(button_frame, text="Save", command=save_contact).pack(
            side=tk.RIGHT, padx=(5, 0)
        )
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(
            side=tk.RIGHT
        )

        # Bind Enter key to save
        dialog.bind("<Return>", lambda e: save_contact())

    def remove_selected_contacts(self):
        """Remove selected contacts from the list."""
        selected = self.contact_listbox.curselection()
        if not selected:
            messagebox.showinfo("Info", "Please select contacts to remove")
            return

        if messagebox.askyesno("Confirm", "Remove selected contacts?"):
            try:
                with sqlite3.connect(self.db_manager.db_path) as conn:
                    for index in reversed(selected):
                        contact_name = self.contact_listbox.get(index)
                        conn.execute("DELETE FROM contacts WHERE name = ?", (contact_name,))
                        self.contact_listbox.delete(index)
                self.status_var.set("Contacts removed")
                self.load_contacts()  # Refresh the contacts management tab
            except Exception as e:
                messagebox.showerror("Error", f"Failed to remove contacts: {e}")

    def remove_selected_contact(self):
        """Remove selected contact from the management tab."""
        selected = self.contacts_tree.selection()
        if not selected:
            messagebox.showinfo("Info", "Please select a contact to remove")
            return

        if messagebox.askyesno("Confirm", "Remove selected contact?"):
            try:
                item = selected[0]
                contact_name = self.contacts_tree.item(item, "values")[0]
                with sqlite3.connect(self.db_manager.db_path) as conn:
                    conn.execute("DELETE FROM contacts WHERE name = ?", (contact_name,))
                self.load_contacts()
                self.refresh_contact_list()  # Refresh the export tab too
                self.status_var.set("Contact removed")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to remove contact: {e}")

    def edit_selected_contact(self):
        """Edit the selected contact."""
        selected = self.contacts_tree.selection()
        if not selected:
            messagebox.showinfo("Info", "Please select a contact to edit")
            return

        # Get selected contact info
        item = selected[0]
        values = self.contacts_tree.item(item, "values")
        name, phone, email = values

        # Show edit dialog with pre-filled values
        self.edit_contact_dialog(name, phone, email)

    def browse_db_path(self):
        """Browse for database file."""
        path = filedialog.askopenfilename(
            title="Select Database File",
            filetypes=[("SQLite files", "*.db"), ("All files", "*.*")],
        )
        if path:
            self.db_path_var.set(path)

    def browse_output_dir(self):
        """Browse for output directory."""
        path = filedialog.askdirectory(title="Select Output Directory")
        if path:
            self.output_dir_var.set(path)

    def set_quick_date_range(self, days: int):
        """Set a quick date range."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        self.start_date_var.set(start_date.strftime("%Y-%m-%d"))
        self.end_date_var.set(end_date.strftime("%Y-%m-%d"))

    async def run_export_async(self, loading_window: LoadingWindow):
        """Run the export process asynchronously."""
        try:
            # Get selected contacts
            selected_indices = self.contact_listbox.curselection()
            if not selected_indices:
                loading_window.close()
                messagebox.showerror("Error", "Please select at least one contact")
                return

            contact_names = [self.contact_listbox.get(i) for i in selected_indices]

            # Validate dates
            start_date = self.start_date_var.get().strip() or None
            end_date = self.end_date_var.get().strip() or None

            if start_date and is_date_in_future(start_date):
                loading_window.close()
                messagebox.showerror(
                    "Error", f"Start date {start_date} is in the future"
                )
                return

            if end_date and is_date_in_future(end_date):
                loading_window.close()
                messagebox.showerror("Error", f"End date {end_date} is in the future")
                return

            # Create chunk config
            chunk_config = None
            chunk_type = self.chunk_var.get()

            if chunk_type == "size":
                try:
                    size_mb = float(self.size_var.get())
                    chunk_config = ChunkConfig(ChunkStrategy.SIZE_MB, size_mb)
                except ValueError:
                    loading_window.close()
                    messagebox.showerror("Error", "Invalid size value")
                    return
            elif chunk_type == "count":
                try:
                    count = int(self.count_var.get())
                    chunk_config = ChunkConfig(ChunkStrategy.COUNT, count)
                except ValueError:
                    loading_window.close()
                    messagebox.showerror("Error", "Invalid count value")
                    return

            # Create export config
            config = ExportConfig(
                contact_names=contact_names,
                start_date=start_date,
                end_date=end_date,
                chunk_config=chunk_config,
                only_contact_messages=self.one_side_var.get(),
                output_format=self.format_var.get(),
            )

            # Update loading window
            loading_window.update_status("Fetching messages from iMessage...")

            if loading_window.cancelled:
                loading_window.close()
                return

            # Run export
            success = await self.export_manager.export_messages(config)

            loading_window.close()

            if success:
                messagebox.showinfo(
                    "Success",
                    f"Export completed successfully!\n\nCheck your output directory: {OUTPUT_DIR}",
                )
                self.status_var.set("Export completed successfully")
            else:
                messagebox.showerror(
                    "Error", "Export failed. Check the console for details."
                )

        except Exception as e:
            loading_window.close()
            messagebox.showerror("Error", f"Export failed: {e}")
            self.status_var.set(f"Export failed: {e}")

    def start_export(self):
        """Start the export process."""
        # Reinitialize components in case settings changed
        try:
            db_path = Path(self.db_path_var.get()) if self.db_path_var.get() else None
            self.db_manager = DatabaseManager(db_path)
            self.contact_manager = ContactManager(self.db_manager)
            self.processor = MessageProcessor(self.db_manager)
            self.export_manager = ExportManager(self.db_manager, self.processor)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to initialize components: {e}")
            return

        # Show loading window
        loading_window = LoadingWindow(self.root, "Exporting Messages...")

        # Run export in background thread
        def run_export():
            asyncio.run(self.run_export_async(loading_window))

        import threading

        export_thread = threading.Thread(target=run_export, daemon=True)
        export_thread.start()

    def run(self):
        """Run the GUI application."""
        self.root.mainloop()


def main():
    """Main entry point for the GUI application."""
    app = IMessageExporterGUI()
    app.run()


if __name__ == "__main__":
    main()
