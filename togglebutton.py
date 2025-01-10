"""
This module provides utility classes for creating interactive buttons in a Tkinter-based GUI

Classes:
    ToggleButton: A button that toggles between two states, with customizable icons for each state
    ContrButtons: A simple button to choose contrast target image in radio button style
"""
import tkinter as tk
from PIL import Image, ImageTk
from glogger import logger

class ToggleButton:
    """
    A button with toggle functionality that switches between two states, 
    each represented by a different icon
    """
    def __init__(self, frame, ic_path, ic_path_clicked, **kw):
        """
        Initializes the ToggleButton with specified icons and configurations
        """
        self.frame=frame
        self.ic_path=ic_path
        self.ic_path_clicked=ic_path_clicked
        self.h_size=kw.pop("h_size", 40)
        self.v_size=kw.pop("v_size", 40)
        self.compound=kw.pop("compound", "center")
        self.bg=kw.pop("bg", "#222020")
        self.border=kw.pop("border", 0)
        self.command=kw.pop("command", None)
        self.side=kw.pop("side", "left")
        self.padx=kw.pop("padx", 5)
        self.pady=kw.pop("pady", 5)
        self.clicked_state = False

        try:
            self.icon_default=ImageTk.PhotoImage(Image.open(self.ic_path).resize((self.h_size,
                                                                                  self.v_size)))
            self.icon_clicked=ImageTk.PhotoImage(Image.open(self.ic_path_clicked).resize((self.h_size,
                                                                                          self.v_size)))

            self.button = tk.Button(self.frame,
                                    image=self.icon_default,
                                    compound=self.compound,
                                    bg=self.bg,
                                    activebackground=self.bg,
                                    border=self.border,
                                    command=self.command)
            self.button.image = self.icon_default
            self.button.pack(side=self.side, padx=self.padx, pady=self.pady)

            self.button.bind("<Enter>", self.on_hover)
            self.button.bind("<Leave>", self.on_leave)

        except Exception as e:
            self.icon_default=None
            self.icon_clicked = None
            logger.error("Error loading image: %s", e)

    def get_button(self):
        """
        Retrieves the underlying Tkinter Button widget
        """
        return self.button

    def toggle_button_action(self):
        """
        Toggles the button state and updates its appearance accordingly

        Returns:
            bool: The new state of the button (True if clicked, False otherwise)
        """
        self.clicked_state = not self.clicked_state

        if self.clicked_state:
            self.button.configure(image=self.icon_clicked, bg=self.bg, relief="flat")
            self.button.image = self.icon_clicked
        else:
            self.button.configure(image=self.icon_default, bg=self.bg, relief="flat")
            self.button.image = self.icon_default
        return self.clicked_state

    def on_hover(self, event):
        """
        Updates the button appearance when the mouse hovers over it
        """
        if not self.clicked_state:
            self.button.configure(image=self.icon_clicked)
            self.button.image = self.icon_clicked

    def on_leave(self, event):
        """
        Updates the button appearance when the mouse leaves it
        """
        if not self.clicked_state:
            self.button.configure(image=self.icon_default)
            self.button.image = self.icon_default
        else:
            self.button.configure(image=self.icon_clicked)
            self.button.image = self.icon_clicked

class ContrButtons:
    """
    A simple button to choose contrast target image in radio button style
    """
    def __init__(self, frame, **kw):
        """
        Initializes a ContrButtons instance
        """
        self.frame=frame
        self.text=kw.pop("text", "Button")
        self.bg=kw.pop("bg", "gray")
        self.fg=kw.pop("fg", "white")
        self.font=kw.pop("font", ("Arial", 10))
        self.border=kw.pop("border", 0)
        self.command=kw.pop("command", None)
        self.padx=kw.pop("padx", 5)
        self.pady=kw.pop("pady", 5)
        self.compound=kw.pop("compound", "center")
        self.side=kw.pop("side", "left")

        try:
            self.button=tk.Button(self.frame,
                                  text=self.text,
                                  compound=self.compound,
                                  bg=self.bg,
                                  activebackground=self.bg,
                                  border=self.border,
                                  command=self.command,
                                  fg=self.fg,
                                  font=self.font,
                                  relief="flat",
                                  highlightthickness=0)
            self.button.pack(side=self.side, padx=self.padx, pady=self.pady)

        except Exception as e:
            logger.error("Error creating button: %s", e)

    def get_button(self):
        """
        Retrieves the underlying Tkinter Button widget
        """
        return self.button
