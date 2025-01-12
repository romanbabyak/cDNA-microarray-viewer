"""
This module provides the ScrollableImage class for displaying and interacting with heavy tif images

The ScrollableImage class supports zooming, dragging, 
and contrast adjustments using a Tkinter-based GUI

Invariants:
- Zooming levels are cashed. They are initialized during the zoom operation
but can be precomputed up to a certain level
- To display image in the canvas image it is cropped to the visible portion
of the screen (loading whole image into canvas would be too slow)
- The image is resized to fit the canvas while maintaining its aspect ratio;
default interpolation method is cv2.INTER_LINEAR
- Since contrast adjustment are applied with respect to the 16-bit image,
new contrast images rewrite those in the pyramid (there are just too
many possibilities for the level of the contrast window that makes
cashing images for each contrast level impractical)
- It may seem that it is cheaper to store interpolated versions of the 16-bit image
and apply contrast changes to them, but it is not the case. Since windowing method
in MDNA class is considerably less efficient than cv2.resize method for huge 
matrices, it is cheaper to apply contrast change to original 16-bit image once
and then interpolate for each zoom level at each contrast change

Possible improvements:
- Using interpolation only to visible portion of the image
would likely eliminate lagging during zooming with levels that have not 
yet been computed; it would also require concatenation of the interpolated matrix
during dragging of the image.
- Even though, previous point would eliminate lagging during initial zooming, 
lagging would still occur since loading image into Tkinter canvas is not efficient and causes
lags for fullscreen or almost fullscrean images. Usage of alternative
library for GUI management may turn out to be more efficient
- CUDA acceleration for image processing would be a great improvement
---------------------------------------------------------------------------

Above points were not implemented in this project, since 
they require rewriting of the whole classes responsible for the
mentioned functionalities. They were noticed in the hindsight.
"""

import tkinter as tk
import time
from PIL import Image, ImageTk
import cv2
from mdna import MDNA
from glogger import logger

class ScrollableImage(tk.Frame):
    """
    A class for displaying and interacting with heavy tif images in a and zoomable Tkinter frame

    Attributes:
        INTERPOLATION (int): Interpolation method used for resizing (default is cv2.INTER_LINEAR)
        ZOOM_FACTOR (float): The zoom factor for scaling the image
        PRE_COMP (bool): Whether to precompute zoom levels
        PRE_COMP_LEVEL (int): The level up to which zooming is precomputed
        MAX_INZOOM_LEVEL (int): Maximum zoom-in level allowed
    """
    INTERPOLATION=cv2.INTER_LINEAR
    ZOOM_FACTOR=1.15
    PRE_COMP=False #change to False for testing, faster loading
    PRE_COMP_LEVEL=5
    MAX_INZOOM_LEVEL=13

    def __init__(self, coords_label, master=None, **kw):
        """
        Initializes a ScrollableImage instance

        Args:
            master (tk.Widget): The parent widget for the frame
            **kw: Additional arguments, such as image path, channel, width, and contrast range
        """
        #args and parent constructor; image placing in canvas
        self.image_path=kw.pop('image_path', None)
        self.channel=kw.pop('channel', None)
        width=kw.pop('width', None)
        self.gim=kw.pop('gim', None)
        self.rim=kw.pop('rim', None)
        self.contr=(kw.pop('lower', None), kw.pop('upper', None))
        self.coords_label = coords_label

        #dragging
        self.last_x = None
        self.last_y = None
        self.offset_x = 0
        self.offset_y = 0
        self.last_scroll_time = 0
        self.delay = 0.0001
        self.pyramid = {}
        self.c_level, self.p_level = None, None
        self.or_im=None
        self.old_img_w, self.old_img_h=None, None
        self.orig_windowed_im=None

        #init MDNA object
        if self.gim is None and self.rim is None:
            self.tk_im = self._init_mdna(width)
            logger.info("new image for display created")
        else:
            self.tk_im = self._init_comb_mdna(width, self.gim, self.rim)
            logger.info("image for display passed")

        #canvas layout
        super().__init__(master=master, **kw)
        self.cnvs = tk.Canvas(self, highlightthickness=0, bg="#181818", **kw)
        self.image_id = self.cnvs.create_image(0, 0, anchor='center', image=self.tk_im)
        self.cnvs.grid(row=0, column=0, sticky='nsew')
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        #bindings
        self.cnvs.bind("<Configure>", self._upd_center)
        self.cnvs.bind("<MouseWheel>", self.mouse_scroll)
        self.cnvs.bind("<ButtonPress-1>", self.rec_pos)
        self.cnvs.bind("<B1-Motion>", self.drag_im)
        self.cnvs.bind("<Motion>", self.show_pixel_coordinates)

    def _upd_center(self, event=None):
        """
        Updates the position of the image in the canvas to center it;
        Also to adjust max outscroll durign window resize
        """
        self.cnvs.coords(self.image_id, self.cnvs.winfo_width() / 2, self.tk_im.height()/2-1)
        self.move_to(self.offset_x, self.offset_y)
        self._upd_upper_bound()

    def _upd_upper_bound(self):
        """
        Updates the upper bounds for zooming
        """
        if self.tk_im.height()<self.cnvs.winfo_height():
            level=self.p_level

            while (level in self.pyramid and self.pyramid[level][1][1]<self.cnvs.winfo_height()):
                level+=1
            im, width, height = self.resize_keeping_ratio(self.orig_windowed_im,
                                                          height=self.cnvs.winfo_height())

            self.pyramid["outscroll"] = (im, (width, height), self.contr)
            self.p_level=level
            self.c_level="outscroll"

            logger.info("final pyramid level %s with dim %sx%s and window %s-%s",
                        self.c_level, width, height, self.contr[0], self.contr[1])

            self._zoom_image()

    def _init_mdna(self, width):
        """
        Initializes the MDNA object and processes the image for display

        Args:
            width (int): The width of the display area

        Returns:
            ImageTk.PhotoImage: The processed image ready for display
        """
        self.mdna = MDNA(self.image_path, self.channel)
        if self.mdna is None:
            logger.error("Error loading image")
            raise Exception("Image could not be loaded")

        self.or_im=self.mdna.get_im()
        im=MDNA.windowing(self.or_im, self.contr[0], self.contr[1])
        self.orig_windowed_im=im

        _, im, self.c_level=self._init_pyramid(im, width)
        pil_image = Image.fromarray(im)
        logger.info("new MDNA object created")
        return ImageTk.PhotoImage(pil_image)

    def _init_comb_mdna(self, width, g, r):
        """
        Initializes the MDNA object for combined images and processes it for display

        Args:
            width (int): The width of the display area
            g (MDNA): The green channel image; instance of ScrollableImage
            r (MDNA): The red channel image; instance of ScrollableImage

        Returns:
            ImageTk.PhotoImage: The processed combined image ready for dispaly
        """
        self.mdna = MDNA.get_combined_image(g.get_im(), r.get_im())
        self.orig_windowed_im=MDNA.windowing(self.mdna, self.contr[0], self.contr[1])
        self.or_im=self.mdna

        _, im, self.c_level=self._init_pyramid(self.orig_windowed_im, width)
        pil_image = Image.fromarray(im)
        logger.info("new MDNA object created")
        return ImageTk.PhotoImage(pil_image)

    def get_im(self):
        """
        Retrieves the original image

        Returns:
            numpy.ndarray: The original image
        """
        return self.or_im

    def rec_pos(self, event):
        """
        Records the current mouse position for im dragging

        Args:
            event (tk.Event): The mouse event containing the current position
        """
        self.last_x = event.x
        self.last_y = event.y

        # logger.info("recording position: %s, %s", self.last_x, self.last_y)

    def drag_im(self, event):
        """
        Drags the image in the canvas based on mouse movement

        Args:
            event (tk.Event): The mouse event containing the current position
        """
        dx = event.x - self.last_x
        dy = event.y - self.last_y

        dims=self.pyramid[self.c_level][1]

        self.offset_x -= dx
        self.offset_y -= dy

        max_x_offset = max(dims[0] - self.cnvs.winfo_width(), 0)
        max_y_offset = max(dims[1] - self.cnvs.winfo_height(), 0)
        self.offset_x = max(0, min(self.offset_x, max_x_offset))
        self.offset_y = max(0, min(self.offset_y, max_y_offset))

        self.move_to(self.offset_x, self.offset_y)

        self.rec_pos(event)

    def move_to(self, offset_x, offset_y):
        """
        Moves the view of the image to the specified offsets, 
        with respect to the left upper corner

        Args:
            offset_x (int): Horizontal offset
            offset_y (int): Vertical offset
        """
        dims=self.pyramid[self.c_level][1]

        x2 = offset_x + self.cnvs.winfo_width()
        y2 = offset_y + self.cnvs.winfo_height()

        x2 = min(x2, dims[0])
        y2 = min(y2, dims[1])

        self._crop_n_show(offset_x, offset_y, x2, y2)

    def _crop_n_show(self, offset_x, offset_y, x2, y2):
        """
        Crops and displays the visible portion of the image;
        notice, that method works with respect to the current level of pyramid (zoom)

        Args:
            offset_x (int): Horizontal offset of the crop
            offset_y (int): Vertical offset of the crop
            x2 (int): Horizontal endpoint of the crop
            y2 (int): Vertical endpoint of the crop
        """
        resized_im, dims,_= self.pyramid[self.c_level]
        cropped_image = resized_im[int(offset_y):int(y2), int(offset_x):int(x2)]

        visible_pil_image = Image.fromarray(cropped_image)
        self.tk_im = ImageTk.PhotoImage(visible_pil_image)
        self.cnvs.itemconfig(self.image_id, image=self.tk_im)
        self.cnvs.config(scrollregion=(0, 0, dims[0], dims[1]))
        self.cnvs.config(scrollregion=self.cnvs.bbox("all"))

        logger.info("moveto offset=(%s,%s), region=(%s:%s,%s:%s)",
                    offset_x, offset_y, offset_x, x2, offset_y, y2)

    def _init_pyramid(self, im, width=None, height=None):
        """
        Initializes a pyramid of image zoom levels at different resolutions

        Args:
            im (numpy.ndarray): The base image
            width (int, optional): Desired width of the base image
            height (int, optional): Desired height of the base image

        Returns:
            tuple: A dictionary of pyramid levels, the resized base image, and the starting level
        """
        level=0
        im, w, h = self.resize_keeping_ratio(im, width, height)

        self.pyramid[level]=(im, (w, h), (self.contr[0], self.contr[1]))
        logger.info("pyramid initialized")

        if self.PRE_COMP:
            for i in range(level+1, self.MAX_INZOOM_LEVEL+1):
                w=int(w*self.ZOOM_FACTOR)
                h=int(h*self.ZOOM_FACTOR)

                if i>self.PRE_COMP_LEVEL:
                    self.add_to_pyramid(i, self.orig_windowed_im, w, h)

        return self.pyramid, im, level

    def add_to_pyramid(self, level, im, width, height):
        """
        Adds a new level to the image pyramid

        Args:
            level (int): The pyramid level to add
            im (numpy.ndarray): The image to resize
            width (int): Width for the new level
            height (int): Height for the new level
        """
        im, width, height = self.resize_keeping_ratio(im, width, height)
        self.pyramid[level] = (im, (width, height), self.contr)

        logger.info("new pyramid level %s with dim %sx%s and contrast window %s-%s",
                    level, width, height, self.contr[0], self.contr[1])

    def mouse_scroll(self, event):
        """
        Handles mouse scrolling for zooming in and out

        Args:
            event (tk.Event): The mouse scroll event
        """
        if time.time() - self.last_scroll_time < self.delay:
            logger.info("scrolling skipped")
            return

        dims=self.pyramid[self.c_level][1]
        self.old_img_w, self.old_img_h=dims

        #inscroll
        if event.delta>0:
            if self.c_level=="outscroll":
                self.c_level=self.p_level
            elif self.c_level<self.MAX_INZOOM_LEVEL:
                self.p_level=self.c_level
                self.c_level += 1
            else:
                return

            if self.c_level not in self.pyramid or self.pyramid[self.c_level][2]!=self.contr:
                self.add_to_pyramid(self.c_level, self.orig_windowed_im,
                                self.old_img_w*self.ZOOM_FACTOR, self.old_img_h*self.ZOOM_FACTOR)

        #outscroll
        elif event.delta<0:
            w=int(self.old_img_w/self.ZOOM_FACTOR)
            h=int(self.old_img_h/self.ZOOM_FACTOR)

            if h<=self.cnvs.winfo_height():
                im, width, height = self.resize_keeping_ratio(self.orig_windowed_im,
                                                              height=self.cnvs.winfo_height())
                self.pyramid["outscroll"] = (im, (width, height), self.contr)
                self.c_level="outscroll"

                logger.info("final pyramid level %s with dim %sx%s and contrast window %s-%s",
                            self.c_level, width, height, self.contr[0], self.contr[1])

            elif self.c_level!="outscroll":
                self.p_level=self.c_level
                self.c_level-=1
                if self.c_level not in self.pyramid or self.pyramid[self.c_level][2]!=self.contr:
                    self.add_to_pyramid(self.c_level, self.orig_windowed_im, w, h)

            else:
                level=self.p_level
                while (level in self.pyramid and self.pyramid[level][1][1]>self.pyramid["outscroll"][1][1]):
                    level-=1

                if level not in self.pyramid or self.pyramid[level][2]!=self.contr:
                    self.add_to_pyramid(level, self.orig_windowed_im,
                                        self.pyramid[level+1][1][0]/self.ZOOM_FACTOR,
                                        self.pyramid[level+1][1][1]/self.ZOOM_FACTOR)
                self.c_level=level

        #anomaly
        else:
            return

        mx=self.offset_x+event.x
        my=self.offset_y+event.y

        try:
            self._zoom_image(mx, my, event.x, event.y)
        finally:
            self.last_scroll_time=time.time()

    def _zoom_image(self, mouse_x_old=0, mouse_y_old=0, canvas_mouse_x=0, canvas_mouse_y=0):
        """
        Zooms the image to the cursor position

        Args:
            mouse_x_old (int): Old mouse x-coordinate on the image
            mouse_y_old (int): Old mouse y-coordinate on the image
            canvas_mouse_x (int): Mouse x-coordinate on the canvas
            canvas_mouse_y (int): Mouse y-coordinate on the canvas
        """
        dims=self.pyramid[self.c_level][1]

        #absolute scaling, dimishing effect on image (effect of slowing down when close to image);
        #change to absolut vals in _mouse_scroll if used
        # scale_x = new_img_w / float(self.old_img_w) if self.old_img_w > 0 else 1.0
        # scale_y = new_img_h / float(self.old_img_h) if self.old_img_h > 0 else 1.0

        scale_x = self.ZOOM_FACTOR if dims[0]>self.old_img_w else 1/self.ZOOM_FACTOR
        scale_y = self.ZOOM_FACTOR if dims[1]>self.old_img_h else 1/self.ZOOM_FACTOR

        new_mouse_x_in_image=int(mouse_x_old*scale_x)
        new_mouse_y_in_image=int(mouse_y_old*scale_y)

        self.offset_x=new_mouse_x_in_image-canvas_mouse_x
        self.offset_y=new_mouse_y_in_image-canvas_mouse_y

        max_x_offset=max(dims[0]-self.cnvs.winfo_width(), 0)
        max_y_offset=max(dims[1]-self.cnvs.winfo_height(), 0)
        self.offset_x=max(0, min(self.offset_x, max_x_offset))
        self.offset_y=max(0, min(self.offset_y, max_y_offset))
        crop_x2=min(dims[0], self.offset_x+self.cnvs.winfo_width())
        crop_y2=min(dims[1], self.offset_y+self.cnvs.winfo_height())

        self._crop_n_show(self.offset_x, self.offset_y, crop_x2, crop_y2)

    def get_c_level(self):
        """
        Retrieves the current zoom level

        Returns:
            int: The current zoom level
        """
        return self.c_level

    def get_offset(self):
        """
        Retrieves the current offset

        Returns:
            tuple: The current offset (x, y)
        """
        return (self.offset_x, self.offset_y)

    def zoom_to_level(self, event, level):
        """
        Zooms the image to a specified level

        Args:
            level (int): The level to zoom to
        """
        if level==self.c_level:
            return

        if level=="outscroll":
            event.delta=-1
        elif self.c_level=="outscroll":
            event.delta=1
        elif level<self.c_level:
            event.delta=-1
        else:
            event.delta=1

        while self.c_level!=level:
            self.mouse_scroll(event)

    def alter_contr(self, contr):
        """
        Alters the contrast of the displayed image

        Args:
            contr (tuple): The new contrast range (lower, upper)
        """
        self.contr=contr
        if self.pyramid[self.c_level][2]!=contr:
            self.orig_windowed_im=MDNA.windowing(self.or_im, contr[0], contr[1])
            res_im, w, h=self.resize_keeping_ratio(self.orig_windowed_im,
                                                   self.pyramid[self.c_level][1][0],
                                                   self.pyramid[self.c_level][1][1])
            self.pyramid[self.c_level]=(res_im, (w, h), contr)

            self.move_to(self.offset_x, self.offset_y)

    def resize_keeping_ratio(self, image, width=None, height=None, inter=INTERPOLATION):
        """
        Resizes an image while maintaining its aspect ratio

        Args:
            image (numpy.ndarray): The image to resize
            width (int, optional): Desired width of the resized image
            height (int, optional): Desired height of the resized image
            inter (int): Interpolation method for resizing

        Returns:
            tuple: The resized image, its width, and its height
        """
        width=int(width) if width is not None else None
        height=int(height) if height is not None else None

        (h, w) = image.shape[:2]
        if width is None and height is None:
            return (image, w, h)
        if width is None:
            r = height / float(h)
            dim = (int(w * r), height)
        else:
            r = width / float(w)
            dim = (width, int(h * r))

        resized = cv2.resize(image, dim, interpolation=inter)

        logger.info("image resized to %s", dim)

        return (resized, dim[0], dim[1])

    def get_pixel_coordinates(self, event):
        offset_x = self.offset_x
        offset_y = self.offset_y

        resized_im = self.pyramid[self.c_level][0]
        relative_x = offset_x + event.x
        relative_y = offset_y + event.y

        scale_x = self.or_im.shape[1] / resized_im.shape[1]
        scale_y = self.or_im.shape[0] / resized_im.shape[0]

        if(self.c_level == 'outscroll' or self.c_level < 0):
            original_x = int(relative_x * scale_x)
            original_x -= int(self.cnvs.winfo_width() / 2 * scale_x)
            original_x += int(self.or_im.shape[1] / 2)
            original_y = int(relative_y * scale_y)
            original_x = max(0, min(self.or_im.shape[1] - 1, original_x))
            original_y = max(0, min(self.or_im.shape[0] - 1, original_y))

            return original_x, original_y
        else:
            original_x = max(0, min(self.or_im.shape[1] - 1, int(relative_x * scale_x)))
            original_y = max(0, min(self.or_im.shape[0] - 1, int(relative_y * scale_y)))

            return original_x, original_y

    def show_pixel_coordinates(self, event):
        original_x, original_y = self.get_pixel_coordinates(event)
        if self.channel == 1:
            self.coords_label.config(text=f"Green image: x: {original_x}/{self.or_im.shape[1]-1}, y: {original_y}/{self.or_im.shape[0]-1}")
        elif self.channel == 2:
            self.coords_label.config(text=f"Red image: x: {original_x}/{self.or_im.shape[1]-1}, y: {original_y}/{self.or_im.shape[0]-1}")
        elif self.gim is not None and self.rim is not None:
            self.coords_label.config(text=f"Combined image: x: {original_x}/{self.or_im.shape[1]-1}, y: {original_y}/{self.or_im.shape[0]-1}")

