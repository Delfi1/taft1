from PyQt6.QtCore import QElapsedTimer, QPoint, QPointF, QSize, QTimer, Qt
from PyQt6.QtGui import QAction, QIcon, QPainter
from PyQt6.QtWidgets import QApplication, QComboBox, QDialog, QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton, QSlider, QSpinBox, QVBoxLayout, QWidget
import sys, os, random, json

MIN_SPEED: int = 0
MAX_SPEED: int = 100

# Загрузка файлов с диска
def resource(relative: str):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative)

COIN_SIZE = 32
MONEY_ICON = QIcon(resource(os.path.join("assets", "money.svg")))
MONEY_PIXMAP = None

PERSON_SIZE = 125
PERSON_PIXMAP = None

MIN_Y = 50
MAX_Y = 280

class Money:
    def __init__(self, idx: int):
        self.idx = idx
        self.pos = QPointF(x_from_idx(idx), MIN_Y)
        self.speed = 0

    def tick(self, delta: float):
        y = self.pos.y() + self.speed * delta
        self.speed += MAX_Y * delta
        self.pos.setY(y)

    def is_end(self) -> bool:
        return self.pos.y() > MAX_Y

    def draw(self, painter: QPainter):
        painter.drawPixmap(self.pos, MONEY_PIXMAP)

def x_from_idx(idx: int) -> int:
    return 20 + idx*70

def svg_to_pixmap(svg_path: str, width: int, height: int) -> QPixmap:
    icon = QIcon(resource(os.path.join("assets", svg_path)))
    return icon.pixmap(QSize(width, height))

class Person:
    def __init__(self, value: int, idx: int, flag: int):
        self.wallet = value
        self.idx = idx
        x = x_from_idx(idx)
        self.pos = QPointF(x-45, MAX_Y-40)
        self.flag_pos = QPointF(x, MAX_Y+94)
        key = flag_keys[flag]
        self.flag_pixmap = svg_to_pixmap(flags_ops[key], 32, 32)

    def draw(self, painter: QPainter):
        painter.drawPixmap(self.pos, PERSON_PIXMAP)
        painter.drawPixmap(self.flag_pos, self.flag_pixmap)

        tx = int(self.pos.x()) + 60
        ty = int(self.pos.y())
        painter.drawText(tx, ty, f"{self.wallet}")

class GameFrame(QFrame):
    def __init__(self):
        super().__init__()
        self.setFixedSize(710, 400)

        self.speed = MIN_SPEED
        self.running = False
        self.paused = False
        self.finished = False
        self.count = 0

        self.frame_timer = QElapsedTimer()
        self.frame_timer.start()

        # Массив с состояниями человечков
        self.reload()

        # Массив c состояниями анимаций
        self.moneys: list[Money] = []

        self.state_label = QLabel()
        self.setStyleSheet("background-color: #262626;")
        self.setAutoFillBackground(True)

        self.btn_start = QPushButton("Старт")
        self.btn_pause = QPushButton("Пауза")
        self.btn_pause.setDisabled(True)

        self.btn_close = QPushButton("Выход")

        layout = QVBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)

        self.setLayout(layout)

    def reload(self):
        self.buf = list(start_money_values)

        self.persons = {}
        for i in range(10):
            p = Person(start_money_values[i], i, current_flags[i])
            self.persons[i] = p

    def paintEvent(self, event):
        global MONEY_PIXMAP, PERSON_PIXMAP

        super().paintEvent(event)
        if not(MONEY_PIXMAP):
            MONEY_PIXMAP = MONEY_ICON.pixmap(COIN_SIZE, COIN_SIZE)

        if not(PERSON_PIXMAP):
            icon = QIcon(resource(os.path.join("assets", "person.png")))
            PERSON_PIXMAP = icon.pixmap(PERSON_SIZE, PERSON_SIZE)

        painter = QPainter(self)

        for p in self.persons.values():
            p.draw(painter)

        for money in self.moneys:
            money.draw(painter)

        painter.end()

    def tick(self):
        if self.paused or self.finished or not self.running or self.speed == 0:
            return

        available = [i for i, value in enumerate(self.buf) if value < 10 ]

        if not available:
            self.finished = True
            return

        i = random.choice(available)

        self.moneys.append(Money(i))
        self.buf[i] += 1

        if self.buf[i] >= 10:
            self.count += 1

        self.finished = self.count >= 10

    def animations(self):
        delta = self.frame_timer.elapsed()/1000
        self.frame_timer.restart()

        if self.paused:
            return

        self.update()
        c = 0
        for m in self.moneys:
            m.tick(delta)
            if m.is_end():
                c += 1
                self.persons[m.idx].wallet += 1

        self.moneys = self.moneys[c:]

    def start(self):
        self.running = not(self.running)
        self.btn_start.setText("Старт")
        self.btn_pause.setDisabled(True)
        self.set_pause(False)
        self.moneys = []

        if self.running:
            self.btn_pause.setDisabled(False)
            self.btn_start.setText("Стоп")

    def set_pause(self, paused: bool):
        self.paused = not(paused)
        self.pause()

    def pause(self):
        self.paused = not(self.paused)
        self.state_label.setText('')
        self.btn_pause.setText("Пауза")
        if self.paused:
            self.state_label.setText("На паузе")
            self.btn_pause.setText("Продолжить")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.tickspeed = 1000
        self.setWindowTitle("Биткоины. Лабораторная 1")
        self.setFixedSize(730, 520)

        # Верхнее меню
        menubar = self.menuBar()
        menu_file = menubar.addMenu('Файл')

        self.save_file = menu_file.addAction('Открыть', self.open_sett)
        self.load_file = menu_file.addAction('Сохранить', self.load_sett)
        self.exit_file = menu_file.addAction('Выход', self.close)


        self.menu_settings = menubar.addMenu('Настройки')

        self.flags_action =  self.menu_settings.addAction('Выбор флагов', self.open_flags)
        self.ic_action = self.menu_settings.addAction('Начальные условия', self.open_ic)

        menu_help = menubar.addMenu('Помощь')

        # Основные виджеты
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        self.game = GameFrame()

        main_layout.addWidget(self.game)

        # Управление

        controls_container = QWidget()
        controls_layout = QHBoxLayout(controls_container)

        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setFixedWidth(100)
        self.speed_slider.setRange(MIN_SPEED, MAX_SPEED)
        self.speed_slider.valueChanged.connect(self.update_value)

        self.speed_field = QLineEdit(self)
        self.speed_field.textEdited.connect(self.set_value)
        self.speed_field.setFixedWidth(50);

        self.game.btn_close.clicked.connect(self.close)
        self.game.btn_start.clicked.connect(self.start)
        self.game.btn_pause.clicked.connect(self.game.pause)

        controls_layout.addWidget(self.game.state_label)
        controls_layout.addStretch()
        controls_layout.addWidget(QLabel("Скорость:"))
        controls_layout.addWidget(self.speed_slider)
        controls_layout.addSpacing(5)
        controls_layout.addWidget(self.speed_field)
        controls_layout.addSpacing(20)
        controls_layout.addWidget(self.game.btn_start)
        controls_layout.addWidget(self.game.btn_pause)
        controls_layout.addWidget(self.game.btn_close)

        main_layout.addWidget(controls_container, 0, Qt.AlignmentFlag.AlignBottom)

        # Run game loop
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.game.tick)
        self.timer.start(self.tickspeed)

        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self.game.animations)
        self.anim_timer.start(8)

        self.update_value(1)

    def start(self):
        self.game.start()
        self.menu_settings.setDisabled(False)
        if self.game.running:
            self.menu_settings.setDisabled(True)

    def update_value(self, value: int):
        self.game.speed = value
        self.speed_field.setText(str(self.game.speed))

        if value != 0:
            x = value**(0.349)
            t = int(self.tickspeed / x)
            self.timer.setInterval(t)

    def set_value(self, text: str):
        try:
            if not text:
                self.update_value(MIN_SPEED)
                return

            if not text.isdigit():
                raise ValueError("Неправильный символ, разрешены только цифры (0-9)")

            v = int(text)
            if len(text) > 1 and text.startswith('0') and self.game.speed != 0 and v != 0:
                raise ValueError("Ведущие нули не разрешены")

            val = max(min(v, MAX_SPEED), MIN_SPEED)
            self.update_value(val)
            self.speed_slider.setValue(self.game.speed)

        except ValueError as e:
            msg_error(self, f"Ошибка ввода!\n{e}")
            self.update_value(self.game.speed)

    def open_sett(self):
        global current_flags, start_money_values

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open JSON File",
            ".",
            "JSON Files (*.json);;All Files (*)"
        )

        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                    current_flags = data["flags"]
                    start_money_values = data["money"]
            except json.JSONDecodeError:
                QMessageBox.critical(self, "Error", "Формат json файла некорректный")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Не удалось прочитать файл:\n{e}")

    def load_sett(self):
        data = {}
        data["flags"] = current_flags
        data["money"] = start_money_values

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save JSON File",
            ".",
            "JSON Files (*.json);;All Files (*)"
        )

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as file:
                    json.dump(data, file, indent=4, ensure_ascii=False)
            except Exception as e:
                    QMessageBox.critical(self, "Error", f"Не удалось сохранить файл:\n{e}")

    def open_flags(self):
        window = FlagsWindow()
        window.exec()
        self.game.reload()

    def open_ic(self):
        window = ICWindow()
        window.exec()


def msg_error(parent, text: str):
    msg = QMessageBox(parent)
    msg.setStandardButtons(QMessageBox.StandardButton.NoButton)
    msg.setIcon(QMessageBox.Icon.Critical)
    msg.setWindowTitle("Ошибка")
    msg.setText(text)
    msg.show()

    QTimer.singleShot(500, msg.accept)

flags_ops = {
    "Россия": "russia.svg",
    "Китай": "china.svg",
    "Бангладеш": "bangladesh.svg",
    "Бразилия": "brazil.svg",
    "Египет": "egypt.svg",
    "Эфиопия": "ethiopia.svg",
    "Индия": "india.svg",
    "Индонезия": "indonesia.svg",
    "США": "usa.svg",
    "Мексика": "mexico.svg",
    "ДР Конго": "dr_congo.svg",
    "Нигерия": "nigeria.svg",
    "Пакистан": "pakistan.svg",
    "Филиппины": "philippines.svg",
    "Вьетнам": "vietnam.svg"
}
flag_keys = list(flags_ops.keys())

# First 10 indices are current choose
current_flags = list(range(15))
start_money_values = list(range(10))


class FlagsWindow(QDialog):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Выбор флагов")
        self.setFixedSize(500, 440)

        self.buf = list(current_flags)
        layout = QVBoxLayout()

        self.combo: list[QComboBox] = [QComboBox()]*10
        for idx in range(10):
            combo_container = QWidget()
            combo_container.setFixedHeight(50)
            combo_layout = QHBoxLayout(combo_container)

            self.combo[idx] = QComboBox()
            self.combo[idx].addItems(flag_keys)
            self.combo[idx].currentTextChanged.connect(lambda text, i=idx: self.set(text, i))
            for j in range(15):
                path = flags_ops[flag_keys[j]]
                path = os.path.join('assets', path)
                self.combo[idx].setItemIcon(j, QIcon(resource(path)))

            label = QLabel(f"Человек №{idx+1}: ", self)
            combo_layout.addWidget(label)
            combo_layout.addWidget(self.combo[idx])
            layout.addWidget(combo_container)

        self.update_combos()

        # Виджеты и настройки
        buttons_container = QWidget()
        buttons_container.setFixedHeight(50)
        buttons_layout = QHBoxLayout(buttons_container)

        self.btn_cancel = QPushButton("Отмена")
        self.btn_cancel.setFixedWidth(80)
        self.btn_cancel.clicked.connect(self.close)

        self.btn_reset = QPushButton("Сброс")
        self.btn_reset.setFixedWidth(80)
        self.btn_reset.clicked.connect(self.reset)

        self.btn_random = QPushButton("Случайно")
        self.btn_random.setFixedWidth(80)
        self.btn_random.clicked.connect(self.shuffle)

        self.btn_close = QPushButton("ОК")
        self.btn_close.setFixedWidth(80)
        self.btn_close.clicked.connect(self.save)

        buttons_layout.addWidget(self.btn_cancel)
        buttons_layout.addWidget(self.btn_reset)
        buttons_layout.addWidget(self.btn_random)
        buttons_layout.addWidget(self.btn_close)

        layout.addWidget(buttons_container, 0, Qt.AlignmentFlag.AlignBottom)

        self.setLayout(layout)

    def set(self, key: str, idx: int):
        i = flag_keys.index(key)
        p = self.buf.index(i)

        if p == idx:
            return

        self.buf[p], self.buf[idx] = self.buf[idx], self.buf[p]
        self.update_combos()

    def reset(self):
        self.buf = list(range(15))
        self.update_combos()

    def shuffle(self):
        random.shuffle(self.buf)
        self.update_combos()

    def update_combos(self):
        for c in range(10):
            self.combo[c].setCurrentIndex(self.buf[c])

    def save(self):
        global current_flags
        current_flags = self.buf
        self.close()


class ICWindow(QDialog):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Начальные условия")
        self.setFixedSize(380, 470)

        self.buf = list(start_money_values)
        layout = QVBoxLayout()

        self.spins: list[QSpinBox] = [QSpinBox()]*10
        for idx in range(10):
            spins_container = QWidget()
            spins_container.setFixedHeight(50)
            spins_layout = QHBoxLayout(spins_container)
            self.spins[idx] = QSpinBox()
            self.spins[idx].setMinimum(0)
            self.spins[idx].setValue(self.buf[idx])
            self.spins[idx].setMaximum(10)

            self.spins[idx].valueChanged.connect(lambda v, i=idx: self.set(v, i))

            label = QLabel(f"Кошелёк №{idx+1}: ", self)
            spins_layout.addWidget(label)
            spins_layout.addWidget(self.spins[idx])
            layout.addWidget(spins_container)

        buttons_container = QWidget()

        buttons_container.setFixedHeight(50)
        buttons_layout = QHBoxLayout(buttons_container)

        self.btn_cancel = QPushButton("Отмена")
        self.btn_cancel.setFixedWidth(80)
        self.btn_cancel.clicked.connect(self.close)

        self.btn_reset = QPushButton("Сброс")
        self.btn_reset.setFixedWidth(80)
        self.btn_reset.clicked.connect(self.reset)

        self.btn_random = QPushButton("Случайно")
        self.btn_random.setFixedWidth(80)
        self.btn_random.clicked.connect(self.shuffle)

        self.btn_close = QPushButton("ОК")
        self.btn_close.setFixedWidth(80)
        self.btn_close.clicked.connect(self.save)

        buttons_layout.addWidget(self.btn_cancel)
        buttons_layout.addWidget(self.btn_reset)
        buttons_layout.addWidget(self.btn_random)
        buttons_layout.addWidget(self.btn_close)

        layout.addWidget(buttons_container, 0, Qt.AlignmentFlag.AlignBottom)
        self.setLayout(layout)

    def set(self, v: int, idx: int):
        if v != 10:
            self.buf[idx] = v
            return

        self.spins[idx].setValue(self.buf[idx])
        msg_error(self, "Начальное количество монет не может быть равно 10!")

    def reset(self):
        self.buf = list(range(10))
        for i in range(10):
            self.spins[i].setValue(self.buf[i])

    def shuffle(self):
        for i in range(10):
            v = random.randint(0, 9)
            self.buf[i] = v
            self.spins[i].setValue(v)

    def save(self):
        global start_money_values

        start_money_values = list(self.buf)
        self.close()


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
