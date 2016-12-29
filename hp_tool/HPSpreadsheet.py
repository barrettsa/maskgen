from Tkinter import *
import tkFileDialog
import os
import sys
import pandas as pd
import tkMessageBox
import pandastable
import csv
from PIL import Image, ImageTk
from ErrorWindow import ErrorWindow
import hp_data


class HPSpreadsheet(Toplevel):
    def __init__(self, dir=None, ritCSV=None, master=None):
        Toplevel.__init__(self, master=master)
        self.create_widgets()
        self.dir = dir
        if self.dir:
            self.imageDir = os.path.join(self.dir, 'image')
        self.master = master
        self.ritCSV=ritCSV
        self.saveState = True
        self.kinematics = self.load_kinematics()
        self.protocol('WM_DELETE_WINDOW', self.check_save)
        w, h = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry("%dx%d+0+0" % (w, h))
        #self.attributes('-fullscreen', True)
        self.set_bindings()

    def create_widgets(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.topFrame = Frame(self)
        self.topFrame.pack(side=TOP, fill=X)
        self.rightFrame = Frame(self, width=480)
        self.rightFrame.pack(side=RIGHT, fill=Y)
        self.leftFrame = Frame(self)
        self.leftFrame.pack(side=LEFT, fill=BOTH, expand=1)
        self.pt = CustomTable(self.leftFrame, scrollregion=None, width=1024, height=720)
        self.leftFrame.pack(fill=BOTH, expand=1)
        self.pt.show()
        self.currentImageNameVar = StringVar()
        self.currentImageNameVar.set('Current Image: ')
        l = Label(self.topFrame, height=1, textvariable=self.currentImageNameVar)
        l.pack(fill=BOTH, expand=1)

        image = Image.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'RedX.png'))
        image.thumbnail((250,250))
        self.photo = ImageTk.PhotoImage(image)
        self.l2 = Button(self.rightFrame, image=self.photo, command=self.open_image)
        self.l2.image = self.photo  # keep a reference!
        self.l2.pack(side=TOP)

        self.validateFrame = Frame(self.rightFrame, width=480)
        self.validateFrame.pack(side=BOTTOM)
        self.currentColumnLabel = Label(self.validateFrame, text='Current column:')
        self.currentColumnLabel.grid(row=0, column=0, columnspan=2)
        lbl = Label(self.validateFrame, text='Valid values for cells in this column:').grid(row=1, column=0, columnspan=2)
        self.vbVertScroll = Scrollbar(self.validateFrame)
        self.vbVertScroll.grid(row=2, column=1, sticky='NS')
        self.vbHorizScroll = Scrollbar(self.validateFrame, orient=HORIZONTAL)
        self.vbHorizScroll.grid(row=3, sticky='WE')
        self.validateBox = Listbox(self.validateFrame, xscrollcommand=self.vbHorizScroll.set, yscrollcommand=self.vbVertScroll.set, selectmode=SINGLE, width=50, height=14)
        self.validateBox.grid(row=2, column=0)
        self.vbVertScroll.config(command=self.validateBox.yview)
        self.vbHorizScroll.config(command=self.validateBox.xview)

        self.menubar = Menu(self)
        self.fileMenu = Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="File", menu=self.fileMenu)
        self.fileMenu.add_command(label='Save', command=self.exportCSV, accelerator='ctrl-s')
        self.fileMenu.add_command(label='Load image directory', command=self.load_images)
        self.fileMenu.add_command(label='Validate', command=self.validate)

        self.editMenu = Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label='Edit', menu=self.editMenu)
        self.editMenu.add_command(label='Fill Down', command=self.fill_down, accelerator='ctrl-d')
        self.editMenu.add_command(label='Fill True', command=self.pt.enter_true, accelerator='ctrl-t')
        self.editMenu.add_command(label='Fill False', command=self.pt.enter_false, accelerator='ctr-f')
        self.config(menu=self.menubar)

    def set_bindings(self):
        self.bind('<Key>', self.keypress)
        self.bind('<Button-1>', self.update_current_image)
        self.bind('<Left>', self.update_current_image)
        self.bind('<Right>', self.update_current_image)
        self.bind('<Return>', self.update_current_image)
        self.bind('<Up>', self.update_current_image)
        self.bind('<Down>', self.update_current_image)
        self.bind('<Control-d>', self.fill_down)
        self.bind('<Control-s>', self.exportCSV)

    def keypress(self, event):
        self.saveState = False

    def open_image(self):
        image = os.path.join(self.imageDir, self.imName)
        if sys.platform.startswith('linux'):
            os.system('xdg-open "' + image + '"')
        elif sys.platform.startswith('win'):
            os.startfile(image)
        else:
            os.system('open "' + image + '"')

    def update_current_image(self, event):
        row = self.pt.getSelectedRow()
        self.imName = str(self.pt.model.getValueAt(row, 0))
        self.currentImageNameVar.set('Current Image: ' + self.imName)
        maxSize = 480
        try:
            im = Image.open(os.path.join(self.imageDir, self.imName))
        except (IOError, AttributeError):
            im = Image.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'RedX.png'))
        if im.size[0] > maxSize or im.size[1] > maxSize:
            im.thumbnail((maxSize,maxSize), Image.ANTIALIAS)
        newimg=ImageTk.PhotoImage(im)
        self.l2.configure(image=newimg)
        self.l2.image = newimg
        self.update_valid_values()

    def update_valid_values(self):
        #self.pt.model.df.columns.get_loc('HP-OnboardFilter')
        cols = list(self.pt.model.df)
        col = self.pt.getSelectedColumn()
        currentCol = cols[col]
        self.currentColumnLabel.config(text='Current column: ' + currentCol)
        if currentCol in ['HP-OnboardFilter', 'HP-LensFilter', 'HP-Reflections', 'HP-Shadows', 'HP-HDR']:
            validValues = ['True', 'False']
        elif currentCol == 'HP-CameraKinematics':
            validValues = self.kinematics
        elif currentCol == 'HP-JpgQuality':
            validValues = ['High', 'Medium', 'Low']
        elif currentCol == 'Type':
            validValues = ['image', 'video', 'audio']

        elif currentCol in ['ImageWidth', 'ImageHeight', 'BitDepth']:
            validValues = {'instructions':'Any integer value'}
        elif currentCol in ['GPSLongitude', 'GPSLatitude']:
            validValues = {'instructions':'Coodinates, specified in decimal degree format'}
        elif currentCol == 'HP-CollectionRequestID':
            validValues = {'instructions':'Request ID for this image, if applicable'}
        elif currentCol == 'CreationDate':
            validValues = {'instructions':'Date/Time, specified as \"YYYY:MM:DD HH:mm:SS\"'}
        elif currentCol == 'FileType':
            validValues = {'instructions':'Any file extension, without the dot (.) (e.g. jpg, png)'}
        elif currentCol == 'HP-App':
            validValues = {'instructions': 'Name of phone app used to take this image'}
        elif currentCol == 'HP-LensLocalId':
            validValues = {'instructions':'Local ID number (PAR, RIT) of lens'}
        elif currentCol == 'HP-DeviceLocalID':
            validValues = {'instructions': 'Local ID number (PAR, RIT) of device'}
        elif currentCol == 'CameraModel':
            validValues = {'instructions':'Manufacturer camera model number'}
        else:
            validValues = {'instructions':'Any string of text'}

        self.validateBox.delete(0, END)
        if type(validValues) == dict:
            self.validateBox.insert(END, validValues['instructions'])
            self.validateBox.unbind('<<ListboxSelect>>')
        else:
            for v in validValues:
                self.validateBox.insert(END, v)
            self.validateBox.bind('<<ListboxSelect>>', self.insert_item)

    def insert_item(self, event=None):
        selection = event.widget.curselection()
        val = event.widget.get(selection[0])
        row = self.pt.getSelectedRow()
        col = self.pt.getSelectedColumn()
        self.pt.model.setValueAt(val, row, col)
        self.pt.redraw()

    def load_images(self):
        self.imageDir = tkFileDialog.askdirectory(initialdir=self.dir)
        self.focus_set()

    def open_spreadsheet(self):
        if self.dir and not self.ritCSV:
            self.csvdir = os.path.join(self.dir, 'csv')
            for f in os.listdir(self.csvdir):
                if f.endswith('.csv') and 'rit' in f:
                    self.ritCSV = os.path.join(self.csvdir, f)
        self.title(self.ritCSV)
        self.pt.importCSV(self.ritCSV)

        self.obfiltercol = self.pt.model.df.columns.get_loc('HP-OnboardFilter')
        try:
            self.reflectionscol = self.pt.model.df.columns.get_loc('HP-Reflections')
            self.shadcol = self.pt.model.df.columns.get_loc('HP-Shadows')
        except KeyError:
            self.reflectionscol = self.pt.model.df.columns.get_loc('Reflections')
            self.shadcol = self.pt.model.df.columns.get_loc('Shadows')
        self.modelcol = self.pt.model.df.columns.get_loc('CameraModel')
        self.hdrcol = self.pt.model.df.columns.get_loc('HP-HDR')
        self.kincol = self.pt.model.df.columns.get_loc('HP-CameraKinematics')

        self.color_code_cells()

    def color_code_cells(self):
        notnans = self.pt.model.df.notnull()
        redcols = [self.obfiltercol, self.reflectionscol, self.shadcol, self.modelcol, self.hdrcol]
        videoonlycols = [self.kincol]
        for row in range(0, self.pt.rows):
            for col in range(0, self.pt.cols):
                currentExt = os.path.splitext(self.pt.model.getValueAt(row,0))[1].lower()
                x1, y1, x2, y2 = self.pt.getCellCoords(row, col)
                if col in redcols or (col in videoonlycols and currentExt in hp_data.exts['VIDEO']):
                    rect = self.pt.create_rectangle(x1, y1, x2, y2,
                                                    fill='#ff5b5b',
                                                    outline='#084B8A',
                                                    tag='cellrect')
                else:
                    x1, y1, x2, y2 = self.pt.getCellCoords(row, col)
                    if notnans.iloc[row, col]:
                        rect = self.pt.create_rectangle(x1, y1, x2, y2,
                                                        fill='#c1c1c1',
                                                        outline='#084B8A',
                                                        tag='cellrect')

                self.pt.lift('cellrect')
        self.pt.redraw()

    def exportCSV(self, showErrors=True):
        self.pt.redraw()
        if showErrors:
            self.validate()
        self.pt.doExport(self.ritCSV)
        tmp = self.ritCSV + '-tmp.csv'
        with open(self.ritCSV, 'rb') as source:
            rdr = csv.reader(source)
            with open(tmp, 'wb') as result:
                wtr = csv.writer(result)
                for r in rdr:
                    wtr.writerow((r[1:]))
        os.remove(self.ritCSV)
        os.rename(tmp, self.ritCSV)
        self.saveState = True
        msg = tkMessageBox.showinfo('Status', 'Saved!')

    def fill_down(self, event=None):
        selection = self.pt.getSelectionValues()
        cells = self.pt.getSelectedColumn
        rowList = range(cells.im_self.startrow, cells.im_self.endrow + 1)
        colList = range(cells.im_self.startcol, cells.im_self.endcol + 1)
        for row in rowList:
            for col in colList:
                try:
                    self.pt.model.setValueAt(selection[0][0], row, col)
                except IndexError:
                    pass
        self.pt.redraw()

    def validate(self):
        errors = []
        booleanCols = [self.obfiltercol, self.reflectionscol, self.shadcol, self.hdrcol]
        for col in range(0, self.pt.cols):
            if col in booleanCols:
                for row in range(0, self.pt.rows):
                    val = str(self.pt.model.getValueAt(row, col))
                    if val.title() == 'True' or val.title() == 'False':
                        self.pt.model.setValueAt(val.title(), row, col)
                    else:
                        currentColName = list(self.pt.model.df.columns.values)[col]
                        errors.append('Invalid entry at column ' + currentColName + ', row ' + str(
                            row + 1) + '. Value must be True or False')

        errors.extend(self.check_model())
        errors.extend(self.check_kinematics())

        if errors:
            ErrorWindow(errors).show_errors()

        return errors

    def check_save(self):
        if self.saveState == False:
            message = 'Would you like to save before closing this sheet?'
            confirm = tkMessageBox.askyesnocancel(title='Save On Close', message=message, default=tkMessageBox.YES)
            if confirm:
                errs = self.exportCSV(showErrors=False)
                if not errs:
                    self.destroy()
            elif confirm is None:
                pass
            else:
                self.destroy()
        else:
            self.destroy()

    def load_kinematics(self):
        try:
            dataFile = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'Kinematics.csv')
            df = pd.read_csv(dataFile)
        except IOError:
            tkMessageBox.showwarning('Warning', 'Camera kinematics reference not found!')
            return []

        return [x.lower().strip() for x in df['Camera Kinematics']]

    def check_kinematics(self):
        errors = []
        cols_to_check = [self.kincol]
        for col in range(0, self.pt.cols):
            if col in cols_to_check:
                for row in range(0, self.pt.rows):
                    val = str(self.pt.model.getValueAt(row, col))
                    if val.lower() == 'nan' or val == '':
                        imageName = self.pt.model.getValueAt(row, 0)
                        errors.append('No camera kinematic entered for ' + imageName + ' (row ' + str(row + 1) + ')')
                    elif val.lower() not in self.kinematics:
                        errors.append('Invalid camera kinetickinetic ' + val + ' (row ' + str(row + 1) + ')')
        return errors

    def check_model(self):
        errors = []
        try:
            dataFile = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'Devices.csv')
            df = pd.read_csv(dataFile)
        except IOError:
            tkMessageBox.showwarning('Warning', 'Camera model reference not found!')
            return

        data = [x.lower().strip() for x in df['SeriesModel']]
        cols_to_check = [self.modelcol]
        for col in range(0, self.pt.cols):
            if col in cols_to_check:
                for row in range(0, self.pt.rows):
                    val = str(self.pt.model.getValueAt(row, col))
                    if val.lower() == 'nan' or val == '':
                        imageName = self.pt.model.getValueAt(row, 0)
                        errors.append('No camera model entered for ' + imageName + ' (row ' + str(row + 1) + ')')
                    elif val.lower() not in data:
                        errors.append('Invalid camera model ' + val + ' (row ' + str(row + 1) + ')')
        return errors


class CustomTable(pandastable.Table):
    def __init__(self, master, **kwargs):
        pandastable.Table.__init__(self, parent=master, **kwargs)

    def doBindings(self):
        """Bind keys and mouse clicks, this can be overriden"""

        self.bind("<Button-1>", self.handle_left_click)
        self.bind("<Double-Button-1>", self.handle_double_click)
        self.bind("<Control-Button-1>", self.handle_left_ctrl_click)
        self.bind("<Shift-Button-1>", self.handle_left_shift_click)

        self.bind("<ButtonRelease-1>", self.handle_left_release)
        if self.ostyp == 'mac':
            # For mac we bind Shift, left-click to right click
            self.bind("<Button-2>", self.handle_right_click)
            self.bind('<Shift-Button-1>', self.handle_right_click)
        else:
            self.bind("<Button-3>", self.handle_right_click)

        self.bind('<B1-Motion>', self.handle_mouse_drag)
        # self.bind('<Motion>', self.handle_motion)

        self.bind("<Control-c>", self.copy)
        # self.bind("<Control-x>", self.deleteRow)
        # self.bind_all("<Control-n>", self.addRow)
        self.bind("<Delete>", self.clearData)
        self.bind("<Control-v>", self.paste)
        self.bind("<Control-a>", self.selectAll)

        self.bind("<Right>", self.handle_arrow_keys)
        self.bind("<Left>", self.handle_arrow_keys)
        self.bind("<Up>", self.handle_arrow_keys)
        self.bind("<Down>", self.handle_arrow_keys)
        self.parentframe.master.bind_all("<KP_8>", self.handle_arrow_keys)
        self.parentframe.master.bind_all("<Return>", self.handle_arrow_keys)
        self.parentframe.master.bind_all("<Tab>", self.handle_arrow_keys)
        # if 'windows' in self.platform:
        self.bind("<MouseWheel>", self.mouse_wheel)
        self.bind('<Button-4>', self.mouse_wheel)
        self.bind('<Button-5>', self.mouse_wheel)

        #######################################
        self.bind('<Control-Key-t>', self.enter_true)
        self.bind('<Control-Key-f>', self.enter_false)
        #self.bind('<Return>', self.handle_double_click)
        ########################################

        self.focus_set()
        return

    def enter_true(self, event):
        for row in range(self.startrow,self.endrow+1):
            for col in range(self.startcol, self.endcol+1):
                self.model.setValueAt('True', row, col)
        self.redraw()

    def enter_false(self, event):
        # row = self.get_row_clicked(event)
        # col = self.get_col_clicked(event)
        for row in range(self.startrow,self.endrow+1):
            for col in range(self.startcol, self.endcol+1):
                self.model.setValueAt('False', row, col)
        self.redraw()

    def move_selection(self, event, direction='down', entry=False):
        row = self.getSelectedRow()
        col = self.getSelectedColumn()
        if direction == 'down':
            self.currentrow += 1
        elif direction == 'up':
            self.currentrow -= 1
        elif direction == 'left':
            self.currentcol -= 1
        else:
            self.currentcol += 1

        if entry:
            self.drawCellEntry(self.currentrow, self.currentcol)

    def handle_arrow_keys(self, event, entry=False):
        """Handle arrow keys press"""
        # print event.keysym

        # row = self.get_row_clicked(event)
        # col = self.get_col_clicked(event)
        x, y = self.getCanvasPos(self.currentrow, 0)
        if x == None:
            return

        if event.keysym == 'Up':
            if self.currentrow == 0:
                return
            else:
                # self.yview('moveto', y)
                # self.rowheader.yview('moveto', y)
                self.currentrow = self.currentrow - 1
        elif event.keysym == 'Down' or event.keysym == 'Return':
            if self.currentrow >= self.rows - 1:
                return
            else:
                # self.yview('moveto', y)
                # self.rowheader.yview('moveto', y)
                self.currentrow = self.currentrow + 1
        elif event.keysym == 'Right' or event.keysym == 'Tab':
            if self.currentcol >= self.cols - 1:
                if self.currentrow < self.rows - 1:
                    self.currentcol = 0
                    self.currentrow = self.currentrow + 1
                else:
                    return
            else:
                self.currentcol = self.currentcol + 1
        elif event.keysym == 'Left':
            self.currentcol = self.currentcol - 1
        self.drawSelectedRect(self.currentrow, self.currentcol)
        coltype = self.model.getColumnType(self.currentcol)
        # if coltype == 'text' or coltype == 'number':
        #    self.delete('entry')
        #    self.drawCellEntry(self.currentrow, self.currentcol)
        self.startrow = self.currentrow
        self.endrow = self.currentrow
        self.startcol = self.currentcol
        self.endcol = self.currentcol
        return

    def gotonextCell(self):
        """Move highlighted cell to next cell in row or a new col"""

        if hasattr(self, 'cellentry'):
            self.cellentry.destroy()
        self.currentrow = self.currentrow+1
        # if self.currentcol >= self.cols-1:
        #     self.currentcol = self.currentcol+1
        self.drawSelectedRect(self.currentrow, self.currentcol)
        return

    def importCSV(self, filename=None, dialog=False):
        """Import from csv file"""

        if self.importpath == None:
            self.importpath = os.getcwd()
        if filename == None:
            filename = tkFileDialog.askopenfilename(parent=self.master,
                                                          defaultextension='.csv',
                                                          initialdir=self.importpath,
                                                          filetypes=[("csv","*.csv"),
                                                                     ("tsv","*.tsv"),
                                                                     ("txt","*.txt"),
                                                            ("All files","*.*")])
        if not filename:
            return
        if dialog == True:
            df = None
        else:
            df = pd.read_csv(filename, dtype=str, quoting=1)
        model = pandastable.TableModel(dataframe=df)
        self.updateModel(model)
        self.redraw()
        self.importpath = os.path.dirname(filename)
        return