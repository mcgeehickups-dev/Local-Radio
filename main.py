from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.core.audio import SoundLoader


class RadioApp(App):
    def build(self):
        self.sound = None

        layout = BoxLayout(orientation='vertical', padding=30, spacing=20)

        self.status_label = Label(
            text='Listo para conectar',
            size_hint=(1, 0.3),
            font_size='18sp'
        )
        layout.add_widget(self.status_label)

        # Cambia esta URL por defecto por la de tu emisora local
        self.url_input = TextInput(
            text='http://192.168.1.100:8000/stream',
            multiline=False,
            size_hint=(1, 0.15),
            font_size='16sp'
        )
        layout.add_widget(self.url_input)

        btn_layout = BoxLayout(size_hint=(1, 0.2), spacing=15)

        play_btn = Button(text='Escuchar', font_size='18sp')
        play_btn.bind(on_press=self.play)
        btn_layout.add_widget(play_btn)

        stop_btn = Button(text='Detener', font_size='18sp')
        stop_btn.bind(on_press=self.stop)
        btn_layout.add_widget(stop_btn)

        layout.add_widget(btn_layout)

        return layout

    def play(self, instance):
        url = self.url_input.text.strip()
        if not url:
            self.status_label.text = 'Escribe una URL válida'
            return

        self.stop(None)
        self.sound = SoundLoader.load(url)
        if self.sound:
            self.sound.play()
            self.status_label.text = f'Reproduciendo...\n{url}'
        else:
            self.status_label.text = 'No se pudo conectar al stream'

    def stop(self, instance):
        if self.sound:
            self.sound.stop()
            self.sound.unload()
            self.sound = None
            self.status_label.text = 'Detenido'


if __name__ == '__main__':
    RadioApp().run()
