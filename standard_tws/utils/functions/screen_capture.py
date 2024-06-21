from win32api import GetSystemMetrics  # pylint: disable=E0611
from threading import Thread
import cv2
import numpy as np
import pyautogui
import os


class ScreenCapture(Thread):
    def __init__(self, video_name):
        """
        屏幕录制。
        """
        super().__init__()
        self.flag = False
        self.video_name = video_name

    def run(self):
        """
        录制屏幕。
        :return: None
        """
        # display screen resolution, get it from your OS settings
        screen_size = (GetSystemMetrics(0), GetSystemMetrics(1))
        # define the codec
        fourcc = cv2.VideoWriter_fourcc(*"XVID")  # pylint: disable=E1101
        # create the video write object
        out = cv2.VideoWriter("{}.avi".format(self.video_name), fourcc, 20.0, screen_size)  # pylint: disable=E1101
        while True:
            # make a screenshot
            img = pyautogui.screenshot()
            # convert these pixels to a proper numpy array to work with OpenCV
            frame = np.array(img)
            # convert colors from BGR to RGB
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  # pylint: disable=E1101
            # write the frame
            out.write(frame)
            # if the user clicks q, it exits
            if self.flag:
                break

        # make sure everything is closed when exited
        cv2.destroyAllWindows()  # pylint: disable=E1101
        out.release()

    def remove(self):
        """
        删除录制的视频。
        :return: None
        """
        try:
            os.remove('{}.avi'.format(self.video_name))
        except (FileNotFoundError, PermissionError):
            pass
