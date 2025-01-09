"""
This module provides the MDNA class for image processing, including loading, 
manipulating color channels, contrast adjustment, and combining images

Our solution uses OpenCV for loading and processing of tiff files
"""
import cv2
import numpy as np
from glogger import logger

class MDNA:
    """
    A class for handling and processing MDNA images with various utilities
    such as loadnig images, manipulating color channels, adjusting contrast, 
    and combining images

    Attributes:
        cy (numpy.ndarray): The loaded image in memory
    """
    def __init__(self, cy=None, channel=None):
        """
        Initializes the MDNA object by loading an image and optionally applying a color channel

        Args:
            cy (str): Path to the image file to load.
            channel (int, optional): The color channel to apply;
            1 for green, 2 for red. Defaults to None
        """
        self.cy=self._im_load(cy, channel)

    def _im_load(self, path, channel=None):
        """
        Loads an 16-bit image from the specified path and optionally applies a color channel

        Args:
            path (str): The file path to the image
            channel (int, optional): The color channel to apply;
            1 for green, 2 for red. Defaults to None

        Returns:
            numpy.ndarray: The loaded image. Returns None if the image could not be loaded
        """
        try:
            im=cv2.imread(path, -1)
            if channel is not None: #if channel isn't given then image is black and white
                im=self._get_c_image(im, channel)
                logger.info("Image with channel %s loaded", channel)
            return im
        except Exception as e:
            logger.error("Error loading image: %s", e)
            return None

    def _get_c_image(self, im, channel):
        """
        Applies a specified color channel to a grayscale image

        Args:
            im (numpy.ndarray): The input grayscale image
            channel (int): The color channel to apply; 
                            1 for green, 2 for red

        Returns:
            numpy.ndarray: The image with the specified color channel applied
        """
        if channel is None:
            return im
        zeros = np.zeros_like(im, dtype=im.dtype)
        if channel==1:
            im = cv2.merge([zeros, im, zeros])
        elif channel==2:
            im = cv2.merge([im, zeros, zeros])
        else:
            raise Exception("Invalid channel")
        return im

    def _std_contrast(self):
        """
        Adjusts the contrast of the image to standardize intensity levels 
        (max width (65535) and window center is in teh center of the contrast range (32767))

        Returns:
            numpy.ndarray: The contrast-adjusted image
        """
        lower = np.min(self.cy)
        upper = np.max(self.cy)
        windowed_image = np.clip(self.cy, lower, upper)
        image = ((windowed_image - lower) / (upper - lower) * 255).astype(np.uint8)
        logger.info("Windowing with lower=%lo upper=%u", lower, upper)
        return image

    def get_im(self):
        """
        Retuerns loaded image

        Returns:
            numpy.ndarray: The loaded image
        """
        return self.cy

    def get_std_im(self):
        """
        Retrieves the default contrast-adjusted version of the loaded image

        Returns:
            numpy.ndarray: The contrast-adjusted image
        """
        return self._std_contrast()

    @staticmethod
    def get_combined_image(cy3, cy5):
        """
        Combines two images by merging their color channels

        Args:
            cy3 (numpy.ndarray): The first image to combine (Cy3 channel)
            cy5 (numpy.ndarray): The second image to combine (Cy5 channel)

        Returns:
            numpy.ndarray: The combined image with channels merged
        """
        zeros = np.zeros_like(cy3[:,:,1], dtype=cy3.dtype)
        combined_image = cv2.merge([cy5[:,:,0], cy3[:,:,1], zeros])
        return combined_image

    @staticmethod
    def windowing(cy, lower, upper):
        """
        Adjusts contrast of an image

        Args:
            cy (numpy.ndarray): The input image
            lower (int): The lower intensity threshold
            upper (int): The upper intensity threshold

        Returns:
            numpy.ndarray: The contrast-adjusted image after windowing
        """
        windowed_image = np.clip(cy, lower, upper)
        image = ((windowed_image - lower) / (upper - lower) * 255).astype(np.uint8)
        logger.info("Windowing with lower=%s, upper=%s", lower, upper)
        return image
            