import json
import os
import socket
import struct
import threading
import queue

from kivy.app import App
from kivy.core.audio import SoundLoader
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.properties import StringProperty, BooleanProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.textinput import TextInput

# ---------------------------------------------------------------------------
# Servidor de transmisión (modo Emisor)
# ---------------------------------------------------------------------------
SAMPLE_RATE = 44100
CHANNELS = 1
BITS = 16
PORT = 8000


def make_wav_header():
    """Cabecera WAV con tamaño 'infinito' para transmisión en vivo."""
    byte_rate = SAMPLE_RATE * CHANNELS * BITS // 8
    block_align = CHANNELS * BITS // 8
    header = b'RIFF' + struct.pack('<I', 0x7FFFFFFF) + b'WAVE'
    header += b'fmt ' + struct.pack('<IHHIIHH', 16, 1, CHANNELS, SAMPLE_RATE,
                                     byte_rate, block_align, BITS)
    header += b'data' + struct.pack('<I', 0x7FFFFFFF)
    return header


class Broadcaster:
    """Maneja la captura de micrófono y el servidor HTTP que la transmite."""

    def __init__(self):
        self.clients = []
        self.lock = threading.Lock()
        self.recording = False
        self.audio_record = None
        self.httpd = None
        self.server_thread = None
        self.capture_thread = None

    # -- clientes conectados -------------------------------------------------
    def add_client(self, q):
        with self.lock:
            self.clients.append(q)

    def remove_client(self, q):
        with self.lock:
            if q in self.clients:
                self.clients.remove(q)

    def push_audio(self, data):
        with self.lock:
            for q in self.clients:
                try:
                    q.put_nowait(data)
                except Exception:
                    pass

    # -- servidor HTTP ---------------------------------------------------------
    def start_server(self):
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

        broadcaster = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header('Content-Type', 'audio/wav')
                self.send_header('Connection', 'close')
                self.end_headers()
                client_q = queue.Queue()
                broadcaster.add_client(client_q)
                try:
                    self.wfile.write(make_wav_header())
                    while True:
                        chunk = client_q.get()
                        if chunk is None:
                            break
                        self.wfile.write(chunk)
                except Exception:
                    pass
                finally:
                    broadcaster.remove_client(client_q)

            def log_message(self, format, *args):
                pass

        self.httpd = ThreadingHTTPServer(('0.0.0.0', PORT), Handler)
        self.server_thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.server_thread.start()

    def stop_server(self):
        if self.httpd:
            try:
                self.httpd.shutdown()
            except Exception:
                pass
            self.httpd = None

    # -- captura de micrófono (Android) ----------------------------------------
    def start_capture(self):
        try:
            from jnius import autoclass

            AudioRecord = autoclass('android.media.AudioRecord')
            MediaRecorder = autoclass('android.media.MediaRecorder')
            AudioFormat = autoclass('android.media.AudioFormat')

            min_buf = AudioRecord.getMinBufferSize(
                SAMPLE_RATE,
                AudioFormat.CHANNEL_IN_MONO,
                AudioFormat.ENCODING_PCM_16BIT,
            )
            if min_buf <= 0:
                return False, 'No se pudo configurar el micrófono (buffer inválido)'

            self.audio_record = AudioRecord(
                MediaRecorder.AudioSource.MIC,
                SAMPLE_RATE,
                AudioFormat.CHANNEL_IN_MONO,
                AudioFormat.ENCODING_PCM_16BIT,
                min_buf * 4,
            )
            self.audio_record.startRecording()
            self.recording = True

            def capture_loop():
                buf = bytearray(min_buf)
                while self.recording:
                    n = self.audio_record.read(buf, 0, len(buf))
                    if n and n > 0:
                        self.push_audio(bytes(buf[:n]))

            self.capture_thread = threading.Thread(target=capture_loop, daemon=True)
            self.capture_thread.start()
            return True, None
        except Exception as e:
            return False, str(e)

    def stop_capture(self):
        self.recording = False
        if self.audio_record:
            try:
                self.audio_record.stop()
                self.audio_record.release()
            except Exception:
                pass
            self.audio_record = None

    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return '127.0.0.1'


# ---------------------------------------------------------------------------
# Interfaz
# ---------------------------------------------------------------------------
KV = '''
<RoundedButton@Button>:
    background_color: 0,0,0,0
    background_normal: ''
    color: 1,1,1,1
    bold: True
    canvas.before:
        Color:
            rgba: (0.13,0.59,0.95,1) if self.state == 'normal' else (0.10,0.45,0.75,1)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [18]

<TabButton@ToggleButton>:
    background_color: 0,0,0,0
    background_normal: ''
    color: 1,1,1,1
    bold: True
    group: 'tabs'
    canvas.before:
        Color:
            rgba: (0.13,0.59,0.95,1) if self.state == 'down' else (0.18,0.18,0.20,1)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [14]

<StationCard>:
    orientation: 'horizontal'
    size_hint_y: None
    height: 74
    padding: 14, 8
    spacing: 12
    canvas.before:
        Color:
            rgba: (0.16,0.16,0.18,1) if not self.playing else (0.10,0.28,0.45,1)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [14]

    BoxLayout:
        orientation: 'vertical'
        Label:
            text: root.name
            color: 1,1,1,1
            bold: True
            font_size: '17sp'
            halign: 'left'
            valign: 'middle'
            text_size: self.size
        Label:
            text: root.url
            color: 0.6,0.6,0.65,1
            font_size: '12sp'
            halign: 'left'
            valign: 'middle'
            text_size: self.size
            shorten: True

    RoundedButton:
        text: '[]' if root.playing else '>'
        size_hint_x: None
        width: 56
        on_press: root.toggle_play()

    Button:
        text: 'x'
        size_hint_x: None
        width: 40
        background_color: 0,0,0,0
        background_normal: ''
        color: 0.55,0.55,0.6,1
        on_press: root.remove_station()


<RootScreen>:
    BoxLayout:
        orientation: 'vertical'
        canvas.before:
            Color:
                rgba: (0.07,0.07,0.08,1)
            Rectangle:
                pos: self.pos
                size: self.size

        BoxLayout:
            size_hint_y: None
            height: 90
            padding: 20, 20
            Label:
                text: 'Mi Radio Local'
                font_size: '24sp'
                bold: True
                color: 1,1,1,1
                halign: 'left'
                valign: 'middle'
                text_size: self.size

        BoxLayout:
            size_hint_y: None
            height: 50
            padding: 14, 0
            spacing: 10
            TabButton:
                text: 'Escuchar'
                state: 'down'
                on_state: if self.state == 'down': root.ids.sm.current = 'listen'
            TabButton:
                text: 'Emitir'
                on_state: if self.state == 'down': root.ids.sm.current = 'broadcast'

        ScreenManager:
            id: sm
            ListenScreen:
                name: 'listen'
            BroadcastScreen:
                name: 'broadcast'


<ListenScreen>:
    BoxLayout:
        orientation: 'vertical'

        Label:
            id: status_label
            text: root.status_text
            size_hint_y: None
            height: 34
            color: 0.55,0.75,1,1
            font_size: '14sp'

        ScrollView:
            BoxLayout:
                id: station_list
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height
                spacing: 10
                padding: 14, 4

        RoundedButton:
            text: '+  Agregar emisora'
            size_hint_y: None
            height: 56
            font_size: '16sp'
            on_press: root.open_add_popup()


<BroadcastScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: 20
        spacing: 16

        Label:
            text: 'Modo Emisor'
            font_size: '20sp'
            bold: True
            color: 1,1,1,1
            size_hint_y: None
            height: 36

        Label:
            text: root.info_text
            color: 0.75,0.75,0.8,1
            font_size: '14sp'
            size_hint_y: None
            height: 90
            halign: 'center'
            valign: 'middle'
            text_size: self.width, None

        Label:
            text: root.status_text
            color: 0.55,0.9,0.6,1
            font_size: '16sp'
            bold: True
            size_hint_y: None
            height: 40

        Widget:

        RoundedButton:
            text: root.button_text
            size_hint_y: None
            height: 60
            font_size: '17sp'
            on_press: root.toggle_broadcast()
'''


class StationCard(BoxLayout):
    name = StringProperty('')
    url = StringProperty('')
    playing = BooleanProperty(False)

    def toggle_play(self):
        self.parent_screen.play_station(self)

    def remove_station(self):
        self.parent_screen.remove_station(self)


class ListenScreen(Screen):
    status_text = StringProperty('Listo para conectar')

    def on_pre_enter(self):
        if not hasattr(self, 'stations'):
            self.sound = None
            self.current_card = None
            self.stations = []
            self.data_file = os.path.join(App.get_running_app().user_data_dir, 'stations.json')
            self.load_stations()

    def load_stations(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    self.stations = json.load(f)
            except Exception:
                self.stations = []
        else:
            self.stations = [
                {'name': 'Ejemplo local', 'url': 'http://192.168.1.100:8000/'}
            ]
        self.refresh_list()

    def save_stations(self):
        try:
            with open(self.data_file, 'w') as f:
                json.dump(self.stations, f)
        except Exception:
            pass

    def refresh_list(self):
        box = self.ids.station_list
        box.clear_widgets()
        for st in self.stations:
            card = StationCard(name=st['name'], url=st['url'])
            card.parent_screen = self
            box.add_widget(card)

    def open_add_popup(self):
        layout = BoxLayout(orientation='vertical', spacing=10, padding=15)
        name_input = TextInput(hint_text='Nombre de la emisora', multiline=False, size_hint_y=None, height=44)
        url_input = TextInput(hint_text='URL del stream (http://IP:8000/)', multiline=False, size_hint_y=None, height=44)
        layout.add_widget(name_input)
        layout.add_widget(url_input)

        btn_row = BoxLayout(size_hint_y=None, height=48, spacing=10)
        save_btn = Button(text='Guardar')
        cancel_btn = Button(text='Cancelar')
        btn_row.add_widget(cancel_btn)
        btn_row.add_widget(save_btn)
        layout.add_widget(btn_row)

        popup = Popup(title='Nueva emisora', content=layout, size_hint=(0.9, 0.4))

        def do_save(instance):
            name = name_input.text.strip() or 'Sin nombre'
            url = url_input.text.strip()
            if url:
                self.stations.append({'name': name, 'url': url})
                self.save_stations()
                self.refresh_list()
            popup.dismiss()

        save_btn.bind(on_press=do_save)
        cancel_btn.bind(on_press=popup.dismiss)
        popup.open()

    def play_station(self, card):
        if self.current_card is card and self.sound:
            self.stop_current()
            return

        self.stop_current()
        self.sound = SoundLoader.load(card.url)
        if self.sound:
            self.sound.play()
            card.playing = True
            self.current_card = card
            self.status_text = f'Reproduciendo: {card.name}'
        else:
            self.status_text = 'No se pudo conectar al stream'

    def stop_current(self):
        if self.sound:
            self.sound.stop()
            self.sound.unload()
            self.sound = None
        if self.current_card:
            self.current_card.playing = False
            self.current_card = None
        self.status_text = 'Detenido'

    def remove_station(self, card):
        if self.current_card is card:
            self.stop_current()
        self.stations = [s for s in self.stations if not (s['name'] == card.name and s['url'] == card.url)]
        self.save_stations()
        self.refresh_list()


class BroadcastScreen(Screen):
    info_text = StringProperty('Toca "Comenzar a emitir" para transmitir tu\nmicrófono a la red local.')
    status_text = StringProperty('')
    button_text = StringProperty('Comenzar a emitir')

    def on_pre_enter(self):
        if not hasattr(self, 'broadcaster'):
            self.broadcaster = Broadcaster()
            self.emitting = False

    def toggle_broadcast(self):
        if self.emitting:
            self.stop()
        else:
            self.start()

    def start(self):
        ok, error = self.broadcaster.start_capture()
        if not ok:
            self.status_text = ''
            self.info_text = f'No se pudo acceder al micrófono:\n{error}'
            return

        self.broadcaster.start_server()
        ip = self.broadcaster.get_local_ip()
        self.emitting = True
        self.button_text = 'Detener transmisión'
        self.status_text = 'Transmitiendo en vivo'
        self.info_text = (
            f'Comparte esta dirección con quien quiera escucharte,\n'
            f'deben estar en tu misma red WiFi:\n\nhttp://{ip}:{PORT}/'
        )

    def stop(self):
        self.broadcaster.stop_capture()
        self.broadcaster.stop_server()
        self.emitting = False
        self.button_text = 'Comenzar a emitir'
        self.status_text = ''
        self.info_text = 'Toca "Comenzar a emitir" para transmitir tu\nmicrófono a la red local.'


class RootScreen(Screen):
    pass


class RadioApp(App):
    def build(self):
        Builder.load_string(KV)
        sm = ScreenManager()
        sm.add_widget(RootScreen(name='root'))
        return sm


if __name__ == '__main__':
    RadioApp().run()
