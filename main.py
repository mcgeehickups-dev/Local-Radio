import json
import os

from kivy.app import App
from kivy.core.audio import SoundLoader
from kivy.lang import Builder
from kivy.properties import StringProperty, BooleanProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.textinput import TextInput

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


<HomeScreen>:
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
'''


class StationCard(BoxLayout):
    name = StringProperty('')
    url = StringProperty('')
    playing = BooleanProperty(False)

    def toggle_play(self):
        self.parent_screen.play_station(self)

    def remove_station(self):
        self.parent_screen.remove_station(self)


class HomeScreen(Screen):
    status_text = StringProperty('Listo para conectar')

    def on_pre_enter(self):
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
                {'name': 'Ejemplo local', 'url': 'http://192.168.1.100:8000/stream'}
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
        url_input = TextInput(hint_text='URL del stream (http://...)', multiline=False, size_hint_y=None, height=44)
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


class RadioApp(App):
    def build(self):
        Builder.load_string(KV)
        sm = ScreenManager()
        sm.add_widget(HomeScreen(name='home'))
        return sm


if __name__ == '__main__':
    RadioApp().run()
