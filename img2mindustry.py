from PyQt5 import QtWidgets, uic
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QFileDialog, QVBoxLayout, QMessageBox
import sys
import os
import subprocess
import os
if getattr(sys, 'frozen', False):
    base_dir = os.path.dirname(sys.executable)
    print("EXE")
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    print("PY")
lib_path = os.path.join(base_dir, "core", "lib.exe")
print(f"lib: {lib_path}")
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        uic.loadUi("ui/main.ui", self)
        
        
        # pre set 
        self.label_7.hide()
        self.Waitcd.hide()
        self.label_8.hide()
        self.waitEvery.hide()
        
        self.folder_path = "" # folder
        self.file_path = "" # image
        self.preset = "small-inner"
        self.downscale = 1
        self.DisplayNameStr = "Display1"
        self.WaitFloat = "0.1"
        self.WaitEveryInt = "10"
        
        self.BrowseImage.clicked.connect(self.chooseimage)
        self.BrowseFolder.clicked.connect(self.choosefolder)
        self.DisplaycomboBox.currentTextChanged.connect(self.presetchanged)
        self.DisplayRatioBox.stateChanged.connect(lambda _: self.upscalerecv())
        self.comboBox_2.currentTextChanged.connect(self.downscalechanged)
        self.DisplayName.textChanged.connect(self.displaynamechanged)
        self.ExtraProperties.stateChanged.connect(lambda _: self.extrasettingsvisiblite())
        self.Waitcd.valueChanged.connect(self.waitchanged)
        self.waitEvery.valueChanged.connect(self.waitEveryChanged)
        self.HowToUsebtn.clicked.connect(self.HowToUseInfo)
        self.ConvertBtn.clicked.connect(self.startconvert)
    def HowToUseInfo(self):
        QMessageBox.information(
            None,
            "How To Use img2mindustry",
            """
1. Image
- Simple image upload

2. Display Preset
- Small-Inner: For small displays with a 4-pixel margin from border
- Small-Full: For small displays without margins
- Lagre: For large displays (may contain a lot of code)

3. Downscale
- Reduces the level of detail; 1 is the highest, but may contain a lot of code

- If the checkbox is unchecked, universal resolutions are used (1, 2, 4, 8)
- If enabled, it depends on the display installed above

4. Out Folder
- Creates .mlog files in the selected folder after conversion

5. Display
- Display name where the image will be displayed

6. Extra Settings
- If enabled, special settings are shown; they are not required for conversion

7. Wait
- Delay in code

8. Waitevery
- How many delays there will be every N lines

IMPORTANT!
if after converting several files, Run the prog_01.mlog first in processor and wait for the initial draw render, then run the others.

"""
        )
    def waitchanged(self, value):
        self.WaitFloat = value
        print(self.WaitFloat)

    def waitEveryChanged(self, value):
        self.WaitEveryInt = value
        print(self.WaitFloat)
        
    def presetchanged(self, text):
        self.preset = text
        print(self.preset)
        self.upscalerecv()
    
    def downscalechanged(self, text):
        self.downscale = text
        print(self.downscale)
    
    def displaynamechanged(self, text):
        self.DisplayNameStr = text
        print(self.DisplayNameStr)
        self.checkforconvertation()

    def upscalerecv(self):
        print("preset =", repr(self.preset))
        print("checkbox =", self.DisplayRatioBox.isChecked())
        if self.DisplayRatioBox.isChecked(): # если да
            if self.preset == "small-inner": # маленький с отступом
                self.comboBox_2.clear()
                self.comboBox_2.addItems(["1", "2", "4", "5", "8", "10", "16", "20", "40", "80"])
            elif self.preset == "small-full": # маленький без отступов 
                self.comboBox_2.clear()
                self.comboBox_2.addItems(["1", "2", "4", "8", "11", "22", "44", "88"])
            elif self.preset == "large": # большой дисплей
                self.comboBox_2.clear()
                self.comboBox_2.addItems(["1", "2", "4", "8", "16", "11", "22", "44", "88", "176"])
        else: # если нет
            self.comboBox_2.clear()
            self.comboBox_2.addItems(["1", "2", "4", "8"]) # универсальные
        

    def extrasettingsvisiblite(self):
        if self.ExtraProperties.isChecked():
            self.label_7.show()
            self.Waitcd.show()
            self.label_8.show()
            self.waitEvery.show()
        else:
            self.label_7.hide()
            self.Waitcd.hide()
            self.label_8.hide()
            self.waitEvery.hide()
            
    
    def checkforconvertation(self):
        if self.folder_path != "" and self.file_path != "" and self.DisplayNameStr != "":
            self.ConvertBtn.setEnabled(True)
        else:
            self.ConvertBtn.setEnabled(False)
            
    def startconvert(self):
        if self.ExtraProperties.isChecked():
            args = [
                str(lib_path),
                str(self.file_path),
                "--preset", str(self.preset),
                "--upscale", str(self.downscale),
                "--resample", "lanczos",
                "--colors", "48",
                "--out", str(self.folder_path),
                "--display", str(self.DisplayNameStr),
            ]
        else:
            args = [
                str(lib_path),
                str(self.file_path),
                "--preset", str(self.preset),
                "--upscale", str(self.downscale),
                "--resample", "lanczos",
                "--colors", "48",
                "--out", str(self.folder_path),
                "--display", str(self.DisplayNameStr),
                "--wait", str(self.WaitFloat),
                "--wait-every", str(self.WaitEveryInt),
            ]
        print("lib_path =", repr(lib_path))
        print("exists =", os.path.exists(lib_path))

        subprocess.run(args)
        QMessageBox.information(
            None,
            "convertation",
            """
convertation successfully!
check the out folder
"""
        )
    def chooseimage(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "choose an image",
            "",
            "image (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        if file_path:
            self.file_path = file_path
            print("Выбран файл:", self.file_path)
            self.ImagePath.setText(self.file_path)
        self.checkforconvertation()

    def choosefolder(self):
        folder_path = QFileDialog.getExistingDirectory(
            None,
            "choose an folder for mlog code(s)",
            "",
            QFileDialog.ShowDirsOnly
        )
        if folder_path:
            self.folder_path = folder_path
            print(self.folder_path)
            self.FolderPath.setText(self.folder_path)
        self.checkforconvertation()

def main():
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
