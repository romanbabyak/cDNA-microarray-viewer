"""
This module provides the GUI class for an app

The GUI includes functionalities for displaying 
and combining DNA images, as well as adjusting contrast.
It uses the Tkinter library for the graphical interface
"""
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from scrollableimage import ScrollableImage
from glogger import logger
from togglebutton import ToggleButton, ContrButtons
class GUI:
    """
    A class to create a graphical user interface for an app
    """
    #track button states
    comb_clicked=contr_clicked=red_clicked=green_clicked=both_clicked=im_loaded=False
    #constant contrast guys
    STD_LOWER = 0
    STD_UPPER = 65535
    DEFAULT_CENTER = 32767
    DEFAULT_WIDTH = 65535
    #variable contrast guys
    last_contr=last_contr_comb=(32767, 65535)
    lower_c1=lower_c2=lower_c=0
    higher_c1=higher_c2=higher_c=65535

    def __init__(self, root):
        """
        Initializes the GUI application window and layout

        Args:
            root (tk.Tk): The root window object for the application
        """
        self.root = root
        self.root.title("mDNA")
        #set window size and position
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        width = int(screen_width * 0.85)
        height = int(screen_height * 0.85)
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        #most of self attributes
        self.left_frame=self.right_frame=self.new_frame=self.seperator=None
        self.gpath=self.rpath=self.gim=self.rim=self.cim=None
        self.button_upload=self.button_comb=self.button_contr=None
        self.contr_button_frame=self.button_green=self.button_red=self.button_both=None
        self.window_center=self.window_width=self.slider_center=self.slider_width=None
        self.window_center_frame=self.window_width_frame=None
        #vars for running contrast adjustment in a separate thread
        self.timer_id = None
        self.computation_thread = None
        #init layout
        self.init_layout()
        self.root.update()
        self.toggle_radio_button('both')

    def init_layout(self):
        """
        Initializes the layout by creating top (buttons), left, and right (images) frames
        """
        #init button frame
        self.top_frame = tk.Frame(self.root, bg="#181818")
        self.top_frame.pack(side="top", fill="x")
        self.button_row(self.top_frame)
        #init palceholders for left and right frames
        self.init_lr_frames()
        self.root.update()

        #for testing
        # self.load_n_disp("data/GSM364164_Poplar_July_20_05_13263264_Cy3_Dec_19_2005.tif",
        #                   "data/GSM364164_Poplar_July_20_05_13263264_Cy5_Dec_19_2005.tif")

    def init_lr_frames(self):
        """
        Creates and initializes left and right frames for displaying images
        """
        self.left_frame = tk.Frame(self.root, bg="#181818")
        self.left_frame.pack(side="left", fill="both",expand=True)

        self.seperator = tk.Frame(self.root, bg="#181818", width=2)
        self.seperator.pack(side="left", fill="y")

        self.right_frame = tk.Frame(self.root, bg="#181818")
        self.right_frame.pack(side="right", fill="both", expand=True)

        logger.info("Left and right placeholders created")

    def hide_lr_frames(self):
        """
        Hides left and right frames
        """
        if hasattr(self, 'left_frame') and self.left_frame.winfo_exists():
            self.left_frame.pack_forget()
            logger.info("Left frame hidden")

        if hasattr(self, 'right_frame') and self.right_frame.winfo_exists():
            self.right_frame.pack_forget()
            logger.info("Right frame hidden")

    def show_lr_frames(self):
        """
        Displays left and right frames
        """
        if hasattr(self, 'left_frame') and self.left_frame.winfo_exists():
            self.left_frame.pack(side="left", fill="both", expand=True)
            logger.info("Left frame shown")

        if hasattr(self, 'right_frame') and self.right_frame.winfo_exists():
            self.right_frame.pack(side="right", fill="both", expand=True)
            logger.info("Right frame shown")

    def del_lr_frames(self):
        """
        Deletes left and right frames
        """
        if hasattr(self, 'left_frame') and self.left_frame.winfo_exists():
            self.left_frame.destroy()
            self.left_frame = None
            logger.info("Left frame deleted")

        if hasattr(self, 'right_frame') and self.right_frame.winfo_exists():
            self.right_frame.destroy()
            self.right_frame = None
            logger.info("Right frame deleted")

    def init_n_pack_im(self, image_path, channel, frame, width):
        """
        Creates ScrollableImage object, clears prev changes and packs an image into specified frame

        Args:
            image_path (str): Path to the image file
            channel (int): The image channel (1 for green, 2 for red)
            frame (tk.Frame): The frame to display the image in
            width (int): The width of the image display area
        """
        #delete existing frames
        for widget in frame.winfo_children():
            logger.info("Deleting widget: %s", widget)
            widget.destroy()
        #create ScrollableImage object ad pack into frame
        try:
            image_window = ScrollableImage(master=frame, image_path=image_path, channel=channel,
                                           width=width, lower=self.STD_LOWER, upper=self.STD_UPPER)
        except Exception as e:
            self.del_lr_frames()
            self.init_lr_frames()
            if self.comb_clicked:
                self.toggle_button_comb()
            self.im_loaded = False
            logger.error("Error loading image: %s", e)
            messagebox.showerror("Error", e)
        if channel in {1, 2}:
            setattr(self, 'gim' if channel == 1 else 'rim', image_window) #init self.gim or self.rim
        image_window.pack(fill="both", expand=True)
        logger.info("Image displayed")
        self.im_loaded = True

    def load_n_disp(self, gpath, rpath):
        """
        Loads and displays green and red channel images

        Args:
            gpath (str): Path to the green channel image
            rpath (str): Path to the red channel image
        """
        #frame width part
        frame_width = self.root.winfo_width() // 2
        self.left_frame.config(width=frame_width)
        self.right_frame.config(width=frame_width)
        logger.info("Frame width set to: %s", frame_width)

        self.init_n_pack_im(gpath, 1, self.left_frame, frame_width)
        self.init_n_pack_im(rpath, 2, self.right_frame, frame_width)

    def comb_ims(self):
        """
        Combines green and red channel images into a single image and displays it in seperate frame.
        Creation of combined image does not delete red and greeen images, ratehr hides them;
        reverting to seperate channels also hides combined image
        """
        if not self.comb_clicked:
            self.hide_lr_frames()
            self.last_contr=(int(self.window_center.get()), int(self.window_width.get()))
            self.slider_center.set(self.last_contr_comb[0])
            self.slider_width.set(self.last_contr_comb[1])
            self.button_green.pack_forget()
            self.button_red.pack_forget()
            self.button_both.pack_forget()

            if self.new_frame is None:
                self.new_frame=tk.Frame(self.root, bg="gray")
                self.new_frame.pack(side="bottom", fill="both", expand=True)
                try:
                    image_window = ScrollableImage(master=self.new_frame, gim=self.gim,
                                                   rim=self.rim, width=self.root.winfo_width(),
                                                   lower=self.STD_LOWER, upper=self.STD_UPPER)
                except Exception as e:
                    logger.error("Error loading image: %s", e)
                    messagebox.showerror("Error", e)
                image_window.pack(fill="both", expand=True)
                self.cim=image_window
                logger.info("Combined image created")
            else:
                self.new_frame.pack(side="bottom", fill="both", expand=True)
                self.root.update()
                logger.info("Used existing frame")

            logger.info("Combined image displayed")

        else:
            self.new_frame.pack_forget()
            self.show_lr_frames()
            self.last_contr_comb=(int(self.window_center.get()), int(self.window_width.get()))
            self.slider_center.set(self.last_contr[0])
            self.slider_width.set(self.last_contr[1])
            self.window_center_frame.pack_forget()
            self.window_width_frame.pack_forget()
            self.button_green.pack(side="left", padx=5, pady=5)
            self.button_red.pack(side="left", padx=5, pady=5)
            self.button_both.pack(side="left", padx=5, pady=5)
            self.window_center_frame.pack(side="left", padx=5, pady=5)
            self.window_width_frame.pack(side="left", padx=5, pady=5)
            self.root.update()

            logger.info("Combined image frame hidden")

    def button_row(self, parent_frame):
        """
        Creates and adds the main button row to the parent frame

        Args:
            parent_frame (tk.Frame): The parent frame where the button row is added
        """
        self.add_main_buttons(parent_frame=parent_frame)

        self.add_contr_buttons(parent_frame=parent_frame)

        self.add_sliders()

    def add_main_buttons(self, parent_frame=None):
        """
        Adds the main action buttons (upload, combine, contrast) to the parent frame

        Args:
            parent_frame (tk.Frame, optional): The parent frame for the buttons
        """
        button_frame = tk.Frame(parent_frame, bg="#181818", relief="flat",
                                highlightbackground="#575655")
        button_frame.pack(side="top", pady=5)

        separator = tk.Frame(button_frame, bg="#d7d7d7", height=1)
        separator.pack(side="bottom", fill="both", pady=(3, 1))

        self.button_upload=ToggleButton(button_frame,
                                        ic_path="icons/upload_min.png",
                                        ic_path_clicked="icons/upload_min_toggle_white.png",
                                        sq_size=38,
                                        compound="center",
                                        bg="#181818",
                                        border=0,
                                        command=self.choose_file_and_disp)
        self.button_comb=ToggleButton(button_frame,
                                      ic_path="icons/comp_min.png",
                                      ic_path_clicked="icons/comp_min_toggle_white.png",
                                      sq_size=43,
                                      compound="center",
                                      bg="#181818",
                                      border=0,
                                      command=self.toggle_button_comb)
        self.button_contr=ToggleButton(button_frame,
                                       ic_path="icons/contr_min.png",
                                       ic_path_clicked="icons/contr_min_toggle_white.png",
                                       sq_size=40,
                                       compound="center",
                                       bg="#181818",
                                       border=0,
                                       command=self.toggle_button_contr)

    def add_contr_buttons(self, parent_frame=None):
        """
        Adds the contrast adjustment buttons to the parent frame

        Args:
            parent_frame (tk.Frame, optional): The parent frame for the contrast buttons
        """
        self.contr_button_frame = tk.Frame(parent_frame,
                                           bg="#181818",
                                           relief="flat",
                                           highlightbackground="#575655",
                                           highlightthickness=0)
        self.contr_button_frame.pack(side="top", pady=5)
        self.contr_button_frame.forget()

        separator_contr_left = tk.Frame(self.contr_button_frame, bg="#d7d7d7", height=1)
        separator_contr_right = tk.Frame(self.contr_button_frame, bg="#d7d7d7", height=1)
        separator_contr_left.pack(side="left", fill="both", pady=(3, 1))
        separator_contr_right.pack(side="right", fill="both", pady=(3, 1))

        self.button_green=ContrButtons(self.contr_button_frame,
                                       text="Green",
                                       compound="center",
                                       bg="gray",
                                       fg="white",
                                       border=0,
                                       command=self.toggle_button_green).get_button()
        self.button_green.pack(side="left", padx=5, pady=5)

        self.button_red=ContrButtons(self.contr_button_frame,
                                     text="Red",
                                     compound="center",
                                     bg="white",
                                     fg="white",
                                     border=0,
                                     command=self.toggle_button_red).get_button()
        self.button_red.pack(side="left", padx=5, pady=5, anchor="center")

        self.button_both=ContrButtons(self.contr_button_frame,
                                      text="Both",
                                      compound="center",
                                      bg="white",
                                      fg="white",
                                      border=0,
                                      command=self.toggle_button_both).get_button()
        self.button_both.pack(side="left", padx=5, pady=5, anchor="center")

    def add_sliders(self):
        """
        Adds sliders for window center and width adjustments
        """
        self.window_center_frame = tk.Frame(self.contr_button_frame,
                                            relief="flat",
                                            highlightbackground="#575655",
                                            highlightthickness=0.5)
        self.window_center_frame.pack(side="left", padx=5, pady=5)
        label_entry_center_frame = tk.Frame(self.window_center_frame)
        label_entry_center_frame.pack(side="top", fill="x")

        self.window_center = tk.StringVar(value=self.DEFAULT_CENTER)
        self.window_center.trace_add("write", self.update_slider_center)
        window_center_label = tk.Label(label_entry_center_frame, text="Window center")
        window_center_label.pack(side="left", anchor="w")
        center_vcmd=label_entry_center_frame.register(self.scale_range)
        entry_center = tk.Entry(label_entry_center_frame,
                                textvariable=self.window_center,
                                width=10,
                                validate="key",
                                validatecommand=(center_vcmd, "%P"))
        entry_center.pack(side="right", anchor="e")
        self.slider_center = tk.Scale(self.window_center_frame,
                                      from_=0,
                                      to=65535,
                                      showvalue=0,
                                      orient="horizontal",
                                      length=200,
                                      command=self.update_entry_center)
        self.slider_center.set(self.DEFAULT_CENTER)
        self.slider_center.pack(side="bottom", anchor="w")

        self.window_width_frame = tk.Frame(self.contr_button_frame,
                                           relief="flat",
                                           highlightbackground="#575655",
                                           highlightthickness=0.5)
        self.window_width_frame.pack(side="left", padx=5, pady=5)

        label_entry_width_frame = tk.Frame(self.window_width_frame)
        label_entry_width_frame.pack(side="top", fill="x")
        self.window_width = tk.StringVar(value=self.DEFAULT_WIDTH)
        self.window_width.trace_add("write", self.update_slider_width)
        window_width_label = tk.Label(label_entry_width_frame, text="Window width")
        window_width_label.pack(side="left", anchor="w")
        width_vcmd = label_entry_width_frame.register(self.scale_range)
        entry_width = tk.Entry(label_entry_width_frame,
                               textvariable=self.window_width,
                               width=10,
                               validate="key",
                               validatecommand=(width_vcmd, "%P"))
        entry_width.pack(side="right", anchor="e")
        self.slider_width = tk.Scale(self.window_width_frame,
                                     from_=0,
                                     to=65535,
                                     showvalue=0,
                                     orient="horizontal",
                                     length=200,
                                     command=self.update_entry_width)
        self.slider_width.set(self.DEFAULT_WIDTH)
        self.slider_width.pack(side="bottom", anchor="w")

    def scale_range(self, value):
        """
        Validates whether a given value is within the acceptable range for sliders

        Args:
            value (str): The value to validate

        Returns:
            bool: True if the value is valid, False otherwise
        """
        if value == "":
            return True
        if value.isdigit():
            value_int = int(value)
            return 0 <= value_int <= 65535
        return False

    def toggle_button_comb(self):
        """
        Toggles the state of the combine button and updates the interface accordingly
        """
        if self.im_loaded:
            self.comb_ims()
            self.comb_clicked = self.button_comb.toggle_button_action()

    def toggle_button_contr(self):
        """
        Toggles the state of the contrast button and updates the contrast panel
        """
        if self.im_loaded:
            self.toggle_contr_button_frame()
            self.contr_clicked = self.button_contr.toggle_button_action()

    def toggle_contr_button_frame(self):
        """
        Shows or hides the contrast adjustment panel
        """
        if self.contr_button_frame.winfo_ismapped():
            self.contr_button_frame.pack_forget()
            logger.info("Contrast panel hidden")
        else:
            self.contr_button_frame.pack(side="top", pady=5)
            logger.info("Contrast panel shown")

    def update_entry_center(self, value):
        """
        Updates the window center text entry when the slider is adjusted

        Args:
            value (str): The new slider value
        """
        self.window_center.set(int(float(value)))
        self.timed_conf()

    def update_entry_width(self, value):
        """
        Updates the window width text entry when the slider is adjusted

        Args:
            value (str): The new slider value
        """
        self.window_width.set(int(float(value)))
        self.timed_conf()

    def timed_conf(self):
        """
        Delays the confirmation of contrast adjustments 
        to allow multiple changes without redundant processing
        """
        if self.timer_id is not None:
            self.root.after_cancel(self.timer_id)

        self.timer_id = self.root.after(100, self.confirm_windowing)

    def update_slider_center(self, *args):
        """
        Updates the slider for window center when the text entry is modified
        """
        try:
            value = int(self.window_center.get())
            if self.slider_center["from"] <= value <= self.slider_center["to"]:
                self.slider_center.set(value)
            else:
                logger.warning("Value %s is out of range for center slider", value)
        except ValueError:
            logger.error("Invalid value entered in text field")

    def update_slider_width(self, *args):
        """
        Updates the slider for window width when the text entry is modified
        """
        try:
            value = int(self.window_width.get())
            if self.slider_width["from"] <= value <= self.slider_width["to"]:
                self.slider_width.set(value)
            else:
                logger.warning("Value %s is out of range for width slider", value)
        except ValueError:
            logger.error("Invalid value entered in text field")

    def choose_file(self):
        """
        Opens a file dialog to allow the user to select a file

        Returns:
            str: The selected file path

        Raises:
            Exception: If no file is selected or the file is not a .tif file
        """
        file_path = filedialog.askopenfilename(
            title="Select a File",
            filetypes=(("tif files", "*.tif"), ("All files", "*.*"))
        )
        if file_path and file_path.endswith(".tif"):
            logger.info("Selected File: %s", file_path)
            return file_path
        elif file_path and not file_path.endswith(".tif"):
            logger.info("Selected file is not a tif file")
            raise Exception("Selected file is not a tif file")
        else:
            logger.info("no file selected :<")
            raise Exception("No file selected")

    def choose_file_and_disp(self):
        """
        Opens file dialogs to select two files (green and red channels) and displays them
        """
        try:
            self.gpath=self.choose_file()
            self.rpath=self.choose_file()

            self.clear_all()
            if hasattr(self, 'new_frame') and self.new_frame is not None and self.new_frame.winfo_exists():
                self.new_frame.destroy()
                self.new_frame = None
            if hasattr(self, 'left_frame') and self.left_frame.winfo_exists():
                self.left_frame.destroy()
                self.left_frame = None
            if hasattr(self, 'right_frame') and self.right_frame.winfo_exists():
                self.right_frame.destroy()
                self.right_frame = None

            self.init_lr_frames()
            self.root.update()
            self.load_n_disp(self.gpath, self.rpath)
        except Exception as e:
            logger.error("Error displaying image: %s", e)
            messagebox.showerror("Error", e)

    def clear_all(self):
        """
        Resets the GUI state and clears all loaded images and settings
        """
        if self.comb_clicked:
            self.toggle_button_comb()
        if self.contr_clicked:
            self.toggle_button_contr()
        self.toggle_radio_button('both')

        self.seperator = self.gim = self.rim = self.cim= None
        self.lower_c1 = self.lower_c2 = self.lower_c=0
        self.higher_c1 = self.higher_c2 = self.higher_c = 65535
        self.window_center.set(self.DEFAULT_CENTER)
        self.window_width.set(self.DEFAULT_WIDTH)
        self.slider_center.set(self.DEFAULT_CENTER)
        self.slider_width.set(self.DEFAULT_WIDTH)

    def windowing_parameters(self, center, length):
        """
        Calculates the lower and upper bounds for windowing based on the center and length

        Args:
            center (int): The center value
            length (int): The window length

        Returns:
            tuple: Lower and upper bounds for windowing
        """
        center=int(center)
        length=int(length)
        return (
                max(self.STD_LOWER, int(center-length/2)),
                min(self.STD_UPPER, int(center+length/2))
               )


    def confirm_windowing(self):
        """
        Confirms and applies contrast adjustments based on the current windowing parameters
        """
        if self.computation_thread and self.computation_thread.is_alive():
            return

        self.computation_thread = threading.Thread(target=self._run_contrast_adjustment)
        self.computation_thread.start()

    def _run_contrast_adjustment(self):
        """
        Runs the contrast adjustment logic for the images
        """
        if not self.comb_clicked:

            if self.green_clicked:
                self.lower_c1, self.higher_c1 = self.windowing_parameters(self.window_center.get(),
                                                                          self.window_width.get())
            elif self.red_clicked:
                self.lower_c2, self.higher_c2 = self.windowing_parameters(self.window_center.get(),
                                                                          self.window_width.get())
            elif self.both_clicked:
                self.lower_c1, self.higher_c1 = self.windowing_parameters(self.window_center.get(),
                                                                          self.window_width.get())
                self.lower_c2, self.higher_c2 = self.lower_c1, self.higher_c1

            self.root.after(0, self.disp_alter_contr_ims)

        if self.comb_clicked:
            self.lower_c, self.higher_c = self.windowing_parameters(self.window_center.get(),
                                                                    self.window_width.get())
            self.root.after(0, lambda: self.cim.alter_contr((self.lower_c, self.higher_c)))

    def disp_alter_contr_ims(self):
        """
        Alteres contrast of images and displays them
        """
        if self.green_clicked or self.both_clicked:
            self.gim.alter_contr((self.lower_c1, self.higher_c1))
        if self.red_clicked or self.both_clicked:
            self.rim.alter_contr((self.lower_c2, self.higher_c2))

    def toggle_button_green(self):
        """
        Toggles the green contrast adjustment button
        """
        self.toggle_radio_button('green')

    def toggle_button_red(self):
        """
        Toggles the red contrast adjustment button
        """
        self.toggle_radio_button('red')

    def toggle_button_both(self):
        """
        Toggles the both contrast adjustment button
        """
        self.toggle_radio_button('both')

    def toggle_radio_button(self, button_name):
        """
        Toggles the specified radio button and updates its appearance

        Args:
            button_name (str): The name of the button to toggle ('green', 'red', or 'both')
        """
        buttons = {
            'green': ('!button', 'lightgreen', 'black'),
            'red': ('!button2', 'lightcoral', 'black'),
            'both': ('!button3', 'gold', 'black')
        }
        for name, (widget, _, _) in buttons.items():
            self.contr_button_frame.children[widget].configure(bg="#181818", fg="white")
            setattr(self, f"{name}_clicked", False)

        if button_name in buttons:
            widget, color, tcolor = buttons[button_name]
            self.contr_button_frame.children[widget].configure(bg=color, fg=tcolor)
            setattr(self, f"{button_name}_clicked", True)
