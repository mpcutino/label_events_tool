from os import path as os_path
from os import remove
from PyQt4 import QtGui, QtCore

import pandas as pd
import numpy as np
import cv2

from qt_generated.main import Ui_MainWindow, _fromUtf8
from utils import is_in, show_message


REQUIRED_COLS = ["timestamp", "x", "y", "p", "next_img_name"]
IMG_W = 346
IMG_H = 260

class Modified_MainWindow(Ui_MainWindow):

    def __init__(self):
        super(Modified_MainWindow, self).__init__()

    def doUiSetup(self, qtMainWindow):
        # this is from base class
        self.setupUi(qtMainWindow)

        # now add my own stuff
        self.events_df = pd.DataFrame()
        self.__init_clck_pixels()
        self.images_names = []
        self.count = -1
        self.eraserMode = False
        self.eraserW = 15
        self.eraserH =15
        # add connections to actions
        self.actionLoad.triggered.connect(self.load_events_file)
        self.actionEraser.triggered.connect(self.set_eraser_mode)
        self.actionNext_Image.triggered.connect(self.next_image)
        self.actionPrevious_Image.triggered.connect(self.prev_image)
        self.actionUndo.triggered.connect(self.undo)
        # add event to image click
        self.img_lbl.mousePressEvent = self.img_clicked
        # add connection to buttons
        self.btn_Save.clicked.connect(self.save_changes)
        self.btn_Discard.clicked.connect(self.discard_changes)
    
    def scale_eraser(self):
        return int(self.eraserW*float(IMG_W)/self.img_lbl.width()),\
            int(self.eraserH*float(IMG_H)/self.img_lbl.height())
    
    def save_changes(self):
        print("save")
        self.events_df = self.__get_rmdf()

    def discard_changes(self):
        self.__init_clck_pixels()
        self.paint_img(self.events_df)

    def load_events_file(self):
        # The QWidget widget is the base class of all user interface objects in PyQt4.
        w = QtGui.QWidget()
        # Set window size.
        w.resize(320, 240)
        # Set window title
        w.setWindowTitle("Hello World!")
        filename = QtGui.QFileDialog.getOpenFileName(w, 'Open File', '/', "Text Files (*.txt *.csv)")
        print(filename)

        try:
            df = pd.read_csv(str(filename))
            if not is_in(REQUIRED_COLS, df.columns):
                # display error message
                show_message("Dataframe must contain columns:\n\n{0}".format(", ".join(REQUIRED_COLS)))
            else:
                folder = os_path.dirname(str(filename))
                self.events_df = df
                self.events_df["next_img_name"] = folder + self.events_df["next_img_name"] 
                self.images_names = df.next_img_name.unique()
                self.count = -1
                self.update_image(foward=True)
        except Exception as e:
            print(e)
            show_message("Not a valid dataframe")

    def set_eraser_mode(self):
        self.eraserMode = not self.eraserMode
        if self.eraserMode:
            pm = QtGui.QPixmap(_fromUtf8(":/images/images/init.png")).scaled(self.eraserW,self.eraserH)
            # create painter instance with pixmap
            painterInstance = QtGui.QPainter(pm)
            # set rectangle color and thickness
            penRectangle = QtGui.QPen(QtCore.Qt.blue)
            penRectangle.setWidth(2)
            # draw rectangle on painter
            painterInstance.setPen(penRectangle)
            painterInstance.drawRect(0,0, self.eraserW,self.eraserH)
            painterInstance.end()

            self.centralwidget.setCursor(QtGui.QCursor(pm))
        else:
            self.centralwidget.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))

    def img_clicked(self, event):
        if not self.eraserMode:
            return
        if self.count < 0 or self.count >= len(self.images_names):
            return
        x = event.pos().x()
        y = event.pos().y()
        
        scale_erW, scale_erH = self.scale_eraser()
        # transform from label scale to image scale
        x = int(x*float(IMG_W)/self.img_lbl.width() - scale_erW/2.0)
        y = int(y*float(IMG_H)/self.img_lbl.height() - scale_erH/2.0)
        
        if (x, y) not in self.remove_pixels:
            self.clicked_pixels.append((x, y))
            self.remove_pixels[(x, y)] = []
            for i in range(scale_erW):
                for j in range(scale_erH):
                    nx, ny = (x+i, y+j)
                    if self.__is_valid(nx, ny):
                        self.remove_pixels[(x, y)].append((nx, ny))
            # self.remove_pixels[(x, y)] = [(x, y)]
            df = self.__get_rmdf()
            self.paint_img(df)

    def undo(self):
        if len(self.clicked_pixels):
            rm_pixel = self.clicked_pixels[-1]
            self.clicked_pixels = self.clicked_pixels[:-1]
            self.remove_pixels.pop(rm_pixel, None)
            df = self.__get_rmdf()
            self.paint_img(df)

    def next_image(self):
        self.update_image(foward=True)

    def prev_image(self):
        self.update_image(foward=False)

    def update_image(self, foward=True):
        # new image, so update clicked pixels
        self.__init_clck_pixels()
        if not len(self.images_names):
            show_message("No images")
            return

        self.count += 1 if foward else -1

        if self.count >= len(self.images_names) and foward:
            self.count = 0
        if self.count < 0 and not foward:
            self.count = len(self.images_names) - 1
        self.paint_img(self.events_df)
    
    def paint_img(self, df):
        if 0 <= self.count < len(self.images_names):
            current_img_name = self.images_names[self.count]

            events_data = df.loc[df["next_img_name"] == current_img_name]
            print(len(events_data))

            img = np.full((IMG_H, IMG_W, 3), (255, 255, 255))
            for _, r in events_data[REQUIRED_COLS].iterrows():
                color = (0, 0, 255) if r.p > 0 else (255, 0, 0)
                img[r.y][r.x] = color
            cv2.imwrite("tmp.png", img)
            self.img_lbl.setPixmap(QtGui.QPixmap("tmp.png"))
            remove("tmp.png")

    def __get_rmdf(self):
        rm_pixels = []
        for p in self.remove_pixels.values():
            rm_pixels.extend(p)
        # print(rm_pixels)
        # print(len(rm_pixels))
        # print(self.clicked_pixels)
        rm_df = pd.DataFrame(rm_pixels, columns=["x", "y"]).drop_duplicates()
        # get the current image 
        df = self.events_df.loc[self.events_df["next_img_name"] == self.images_names[self.count]]

        # print(len(df))
        # print(df[df[["x", "y"]].apply(tuple,1).isin(rm_df.apply(tuple,1))])
        # print(len(df[~df[["x", "y"]].apply(tuple,1).isin(rm_df.apply(tuple,1))]))

        return df[~df[["x", "y"]].apply(tuple,1).isin(rm_df.apply(tuple,1))]
    
    def __init_clck_pixels(self):
        self.clicked_pixels = []
        self.remove_pixels = {}  # clicked pixels and eraser area

    def __is_valid(self, x, y):
        return 0<= x < IMG_W and 0<= y < IMG_H

if __name__ == "__main__":
    import sys
    app = QtGui.QApplication(sys.argv)
    MainWindow = QtGui.QMainWindow()
    ui = Modified_MainWindow()
    ui.doUiSetup(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())
