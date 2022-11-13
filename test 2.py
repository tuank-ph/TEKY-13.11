from PySide6.QtCore import (
    Qt,
    Signal,
    QObject,
    QThreadPool,
    QRunnable
)
from PySide6.QtWidgets import (
    QMainWindow,
    QApplication,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
    QScrollArea,
    QLabel,
    QLineEdit,
    QPushButton,
)
import sys
import os
from typing import Literal
import pyttsx3 as tts
import speech_recognition as sr
import wolframalpha as wa
os.environ['QT_SCALE_FACTOR'] = '1.4'
class MainWindow(QMainWindow):
    class Worker(QRunnable):
        class WorkerSignals(QObject):
            result = Signal(str)
            progress = Signal(str)
        
        def __init__(self, command, *args) -> None:
            super().__init__()
            self.signals = self.WorkerSignals()
            self.command = command
            self.args = args
        
        def progress_update(self, message = ''):
            self.signals.progress.emit(message)

        def run(self):
            self.signals.result.emit(self.command(self.progress_update, *self.args))

    def __init__(self):
        super().__init__()
        self.setMinimumSize(300, 500)
        self.setWindowTitle("Trí tuệ nhân tạo Kay")
        self.threadpool = QThreadPool()
        self.client = wa.Client('3WX9HU-3G9A2TGPTY')
        self.ttse = tts.Engine()
        self.ttse.setProperty('voice', self.ttse.getProperty('voices')[1].id)
        with open('styles.qss', 'r') as file:
            self.setStyleSheet(file.read())
        self.set_widgets()
        for message in [
            "History of conversation will be shown in here",
            "Tap the voice button to talk",
            "Or anually input text to communicate"
        ]:
            self.sent(message, 'System')
    
    def voice(self):
        def command(callback, *args):
            callback("Initializing...")
            engine = sr.Recognizer()
            with sr.Microphone() as mic:
                callback("Listening, you can talk now")
                audio = engine.record(mic, 7)
            try:
                callback("Processing...")
                result = engine.recognize_google(audio, language='en-vi')
                callback()
                return result
            except:
                return '[failed]'
        worker = self.Worker(command)
        worker.signals.progress.connect(self.info)
        worker.signals.result.connect(self.sent)
        self.threadpool.start(worker)

    def say(self, message):
        def command(callback):
            self.ttse.say(message)
            self.ttse.runAndWait()

        worker = self.Worker(command)
        self.threadpool.start(worker)
    
    def response(self, input):
        def filter(input):
            return len(input['subpod']['plaintext'])
        def done(result):
            self.sent(result, "Kayleigh - AI")
            self.say(result)
        
        def command(callback, *args):
            for keyword, answer in {
            'name': "I'm Kayleigh",
            'created': 'I were born in 2022'
            }.items():
                if keyword in input:
                    return answer
            callback("Processing...")
            results = list(self.client.query(input).results)
            result = min(results, key=filter)
            callback()
            if result:
                return result['subpod']['plaintext']
            else: return "I can't quite answer what you're asking"

        worker = self.Worker(command)
        worker.signals.result.connect(done)
        worker.signals.progress.connect(self.info)
        self.threadpool.start(worker)
        
    
    def sent(self, message = False, host: Literal['User', 'System', 'Kayleigh - AI'] = 'User'):
        if message == "[failed]":
            self.info("I can't hear what you're saying")
            return
        if not message:
            message = self.input_text.text()
            self.input_text.clear()
        if host == 'User':
            align = Qt.AlignRight
        else:
            align = Qt.AlignLeft
        lhost = QLabel(text=host)
        lhost.setProperty('class', 'sender')
        lmessage = QLabel(text=message)
        lmessage.setWordWrap(1)
        lmessage.setFixedSize(lmessage.sizeHint())
        widget_layout = QVBoxLayout()
        widget_container = QWidget()
        if host == 'User':
            widget_container.setProperty('class', 'message user')
        else:
            widget_container.setProperty('class', 'message ai')
        widget_layout.addWidget(lhost, alignment=align)
        widget_layout.addWidget(lmessage)
        widget_container.setLayout(widget_layout)

        self.main_layout.addWidget(widget_container, alignment=align)
        if host == 'User':
            self.response(message)
            
    
    def info(self, message = False):
        if not message:
            message = "Input text to tap voice button"
        self.infobar.setText(message)

    def set_widgets(self):
        top_layout = QVBoxLayout()
        top_layout.setContentsMargins(0,0,0,0)
        top_container = QWidget()

        self.main_layout = QVBoxLayout()
        self.main_layout.setAlignment(Qt.AlignBottom)
        main_container = QWidget()
        main_scroll = QScrollArea()
        main_scroll.setWidget(main_container)
        main_scroll.setWidgetResizable(1)
        main_scroll.verticalScrollBar().rangeChanged.connect(lambda _, max: main_scroll.verticalScrollBar().setSliderPosition(max))


        toolbar_layout = QHBoxLayout()
        toolbar_container = QWidget()
        toolbar_container.setMaximumHeight(55)
        self.input_text = QLineEdit()
        self.input_text.setPlaceholderText("Input text")
        sent_button = QPushButton(text='\ue725')
        sent_button.setProperty('class', 'icon_button')
        sent_button.clicked.connect(self.sent)
        voice_button = QPushButton(text='\uf8b1')
        voice_button.clicked.connect(self.voice)
        voice_button.setProperty('class', 'icon_button accent')

        self.infobar = QLabel()
        self.info()
        self.infobar.setProperty('class', 'infobar')

        top_layout.addWidget(main_scroll)
        top_layout.addWidget(toolbar_container)
        top_layout.addWidget(self.infobar)

        toolbar_layout.addWidget(self.input_text)
        toolbar_layout.addWidget(sent_button)
        toolbar_layout.addWidget(voice_button)

        toolbar_container.setLayout(toolbar_layout)
        main_container.setLayout(self.main_layout)
        top_container.setLayout(top_layout)

        self.setCentralWidget(top_container)


app = QApplication(sys.argv)
window = MainWindow()
window.show()
app.exec()