from PyQt4 import QtGui


def is_in(list_names, search_list):
    for f in list_names:
        if f not in search_list:
            return False
    return True

def show_message(message, title="Error!"):
    e = QtGui.QMessageBox()
    e.setWindowTitle(title)
    e.setText(message)
    e.exec_()
