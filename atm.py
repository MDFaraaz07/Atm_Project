import tkinter as tk
from tkinter import ttk, messagebox, font
import sqlite3
import hashlib
from datetime import datetime
from tkcalendar import DateEntry
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# ======================
# CONSTANTS & CONFIG
# ======================
COLORS = {
    "primary": "#2A2E45",
    "secondary": "#6C63FF",
    "accent": "#FF6584",
    "background": "#F8F9FF",
    "surface": "#FFFFFF",
    "text": "#2B2B2B",
    "success": "#4CAF50",
    "warning": "#FFC107",
    "error": "#F44336"
}

FONTS = {
    "header": ("Roboto", 24, "bold"),
    "subheader": ("Roboto", 16),
    "body": ("Roboto", 12),
    "button": ("Roboto", 12, "bold")
}

# ======================
# DATABASE SETUP
# ======================
def init_database():
    conn = sqlite3.connect('atm.db')
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS users
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 name TEXT NOT NULL,
                 pin_hash TEXT NOT NULL,
                 balance REAL DEFAULT 0,
                 account_type TEXT DEFAULT 'Savings',
                 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                 status TEXT DEFAULT 'Active')''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS transactions
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 user_id INTEGER,
                 type TEXT NOT NULL,
                 amount REAL NOT NULL,
                 timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                 related_account INTEGER,
                 FOREIGN KEY(user_id) REFERENCES users(id))''')
    
    conn.commit()
    return conn

conn = init_database()

# ======================
# CORE CLASSES
# ======================
class User:
    def __init__(self, user_id):
        self.user_id = user_id
        self._balance = None
        self.account_type = None
        self._load_user_data()

    def _load_user_data(self):
        c = conn.cursor()
        c.execute("SELECT balance, account_type FROM users WHERE id=?", (self.user_id,))
        result = c.fetchone()
        if result:
            self._balance = result[0]
            self.account_type = result[1]

    @property
    def balance(self):
        return self._balance if self._balance is not None else 0.0

    def update_balance(self, amount):
        self._balance += amount
        c = conn.cursor()
        c.execute("UPDATE users SET balance=? WHERE id=?", (self.balance, self.user_id))
        conn.commit()

    def create_transaction(self, transaction_type, amount, related_account=None):
        c = conn.cursor()
        c.execute('''INSERT INTO transactions 
                     (user_id, type, amount, related_account)
                     VALUES (?, ?, ?, ?)''',
                  (self.user_id, transaction_type, amount, related_account))
        conn.commit()
    
    def get_transaction_history(self):
        """Get recent transactions"""
        c = conn.cursor()
        c.execute('''SELECT timestamp, type, amount, related_account 
                     FROM transactions 
                     WHERE user_id=? 
                     ORDER BY timestamp DESC 
                     LIMIT 100''', (self.user_id,))
        return c.fetchall()

class ATMController:
    @staticmethod
    def authenticate(account_id, pin):
        c = conn.cursor()
        pin_hash = hashlib.sha256(pin.encode()).hexdigest()
        c.execute("SELECT id FROM users WHERE id=? AND pin_hash=?", (account_id, pin_hash))
        return c.fetchone()

    @staticmethod
    def create_account(name, pin, initial_deposit=0):
        c = conn.cursor()
        pin_hash = hashlib.sha256(pin.encode()).hexdigest()
        c.execute("INSERT INTO users (name, pin_hash, balance) VALUES (?, ?, ?)",
                  (name, pin_hash, initial_deposit))
        conn.commit()
        return c.lastrowid

# ======================
# GUI APPLICATION
# ======================
class ModernATM(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("NexusBank Pro")
        self.geometry("1280x800")
        self.current_user = None
        self.configure_styles()
        self.show_auth_screen()

    def configure_styles(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        self.style.configure('TButton', font=FONTS["button"], borderwidth=0,
                           padding=10, background=COLORS["secondary"],
                           foreground="white")
        self.style.map('TButton',
                      background=[('active', COLORS["primary"])])
        
        self.style.configure('Header.TLabel', font=FONTS["header"],
                           background=COLORS["background"],
                           foreground=COLORS["primary"])
        
        self.style.configure('Card.TFrame', background=COLORS["surface"],
                           relief='flat', borderwidth=0)
    
    def clear_frame(self):
        for widget in self.winfo_children():
            widget.destroy()

    def show_auth_screen(self):
        self.clear_frame()
        frame = ttk.Frame(self, style='Card.TFrame')
        frame.place(relx=0.5, rely=0.5, anchor='center', width=400, height=500)
        
        ttk.Label(frame, text="💎 NexusBank", style='Header.TLabel').pack(pady=40)
        
        self.acc_entry = self.create_input_field(frame, "Account Number")
        self.pin_entry = self.create_input_field(frame, "PIN", is_password=True)
        
        ttk.Button(frame, text="Sign In", command=self.authenticate).pack(pady=20, fill='x', padx=50)
        ttk.Button(frame, text="Create Account", command=self.show_create_account).pack(pady=10, fill='x', padx=50)

    def create_input_field(self, parent, placeholder, is_password=False):
        container = ttk.Frame(parent)
        container.pack(fill='x', pady=10, padx=50)
        
        entry = ttk.Entry(container, font=FONTS["body"], show="•" if is_password else "")
        entry.pack(fill='x', ipady=8)
        entry.insert(0, placeholder)
        
        entry.bind("<FocusIn>", lambda e: entry.delete(0, 'end') if entry.get() == placeholder else None)
        entry.bind("<FocusOut>", lambda e: entry.insert(0, placeholder) if not entry.get() else None)
        return entry

    def authenticate(self):
        account_id = self.acc_entry.get()
        pin = self.pin_entry.get()
        
        if result := ATMController.authenticate(account_id, pin):
            self.current_user = User(result[0])
            self.show_dashboard()
        else:
            messagebox.showerror("Error", "Invalid credentials")
    
    def show_create_account(self):
        dialog = tk.Toplevel(self)
        dialog.title("Create New Account")

        ttk.Label(dialog, text="Full Name:").pack(pady=5)
        name_entry = ttk.Entry(dialog)
        name_entry.pack(pady=5)

        ttk.Label(dialog, text="4-digit PIN:").pack(pady=5)
        pin_entry = ttk.Entry(dialog, show="*")
        pin_entry.pack(pady=5)

        ttk.Label(dialog, text="Initial Deposit:").pack(pady=5)
        deposit_entry = ttk.Entry(dialog)
        deposit_entry.pack(pady=5)

        ttk.Button(dialog, text="Create Account", 
                  command=lambda: self.process_account_creation(
                      name_entry.get(),
                      pin_entry.get(),
                      deposit_entry.get(),
                      dialog
                  )).pack(pady=20)

    def process_account_creation(self, name, pin, deposit, dialog):
        if not name or len(name.strip()) < 3:
            messagebox.showerror("Error", "Please enter a valid name (min 3 characters)")
            return
        
        if not pin.isdigit() or len(pin) != 4:
            messagebox.showerror("Error", "PIN must be 4 digits")
            return
        
        try:
            deposit = float(deposit) if deposit else 0.0
            if deposit < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Invalid deposit amount")
            return
        
        account_id = ATMController.create_account(name, pin, deposit)
        messagebox.showinfo("Success", 
                           f"Account created successfully!\nYour Account ID: {account_id}")
        dialog.destroy()

    def show_dashboard(self):
        self.clear_frame()
        
        header = ttk.Frame(self, style='Card.TFrame')
        header.pack(fill='x', padx=20, pady=10)
        ttk.Label(header, text=f"Account #{self.current_user.user_id}", 
                 style='Header.TLabel').pack(side='left', padx=20)
        ttk.Button(header, text="Logout", command=self.show_auth_screen).pack(side='right', padx=20)

        main_frame = ttk.Frame(self)
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)

        action_frame = ttk.Frame(main_frame, style='Card.TFrame')
        action_frame.pack(side='left', fill='y', padx=10, pady=10)

        actions = [
            ("💰 Balance", self.show_balance),
            ("💸 Withdraw", self.show_withdraw),
            ("📥 Deposit", self.show_deposit),
            ("🔀 Transfer", self.show_transfer),
            ("📊 History", self.show_history)
        ]

        for text, cmd in actions:
            ttk.Button(action_frame, text=text, command=cmd, width=15).pack(pady=5, padx=10)

        overview_frame = ttk.Frame(main_frame, style='Card.TFrame')
        overview_frame.pack(side='left', fill='both', expand=True, padx=10, pady=10)

        ttk.Label(overview_frame, text="Current Balance", 
                 font=FONTS["subheader"]).pack(anchor='w', padx=20, pady=10)
        ttk.Label(overview_frame, text=f"₹{self.current_user.balance:.2f}", 
                 font=("Roboto", 36, "bold"), foreground=COLORS["secondary"]).pack(pady=20)

        ttk.Label(overview_frame, text="Recent Transactions", 
                 font=FONTS["subheader"]).pack(anchor='w', padx=20)

        cols = ('Date', 'Type', 'Amount', 'Account')
        tree = ttk.Treeview(overview_frame, columns=cols, show='headings', height=5)

        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=120)

        vsb = ttk.Scrollbar(overview_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)

        tree.pack(side='left', fill='both', expand=True, padx=20, pady=10)
        vsb.pack(side='right', fill='y')

        transactions = self.current_user.get_transaction_history()
        for trans in transactions[-5:]:
            tree.insert('', 'end', values=trans)

    def show_balance(self):
        messagebox.showinfo("Balance", f"Current Balance: ₹{self.current_user.balance:.2f}")

    def show_deposit(self):
        self.show_transaction_interface("Deposit Funds", COLORS["success"])

    def show_withdraw(self):
        self.show_transaction_interface("Withdraw Cash", COLORS["warning"])

    def show_transfer(self):
        self.clear_frame()
        
        header = ttk.Frame(self, style='Card.TFrame')
        header.pack(fill='x', padx=20, pady=10)
        ttk.Label(header, text="Transfer Funds", style='Header.TLabel').pack(side='left', padx=20)
        ttk.Button(header, text="Back", command=self.show_dashboard).pack(side='right', padx=20)

        main_frame = ttk.Frame(self)
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)

        form_frame = ttk.Frame(main_frame, style='Card.TFrame')
        form_frame.pack(pady=20, padx=20, ipadx=20, ipady=20)

        ttk.Label(form_frame, text="Recipient Account ID:").grid(row=0, column=0, pady=10)
        recipient_entry = ttk.Entry(form_frame)
        recipient_entry.grid(row=0, column=1, pady=10)

        ttk.Label(form_frame, text="Amount:").grid(row=1, column=0, pady=10)
        amount_entry = ttk.Entry(form_frame)
        amount_entry.grid(row=1, column=1, pady=10)

        ttk.Button(form_frame, text="Transfer", 
                 command=lambda: self.process_transfer(
                     recipient_entry.get(),
                     amount_entry.get()
                 )).grid(row=2, columnspan=2, pady=20)

    def process_transfer(self, recipient_id, amount_str):
        try:
            amount = float(amount_str)
            if amount <= 0:
                raise ValueError
                
            if self.current_user.balance < amount:
                messagebox.showerror("Error", "Insufficient funds")
                return
                
            c = conn.cursor()
            c.execute("SELECT id FROM users WHERE id=?", (recipient_id,))
            if not c.fetchone():
                messagebox.showerror("Error", "Recipient account not found")
                return

            self.current_user.update_balance(-amount)
            self.current_user.create_transaction('Transfer', -amount, recipient_id)
            
            recipient = User(recipient_id)
            recipient.update_balance(amount)
            recipient.create_transaction('Transfer', amount, self.current_user.user_id)
            
            messagebox.showinfo("Success", f"Transferred ₹{amount:.2f} to account {recipient_id}")
            self.show_dashboard()
            
        except ValueError:
            messagebox.showerror("Error", "Invalid amount entered")

    def show_history(self):
        self.clear_frame()
        
        header = ttk.Frame(self, style='Card.TFrame')
        header.pack(fill='x', padx=20, pady=10)
        ttk.Label(header, text="Transaction History", style='Header.TLabel').pack(side='left', padx=20)
        ttk.Button(header, text="Back", command=self.show_dashboard).pack(side='right', padx=20)

        main_frame = ttk.Frame(self)
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)

        filter_frame = ttk.Frame(main_frame)
        filter_frame.pack(fill='x', pady=10)

        ttk.Label(filter_frame, text="From:").pack(side='left')
        start_date = DateEntry(filter_frame)
        start_date.pack(side='left', padx=5)

        ttk.Label(filter_frame, text="To:").pack(side='left', padx=10)
        end_date = DateEntry(filter_frame)
        end_date.pack(side='left', padx=5)

        ttk.Button(filter_frame, text="Filter", 
                 command=lambda: self.update_history(
                     start_date.get_date(),
                     end_date.get_date()
                 )).pack(side='left', padx=10)

        cols = ('Date', 'Type', 'Amount', 'Account')
        tree = ttk.Treeview(main_frame, columns=cols, show='headings')

        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=150)

        vsb = ttk.Scrollbar(main_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)

        tree.pack(side='left', fill='both', expand=True)
        vsb.pack(side='right', fill='y')

        self.update_history(tree)

    def update_history(self, tree, start_date=None, end_date=None):
        tree.delete(*tree.get_children())
        transactions = self.current_user.get_transaction_history()
        for trans in transactions:
            tree.insert('', 'end', values=trans)

    def show_transaction_interface(self, title, color):
        self.clear_frame()
        
        header = ttk.Frame(self)
        header.pack(fill='x', pady=20, padx=40)
        ttk.Label(header, text=title, style='Header.TLabel').pack(side='left')
        ttk.Button(header, text="Back", command=self.show_dashboard).pack(side='right')
        
        content = ttk.Frame(self)
        content.pack(fill='both', expand=True, padx=40, pady=20)
        
        ttk.Label(content, text="Enter Amount:", font=FONTS["subheader"]).pack(pady=20)
        amount_entry = ttk.Entry(content, font=("Roboto", 24), justify='center')
        amount_entry.pack(pady=20, ipady=10)
        
        keypad = ttk.Frame(content)
        keypad.pack(pady=20)
        
        buttons = [
            ('7', '8', '9'),
            ('4', '5', '6'),
            ('1', '2', '3'),
            ('00', '0', '⌫')
        ]
        
        for row in buttons:
            row_frame = ttk.Frame(keypad)
            row_frame.pack()
            for btn in row:
                ttk.Button(row_frame, text=btn, width=4,
                          command=lambda b=btn: self.update_amount(amount_entry, b)).pack(side='left', padx=5, pady=5)
        
        ttk.Button(content, text="Confirm", style='TButton',
                  command=lambda: self.process_transaction(title.split()[0].lower(), amount_entry.get())).pack(pady=20)
        ttk.Button(content, text="Cancel", command=self.show_dashboard).pack(pady=10)

    def process_transaction(self, transaction_type, amount_str):
        try:
            amount = float(amount_str)
            if amount <= 0:
                raise ValueError
                
            if transaction_type == "withdraw" and self.current_user.balance < amount:
                messagebox.showerror("Error", "Insufficient funds")
                return
                
            self.current_user.update_balance(amount if transaction_type == "deposit" else -amount)
            self.current_user.create_transaction(transaction_type.capitalize(), 
                                                amount if transaction_type == "deposit" else -amount)
            messagebox.showinfo("Success", f"{transaction_type.capitalize()} successful!\nNew Balance: ₹{self.current_user.balance:.2f}")
            self.show_dashboard()
            
        except ValueError:
            messagebox.showerror("Error", "Invalid amount entered")

    def update_amount(self, entry, value):
        if value == '⌫':
            current = entry.get()[:-1]
            entry.delete(0, 'end')
            entry.insert(0, current)
        else:
            entry.insert('end', value)

if __name__ == "__main__":
    app = ModernATM()
    app.mainloop()