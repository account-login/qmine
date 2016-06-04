from PyQt4.QtCore import *
from PyQt4.QtGui import *
import sys
from mine import MineClientState, MineField, MineServer, Matrix


class MineButton(QPushButton):
    right_clicked = pyqtSignal()
    middle_clicked = pyqtSignal()
    
    def __init__(self, index, box_size=18, parent=None):
        super().__init__(parent)
        self.index = index
        self.state = None
        self.setFixedSize(box_size, box_size)
    
    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if event.button() == Qt.RightButton:
            self.right_clicked.emit()
        elif event.button() == Qt.MiddleButton:
            if self.rect().contains(event.pos()):
                self.middle_clicked.emit()
    
    def update_state(self, state):
        self.state = state
        color_map = {
            1: 'blue',
            2: 'green',
            3: 'red',
            4: 'darkblue',
            5: 'brown',
            6: 'cyan',
            7: 'black',
            8: 'grey',
        }
        if state in color_map:
            self.setStyleSheet('''
                QPushButton {
                    color: %s;
                    font: bold;
                    font-family: "mono";
                    border: 1px solid grey;
                }
            ''' % (color_map[state]))
            self.setFlat(True)
            self.set_size(self.height())    # ???
            self.setText(str(state))
        elif state == 0:
            self.setStyleSheet('''
                QPushButton {
                    border: 1px solid grey;
                }
            ''')
            self.setFlat(True)
            self.setText('')
        elif state == MineClientState.FLAGED:
            self.setText('F')
        elif state == MineClientState.MARKED:
            self.setText('?')
        else:
            self.setText('')

    def set_size(self, size):
        self.setFixedSize(size, size)
#         if self.state is not None:
        font = self.font()
        font.setPixelSize(size)
        self.setFont(font)
        

class MineWidget(QFrame):
    started = pyqtSignal()
    failed = pyqtSignal(MineField)
    win = pyqtSignal()
    flaged = pyqtSignal(tuple, bool)
    
    def __init__(self, server=None, state=None, parent=None):
        super().__init__(parent)
        self.server = server
        self.buttons = None
        self.state = None
        self.box_size = 18
        if server is not None:
            self.reset(server, state)
        self._started = False
    
    def reset(self, server, state=None):
        self._started = False
        self.server = server
        if state is None:
            self.state = MineClientState(self.server.x, self.server.y)
        else:
            self.state = state
        self.init_buttons(self.state)
            
    def init_buttons(self, state):
        x, y = self.server.x, self.server.y
        if self.buttons is not None:
            for btn in self.buttons:
                btn.deleteLater()
        self.buttons = Matrix(x, y)
        
        # deleting layout of a widget
        if self.layout() is not None:
            QWidget().setLayout(self.layout())
        vlayout = QVBoxLayout()
        vlayout.setSpacing(0)
        vlayout.setMargin(0)
        
        for j in range(y):
            hlayout = QHBoxLayout()
#             hlayout.setSpacing(0)
#             hlayout.setMargin(0)
            for i in range(x):
                # need a new scope to capture btn. A lambda referring btn will not work.
                def create_left_click_slot(btn):
                    return lambda: self.click(*btn.index)
                def create_right_click_slot(btn):
                    def f():
                        # cycle through 3 states
                        goto_state = {
                            None                  : MineClientState.FLAGED,
                            MineClientState.FLAGED: MineClientState.MARKED,
                            MineClientState.MARKED: None,
                        }
                        prev_state = btn.state
                        if btn.state in goto_state:
                            new_state = goto_state[btn.state]
                            btn.update_state(new_state)
                            self.state[btn.index] = new_state
                        
                            if prev_state == MineClientState.FLAGED:
                                self.flaged.emit(btn.index, False)
                            elif new_state == MineClientState.FLAGED:
                                self.flaged.emit(btn.index, True)
                    return f
                def create_middle_click_slot(btn):
                    def f():
                        if btn.state in {1, 2, 3, 4, 5, 6, 7, 8}:
                            neighbors = [
                                idx for idx in self.state.neighbors(*btn.index)
                                    if self.state[idx] not in {0, 1, 2, 3, 4, 5, 6, 7, 8}
                            ]
                            neighbor_states = [ self.state[idx] for idx in neighbors ]
                            if neighbor_states.count(MineClientState.FLAGED) == btn.state:
                                for idx in neighbors:
                                    if self.state[idx] != MineClientState.FLAGED:
                                        self.click(*idx)
                    return f
                
                btn = self.buttons[i, j] = MineButton((i, j), self.box_size)
                if state[i, j] is not None:
                    btn.update_state(state[i, j])
                    
                btn.clicked.connect(create_left_click_slot(btn))
                btn.right_clicked.connect(create_right_click_slot(btn))
                btn.middle_clicked.connect(create_middle_click_slot(btn))
                hlayout.addWidget(btn)
                
            vlayout.addLayout(hlayout)
            
        self.setLayout(vlayout)
    
    def click(self, x, y):
        if not self._started:
            self._started = True
            self.started.emit()
            
        result = self.server.click(x, y)
        # emit win signal as quick as possible
        if result['status'] == self.server.WIN:
            self.win.emit()
        self.state.update(result)
        if result['status'] in {self.server.GOOD, self.server.WIN}:
            for k, v in result['update'].items():
                x, y = k
                self.buttons[x, y].update_state(v)
        else:
            self.failed.emit(result['mine_field'])
    
    def resize_buttons(self, size):
        self.box_size = size
        if self.buttons is not None:
            for btn in self.buttons:
                btn.set_size(size)


class NoGrowing(QGridLayout):
    '''
    protect a widget from growing.
    '''
    def __init__(self, widget, parent=None):
        super().__init__(parent)
        self.centered_widget = widget
        
        self.addWidget(widget, 1, 1)
        self.addWidget(QWidget(), 2, 2)
        
        self.setColumnStretch(0, 10086)
        self.setColumnStretch(1, 0)
        self.setColumnStretch(2, 10086)
        self.setRowStretch(0, 10086)
        self.setRowStretch(1, 0)
        self.setRowStretch(2, 10086)


class TzLCD(QLCDNumber):
    def display(self, value):
        value = str(value)
        # increase digits to avoid overflow.
        self.setDigitCount(len(value))
        super().display(value)
    
    def increase(self):
        self.display(int(self.value()) + 1)


class PausableTimer(QObject):
    timeout = pyqtSignal()
    
    STOPED = 'stoped'
    RUNNING = 'running'
    PAUSED = 'paused'
    
    def __init__(self, msec, parent=None):
        super().__init__(parent)
        
        self.interval = msec
        self.count = 0
        self.left = None
        self.state = self.STOPED
        
        def increase_counter():
            self.count += 1
        self.timeout.connect(increase_counter)
        
        self.main_timer = QTimer(parent)
        self.main_timer.timeout.connect(self.timeout)
        
        self.resume_timer = QTimer(parent)
        self.resume_timer.setSingleShot(True)
        self.resume_timer.timeout.connect(self._before_resume_to_main_timer)
        
        self.elapsed_timer = QTime()
    
    def start(self):
        self.state = self.RUNNING
        self.elapsed_timer.start()
        self.main_timer.start(self.interval)
    
    def _before_resume_to_main_timer(self):
        self.timeout.emit()
        self.elapsed_timer.restart()
        self.main_timer.start(self.interval)
    
    def pause(self):
        self.state = self.PAUSED
        if self.resume_timer.isActive():
            self.resume_timer.stop()
            self.left -= self.elapsed_timer.restart()
            assert(self.left >= 0)
        elif self.main_timer.isActive():
            self.main_timer.stop()
            self.left = self.interval - (self.elapsed_timer.restart() % self.interval)
        else:
            pass
    
    def resume(self):
        self.state = self.RUNNING
        self.resume_timer.start(self.left)
        self.elapsed_timer.restart()
    
    def stop(self):
        self.pause()
        self.state = self.STOPED
        self.elapsed_timer = QTime()
        count = self.count
        self.count = 0
        left = self.left
        self.left = None
        return self.interval - left + self.interval * count
    

class Form(QFrame):
    window_state_changed = pyqtSignal(Qt.WindowStates)
    
    def __init__(self, parent=None):
        super().__init__(parent)

        hlayout = QHBoxLayout()
        
        left_layout = QVBoxLayout()
        
        head_layout = QHBoxLayout()
        
        self.mine_left_num = None
        self.mine_left_lcd = TzLCD(1)
        head_layout.addWidget(self.mine_left_lcd)
        
        self.restart_button = QPushButton('Restart')
        self.restart_button.clicked.connect(lambda: self.restart(*self.get_game_param()))
        head_layout.addWidget(self.restart_button)
        
        self.timer_lcd = TzLCD(1)
        head_layout.addWidget(self.timer_lcd)
        
        self.timer = PausableTimer(1000)
        self.timer.timeout.connect(self.timer_lcd.increase)
        
        left_layout.addLayout(head_layout)
        
        self.mine_widget = MineWidget()
        self.mine_widget.win.connect(self.win)
        self.mine_widget.failed.connect(self.failed)
        self.mine_widget.started.connect(self.started)
        
        def flag_slot(pos, flaged):
            if flaged:
                self.mine_left_num -= 1
            else:
                self.mine_left_num += 1
            self.mine_left_lcd.display(self.mine_left_num)
        self.mine_widget.flaged.connect(flag_slot)
        left_layout.addLayout(NoGrowing(self.mine_widget))
        
        hlayout.addLayout(left_layout)
        
        param_layout = QFormLayout()
        
        self.x_spin = QSpinBox()
        self.x_spin.setMinimum(1)
        self.x_spin.setValue(9)
        self.x_spin.valueChanged.connect(self.game_param_changed)
        param_layout.addRow('Width', self.x_spin)
        
        self.y_spin = QSpinBox()
        self.y_spin.setMinimum(1)
        self.y_spin.setValue(9)
        self.y_spin.valueChanged.connect(self.game_param_changed)
        param_layout.addRow('Height', self.y_spin)
        
        self.num_spin = QSpinBox()
        self.num_spin.setMinimum(1)
        self.num_spin.setValue(10)
        self.num_spin.valueChanged.connect(self.game_param_changed)
        param_layout.addRow('Mines', self.num_spin)

        self.resize_box = QSpinBox()
        self.resize_box.setMinimum(1)
        self.resize_box.setValue(18)
        self.resize_box.valueChanged.connect(self.mine_widget.resize_buttons)
        param_layout.addRow('Box size', self.resize_box)
        
        hlayout.addLayout(param_layout)
        self.setLayout(hlayout)
        
        self.window_state_changed.connect(self.pause_resume_timer)
        self.game_param_changed()
    
    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.WindowStateChange:
            self.window_state_changed.emit(self.windowState())
    
    def pause_resume_timer(self, window_state):
        if window_state & Qt.WindowMinimized:
            if self.timer.state == PausableTimer.RUNNING:
                self.timer.pause()
        else:
            if self.timer.state == PausableTimer.PAUSED:
                self.timer.resume()
    
    def get_game_param(self):
        x = self.x_spin.value()
        y = self.y_spin.value()
        num = self.num_spin.value()
        return x, y, num
    
    def game_param_changed(self):
        x, y, num = self.get_game_param()
        if num >= x * y - 1:
            num = x * y - 1
            self.num_spin.setValue(num)
        self.num_spin.setMaximum(x * y - 1)
        
        self.restart(x, y, num)
    
    def restart(self, x, y, num):
        if self.timer.state == PausableTimer.RUNNING:
            self.timer.stop()
        self.timer_lcd.display(0)
        server = MineServer(x, y, num)
        self.mine_widget.reset(server)
        for wid in {self.x_spin, self.y_spin, self.num_spin}:
            wid.setEnabled(True)
        self.mine_left_num = num
        self.mine_left_lcd.display(self.mine_left_num)
    
    def started(self):
        for wid in {self.x_spin, self.y_spin, self.num_spin}:
            wid.setEnabled(False)
        self.timer.start()
    
    def failed(self, mine_field):
        msec_elapsed = self.timer.stop()
        ...
        QMessageBox.critical(self, 'Haha', 'You failed.')
        for wid in {self.x_spin, self.y_spin, self.num_spin}:
            wid.setEnabled(True)
    
    def win(self):
        msec_elapsed = self.timer.stop()
        ...
        QMessageBox.information(self, "Yay", 'You win.\n{:.03f} s'.format(msec_elapsed / 1000))
        for wid in {self.x_spin, self.y_spin, self.num_spin}:
            wid.setEnabled(True)
    

if __name__ == '__main__':
    app = QApplication(sys.argv)
    # perfect font
    font = QFont()
    fontdb = QFontDatabase()
    simsun = 'SimSun-ExtB'
    if simsun in fontdb.families() and font.defaultFamily() != simsun:
        font.setFamily(simsun)
        font.setPointSize(9)
        app.setFont(font)
    app.setStyleSheet("* {font-family: arial,sans-serif;}")
    
    form = Form()
    form.show()
    
    sys.exit(app.exec_())
