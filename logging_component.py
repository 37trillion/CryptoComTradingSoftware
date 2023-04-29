import tkinter as tk
from datetime import datetime
from styling import *

class Logging(tk.Frame):
    def __init__(self, *args, **kwargs):
        super.__init__(*args, **kwargs)

        self.Logging_Text = tk.Text(self, height=10, width=60, state=tk.DISABLED, bg=BG_COLOR, fg=FG_COLOR, font=GLOBAL_FONT)
        self.Logging_Text.pack(side=tk.TOP)

        def add_log(self, message: str):
            self.Logging_text.configure(state=tk.NORMAL)

            self.Logging_Text.insert("1.0", datetime.utcnow().strftime("%a", '%H', '%m', '%s'), message + "\n")
            self.Logging_text.configure(state=tk.DISABLED)