from PySide6.QtCore import (
    Qt,
    QRunnable,
    QThreadPool,
    Signal,
    QObject,
)
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QPushButton,
    QLineEdit,
    QLabel,
    QTreeWidget,
    QTreeWidgetItem,
    QScrollArea,
    QFrame,
    QComboBox,
    QListView,
    QGridLayout,
    QButtonGroup,
    QRadioButton,
    QGroupBox,
    QDialog
)
from os import environ
from sys import argv
from typing import Literal, List
from wolframalpha import Client as wf_client
from pyttsx3 import Engine as ttse
import speech_recognition as sr
from unidecode import unidecode as vh
from json import dump as json_dump, load as json_load
from io import BytesIO

class MainWindow(QMainWindow):
    class QToggleButton(QPushButton):
        def __init__(self, text: str | tuple = "", style_class: str = "", toggle_callback: callable = None):
            self.toggle_text = text if isinstance(text, tuple) else None
            super().__init__(text[0] if self.toggle_text else text)
            self.is_checked = False
            self.callback = toggle_callback
            self.base_class = style_class
            with open('styles.qss', 'r') as f: self.style_sheet = f.read()
            self.setProperty('class', self.base_class)
            self.clicked.connect(self._clicked)
        
        def _clicked(self, *args):
            # Chuyển var trạng thái
            self.is_checked = not self.is_checked

            # On: Accent, Off: bình thường
            self.setProperty('class', f"{self.base_class}{' accent' if self.is_checked else ''}")
            self.setStyleSheet(self.style_sheet) # Cập nhật style

            # Đổi text
            if self.toggle_text: self.setText(self.toggle_text[1] if self.is_checked else self.toggle_text[0])

            # Gọi và pass state cho callback
            if self.callback: self.callback(self.is_checked)
    
    # CLASS Worker
    def Worker(self, func: callable, progress_callback: callable = None, result_callback: callable = None, error_callback: callable = None, *args):
        main = self
        class Worker(QRunnable):
            class WorkerSignals(QObject):
                progress = Signal(str)
                result = Signal(str)
                error = Signal(str)

            def __init__(self, func: callable, progress_callback: callable = None, result_callback: callable = None, error_callback: callable = None, *args) -> None:
                super().__init__()
                self.func = func
                self.signals = self.WorkerSignals()
                self.args = args
                self.progress_callback = progress_callback
                self.result_callback = result_callback
                self.error_callback = error_callback
                if self.progress_callback: self.signals.progress.connect(self.progress_callback)
                if self.result_callback: self.signals.result.connect(self.result_callback)
                if self.error_callback: self.signals.error.connect(self.error_callback)

                main.thread_pool.start(self)
            
            def run(self) -> None:
                match self.progress_callback, self.error_callback, self.result_callback:
                    case None, None, None:
                        self.func(*self.args)
                    case _, None, None:
                        self.func(self.signals.progress.emit, *self.args)
                    case None, _, None:
                        self.func(self.signals.error.emit, *self.args)
                    case None, None, _:
                        self.signals.result.emit(self.func(*self.args))
                    case _, _, None:
                        self.func(self.signals.progress.emit, self.signals.error.emit *self.args)
                    case _, None, _:
                        self.signals.result.emit(self.func(self.signals.progress.emit, *self.args))     
                    case None, _, _:
                        self.signals.result.emit(self.func(self.signals.error.emit, *self.args))
                    case _:
                        self.signals.result.emit(self.func(self.signals.progress.emit, self.signals.error.emit, *self.args))
                if self.progress_callback: main.infobar.update()

        return Worker(func, progress_callback, result_callback, error_callback, *args)

    def __init__(self) -> None:
        super().__init__()
        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(1)
        with open('styles.qss', 'r') as f:
            self.style_sheet = f.read()
        self.setWindowTitle("Phần mềm Quản lý Học sinh")
        # self.setMinimumSize(400, 700)  # Without the SCALE_FACTOR
        self.setMinimumSize(300, 500)
        self.setGeometry(50, 30, 300, 500)
        self.setStyleSheet(self.style_sheet)
        self.ai = self.AI()
        self.init_layout()
        # Init later, dependency problems
        self.ai.init_popup()
        
        for message in [
            "Hello everybody, I'm Kay",
            "I'm so happy to attend this Final Teky Tech Master 2022"
        ]:
            self.messages.sent(message, 'a')

    # CLASS AI
    def AI(self):
        main = self
        class AI:
            class EditDialog(QDialog):
                class _ComboBox(QComboBox):
                    def __init__(self) -> None:
                        super().__init__()
                        self.setView(QListView())
                        self.view().window().setWindowFlags(Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
                        self.view().window().setAttribute(Qt.WA_TranslucentBackground)

                def __init__(self) -> None:
                    super().__init__()
                    self.setModal(1)
                    self.setWindowTitle("Tạo học sinh mới")
                    self.resize(300, 200)
                    self.setStyleSheet(main.style_sheet)
                    self.rejected.connect(self.__cancel)
                    self.__init_widgets()

                def load(self, _class: str, name: str, gender: str, grade_lit: str, grade_math: str, grade_eng: str) -> None:
                    self.class_combobox.setCurrentText(_class)
                    self.name_entry.setText(name)
                    if gender == "Nam":
                        self.gender_male.setChecked(1)
                    else:
                        self.gender_female.setChecked(1)
                    self.grade_entry_lit.setText(grade_lit)
                    self.grade_entry_math.setText(grade_math)
                    self.grade_entry_eng.setText(grade_eng)

                def __accept(self):
                    try:
                        data = self.__get_info()
                    except:
                        main.messages.sent("Please enter all the infomations required", 's')
                    else:
                        main.ai.control_centre(False, *data)
                        self.__clear_form()
                        self.accept()
                
                def __cancel(self):
                    main.ai.control_centre(True)
                    self.__clear_form()
                
                def __get_info(self):
                    def verify(value):
                        # Check if value are empty or not
                        if value: return value
                        raise ValueError('Some QLineEdit are not entered')
                        
                    _class = self.class_combobox.currentText()
                    name = verify(self.name_entry.text())
                    gender = self.gender_group.checkedButton().text()
                    lit = verify(self.grade_entry_lit.text())
                    math = verify(self.grade_entry_math.text())
                    eng = verify(self.grade_entry_eng.text())
                    return _class, name, gender, lit, math, eng
                
                def __clear_form(self):
                    self.class_combobox.setCurrentIndex(-1)
                    self.name_entry.clear()
                    self.gender_group.checkedButton().setChecked(0)
                    self.grade_entry_lit.clear()
                    self.grade_entry_math.clear()
                    self.grade_entry_eng.clear()
                
                def __init_widgets(self):
                    layout = QGridLayout()
                    self.setLayout(layout)

                    class_label = QLabel('Lớp:')
                    self.class_combobox = self._ComboBox()
                    self.class_combobox.insertItems(0, main.sidebar.student_table.get_classes())
                    self.class_combobox.setCurrentIndex(-1)
                    layout.addWidget(class_label, 0, 0)
                    layout.addWidget(self.class_combobox, 0, 1)

                    name_label = QLabel('Tên:')
                    self.name_entry = QLineEdit()
                    self.name_entry.setPlaceholderText('Họ và tên')
                    layout.addWidget(name_label, 1, 0)
                    layout.addWidget(self.name_entry, 1, 1)

                    gender_label = QLabel("Giới tính:")
                    Cgender = QWidget()
                    Lgender = QVBoxLayout()
                    Lgender.setAlignment(Qt.AlignLeft)
                    Cgender.setLayout(Lgender)
                    self.gender_group = QButtonGroup(Cgender)
                    self.gender_male = QRadioButton('Nam')
                    self.gender_female = QRadioButton('Nữ')
                    Lgender.addWidget(self.gender_male)
                    Lgender.addWidget(self.gender_female)
                    self.gender_group.addButton(self.gender_male)
                    self.gender_group.addButton(self.gender_female)
                    layout.addWidget(gender_label, 2, 0)
                    layout.addWidget(Cgender, 2, 1)

                    Lgrade = QHBoxLayout()
                    grade_box = QGroupBox('Điểm')
                    grade_box.setLayout(Lgrade)
                    self.grade_entry_lit = QLineEdit()
                    self.grade_entry_lit.setPlaceholderText("Văn")
                    self.grade_entry_math = QLineEdit()
                    self.grade_entry_math.setPlaceholderText("Toán")
                    self.grade_entry_eng = QLineEdit()
                    self.grade_entry_eng.setPlaceholderText("Anh")
                    Lgrade.addWidget(self.grade_entry_lit)
                    Lgrade.addWidget(self.grade_entry_math)
                    Lgrade.addWidget(self.grade_entry_eng)
                    layout.addWidget(grade_box, 3, 0, 1, 2)

                    layout.setRowMinimumHeight(4, 20)

                    confirm = QPushButton("Xác nhận")
                    confirm.setProperty('class', 'accent')
                    confirm.setMinimumWidth(100)
                    confirm.clicked.connect(self.__accept)
                    cancel = QPushButton("Hủy bỏ")
                    cancel.setMinimumWidth(70)
                    cancel.clicked.connect(self.close)
                    layout.addWidget(confirm, 5, 1, Qt.AlignRight)
                    layout.addWidget(cancel, 5, 0)

            class DeleteDialog(QDialog):
                def __init__(self):
                    super().__init__()
                    self.rejected.connect(self.__cancel)
                    self.setWindowTitle("Xác nhận")
                    self.setFixedSize(300, 100)
                    self.setStyleSheet(main.style_sheet)
                    self.__init_widgets()

                def __init_widgets(self):
                    layout = QGridLayout()
                    self.setLayout(layout)

                    self.message = QLabel()
                    self.message.setWordWrap(1)
                    layout.addWidget(self.message, 0, 0, 1, 2, Qt.AlignTop)

                    confirm = QPushButton("Xóa")
                    confirm.setMinimumWidth(60)
                    confirm.setProperty('class', 'accent')
                    confirm.clicked.connect(self.__accept)
                    cancel = QPushButton("Hủy bỏ")
                    cancel.setMinimumWidth(80)
                    cancel.clicked.connect(self.close)
                    layout.addWidget(confirm, 1, 1, Qt.AlignRight)
                    layout.addWidget(cancel, 1, 0)
                
                def load(self, name: str) -> None:
                    self.message.setText(f'Toàn bộ thông tin của học sinh {name} sẽ bị xóa vĩnh viễn. Bạn có chắc chắn muốn xóa?')
                
                def __cancel(self):
                    main.ai.control_centre(True)
                
                def __accept(self):
                    main.ai.control_centre(False)
                    self.accept()

            def __init__(self) -> None:
                self.WF = wf_client('3WX9HU-3G9A2TGPTY')
                self.table_mode = ''
                # Use to revert back to original state when Editing is discarded
                self.edit_cache = None
                self.delete_dialog = self.DeleteDialog()
                self.preset = {
                    'name': "I'm Kayleigh",
                }

            # Resolve dependency problem
            def init_popup(self) -> None: self.edit_dialog = self.EditDialog()

            def control_centre(self, cancel: bool = True, *data):
                match cancel, self.table_mode:
                    case True, '':
                        main.messages.sent("You've canceled the current student creating process", 's')

                    case True, 'edit':
                        main.messages.sent("Changes you made is discarded", 's')
                        self.mode_switcher('')

                    case True, 'delete':
                        main.messages.sent(f"{vh(self.edit_cache[1])} will not be deleted", 's')
                        self.mode_switcher('')

                    case False, '':
                        main.sidebar.student_table.add_student(*data)
                        main.messages.sent(f"{vh(data[1])} were added to {vh(data[0])}", 'a')

                    case False, 'edit':
                        main.sidebar.student_table.del_student(self.edit_cache[0], self.edit_cache[1])
                        main.sidebar.student_table.add_student(*data)
                        main.messages.sent(f"Student {vh(data[1])} edited", 'a')
                        self.mode_switcher('')

                    case False, 'delete':
                        main.sidebar.student_table.del_student(self.edit_cache[0], self.edit_cache[1])
                        main.sidebar.student_table.update_data()
                        main.messages.sent(f"{vh(self.edit_cache[1])} has been deleted", 'a')
                        self.mode_switcher('')
            
            def table_selected(self, item: QTreeWidgetItem, *args) -> None:
                if item.childCount() != 0 or not self.table_mode:
                    return
                
                _class = item.parent().text(0)
                data = [item.text(i) for i in range(5)]
                self.edit_cache = [_class, *data]
                if self.table_mode == 'edit':
                    self.edit_dialog.load(_class, *data)
                    self.edit_dialog.show()
                else:
                    self.delete_dialog.load(data[0])
                    self.delete_dialog.show()

            def mode_switcher(self, state: str = ''):
                self.table_mode = state
                # If '' then False, 'edit' and 'delete' convert to True
                lock = bool(state)
                main.toolbar.setDisabled(lock)
                main.sidebar.sidebar_toggle.setDisabled(lock)
            
            def reply(self, message: str):
                def ai_reply(callback: callable):  # WOLFRAM ALPHA
                    callback("Processing...")
                    results = list(self.WF.query(message).results)
                    result = min(results, key=lambda x: len(x['subpod']['plaintext']))
                    if result:
                        return result['subpod']['plaintext']
                    else: return "I can't quite answer what you're asking"
                
                message = message.lower()
                for keyword, answer in self.preset.items():
                    if keyword in message:
                        return main.messages.sent(answer, 'a')
                # Student editing
                if 'add' in message:
                    main.messages.sent('Enter student infomation in this form', 'a')
                    self.edit_dialog.show()
                elif 'edit' in message:
                    main.messages.sent('Select student you want to edit from the list', 'a')
                    if not main.sidebar.sidebar_toggle.is_checked: main.sidebar.sidebar_toggle._clicked()
                    self.mode_switcher('edit')
                elif 'delete' in message:
                    main.messages.sent('Select student you want to delete from the list', 'a')
                    if not main.sidebar.sidebar_toggle.is_checked: main.sidebar.sidebar_toggle._clicked()
                    self.mode_switcher('delete')
                else:
                    main.Worker(ai_reply, main.infobar.update, lambda x: main.messages.sent(x, 'a'))

        return AI()

    # CLASS Toolbar
    def Toolbar(self):
        main = self
        class Toolbar(QWidget):

            def __init__(self):
                super().__init__()
                self.sre = sr.Recognizer()
                self.running = False
                # self.sre.adjust_for_ambient_noise()
                self.init_layout()
            
            def voice(self, is_checked: bool):
                def command(callback: callable, failed: callable):  # SPEECH RECOGNITION
                    nonlocal self
                    callback("Initializing...")
                    with sr.Microphone() as mic:
                        frames = BytesIO()
                        callback("Listening...")
                        while True:
                            buffer = mic.stream.read(mic.CHUNK)
                            frames.write(buffer)
                            if not self.running: break
                    callback('Processing...')
                    frame_data = frames.getvalue()
                    frames.close()
                    audio = sr.AudioData(frame_data, mic.SAMPLE_RATE, mic.SAMPLE_WIDTH)
                    try:
                        return self.sre.recognize_google(audio, language='en-vi')
                    except:
                        failed("I can't hear what you're saying")
                    
                if is_checked:
                    self.running = True
                else: 
                    self.running = False
                    return

                main.Worker(command, main.infobar.update, main.messages.sent, lambda x: main.messages.sent(x, 'a'))

            def sent(self):
                main.messages.sent(self.input_text.text())
                self.input_text.clear()
            
            def init_layout(self):
                self.setLayout(QHBoxLayout())
                self.layout().setContentsMargins(5, 0, 5, 0)
                self.setMaximumHeight(55)
                self.input_text = QLineEdit()
                self.input_text.setPlaceholderText("Input text")
                sent_button = QPushButton(text='\ue725')
                sent_button.setProperty('class', 'icon_button')
                sent_button.clicked.connect(self.sent)
                voice_button = main.QToggleButton(('\uf8b1', '\uf8ae'), 'icon_button accent', self.voice)

                self.layout().addWidget(self.input_text)
                self.layout().addWidget(sent_button)
                self.layout().addWidget(voice_button)
            
        return Toolbar()
    
    # CLASS Messages
    def Messages(self):
        main = self
        class Messages(QScrollArea):
            def __init__(self):
                super().__init__()
                self.container = QWidget()
                self.ttse = ttse()
                # Set voice to female
                self.ttse.setProperty('voice', self.ttse.getProperty('voices')[1].id)
                self.init_layout()
            
            def say(self, message: str) -> None:  # TEXT TO SPEECH
                def command():
                    self.ttse.say(message)
                    self.ttse.runAndWait()
                main.Worker(command)
            
            def init_layout(self):
                self.container.setLayout(QVBoxLayout())
                self.container.layout().setAlignment(Qt.AlignBottom)
                self.setWidget(self.container)
                self.setWidgetResizable(1)
                self.verticalScrollBar().rangeChanged.connect(lambda _, max: self.verticalScrollBar().setSliderPosition(max))
            
            def sent(self, message = False, host: Literal['u', 's', 'a'] = 'u'):
                """
                'u': User
                's': System
                'a': Kayleigh - AI
                """
                def build_widget():
                    align = Qt.AlignRight if host == 'User' else Qt.AlignLeft
                    lhost = QLabel(host)
                    lhost.setProperty('class', 'sender')
                    lmessage = QLabel(message)
                    lmessage.setWordWrap(1)
                    lmessage.setFixedSize(lmessage.sizeHint())
                    widget_layout = QVBoxLayout()
                    widget_container = QWidget()
                    widget_container.setProperty('class', f"message {'user' if host == 'User' else 'ai'}")
                    widget_layout.addWidget(lhost, alignment=align)
                    widget_layout.addWidget(lmessage)
                    widget_container.setLayout(widget_layout)
                    self.container.layout().addWidget(widget_container, alignment=align)
                if not message: return
                host = {'u': 'User', 's': 'System', 'a': 'Kayleigh - AI'}.get(host)
                build_widget()
                if host == 'User':
                    main.ai.reply(message)
                if host == "Kayleigh - AI":
                    self.say(message)

        return Messages()

    # CLASS Infobar
    def Infobar(self):
        main = self
        class Infobar(QLabel):
            def __init__(self):
                super().__init__()
                self.setProperty('class', 'infobar')
                self.update()
            
            def update(self, text: str = 'Input text to tap voice button'):
                self.setText(text)
                super().update()
        return Infobar()
    
    # CLASS Sidebar
    def Sidebar(self):
        main = self
        class Sidebar(QFrame):

            class StudentTable(QTreeWidget):
                class ClassItem(QTreeWidgetItem):
                    # Used to exclude thís Row from sorting
                    def __lt__(self, other):
                        return False

                def __init__(self) -> None:
                    super().__init__()
                    self.data = {}
                    self.itemDoubleClicked.connect(main.ai.table_selected)
                    with open('data.json', 'r', encoding='utf-8') as file:
                        self.data = json_load(file)
                    self.__init_layout()
                    self.update_data()
                
                def __init_layout(self):
                    self.setAnimated(True)
                    self.setSortingEnabled(True)
                    self.setColumnCount(5)
                    self.setHeaderLabels(["Tên", "Giới tính", "Văn", "Toán", "Anh"])
                    self.setColumnWidth(0, 170)
                    self.setColumnWidth(1, 60)
                    self.setColumnWidth(2, 35)
                    self.setColumnWidth(3, 35)
                    self.setColumnWidth(4, 35)
                
                def get_classes(self) -> list: return self.data.keys()
                
                def add_student(self, *data):
                    self.data[data[0]][data[1]] = {
                        'giới tính': data[2],
                        'văn': data[3],
                        'toán': data[4],
                        'anh': data[5]
                    }
                    self.update_data()
                    
                def del_student(self, _class: str, name: str) -> None: del self.data[_class][name]

                def __save_to_file(self):
                    with open('data.json', 'w', encoding='utf-8') as file:
                        json_dump(self.data, file, indent=4, ensure_ascii=False)
                
                def update_data(self):
                    def save_state() -> List[bool]:
                        bool_items = []
                        for index in range(self.topLevelItemCount()):
                            bool_items.append(self.topLevelItem(index).isExpanded())
                        return bool_items
                    
                    def restore_state(states: List[bool]) -> None:
                        for state, index in zip(states, range(self.topLevelItemCount())):
                            self.topLevelItem(index).setExpanded(state)

                    states = save_state()
                    self.clear()
                    items = []
                    for _class, students in self.data.items():
                        item = self.ClassItem([_class])
                        for student_name, info in students.items():
                            item.addChild(QTreeWidgetItem([student_name, *info.values()]))
                        items.append(item)
                    self.insertTopLevelItems(0, list(reversed(items)))
                    restore_state(states)
                    self.__save_to_file()
                    
            def __init__(self):
                super().__init__()
                self.old_size = ()
                self.setProperty('class', 'sidebar')
                self.init_layout()

            def init_layout(self):
                self.setLayout(QVBoxLayout())
                self.layout().setContentsMargins(4, 4, 4, 4)
                self.layout().setAlignment(Qt.AlignTop)

                self.sidebar_toggle = main.QToggleButton(('\ue89f', '\ue8a0'), 'icon_button', self.toggle_table)
                self.layout().addWidget(self.sidebar_toggle)

                self.student_table = self.StudentTable()
                self.student_table.setHidden(1)
                self.layout().addWidget(self.student_table)
            
            def toggle_table(self, is_open: bool):
                if is_open:
                    main.Cmain.setFixedWidth(main.Cmain.width())
                    self.old_size = main.width()
                    main.resize(self.old_size + 310, main.height())
                    self.student_table.setHidden(0)
                else:
                    self.student_table.setHidden(1)
                    main.resize(self.old_size, main.height())
                    main.Cmain.setFixedSize(16777215, 16777215)  # Remove fixed size, allow widget to freely resize again
                    main.setMinimumWidth(300)
                    
        return Sidebar()

    def init_layout(self) -> None:
        """
        Variable name:
            C[name] = Container[name] {QWidget}
            L[name] = Layout[name] {*Layout}
        """
        # TODO: Reimplementing: AI, Sound, Voice to Toolbar
        Croot = QWidget()
        self.setCentralWidget(Croot)
        Lroot = QHBoxLayout()
        Croot.setLayout(Lroot)
        Lroot.setContentsMargins(0, 0, 0, 0)
        Lroot.setSpacing(0)
        
        self.Cmain = QWidget()
        Lroot.addWidget(self.Cmain)
        Lmain = QVBoxLayout()
        self.Cmain.setLayout(Lmain)
        Lmain.setContentsMargins(0, 0, 0, 0)
        self.messages = self.Messages()
        self.toolbar = self.Toolbar()
        self.infobar = self.Infobar()
        Lmain.addWidget(self.messages)
        Lmain.addWidget(self.toolbar)
        Lmain.addWidget(self.infobar)

        self.sidebar = self.Sidebar()
        Lroot.addWidget(self.sidebar)

environ['QT_SCALE_FACTOR'] = '1.4'
app = QApplication(argv)
window = MainWindow()
window.show()
app.exec()