from kivy.uix.screenmanager import Screen
from kivy.lang import Builder
from kivy.properties import ListProperty, StringProperty
from kivy.uix.label import Label
from kivy.metrics import dp

# Loads the associated kv file
Builder.load_file("graph_view_screen.kv", encoding='utf-8')

class GraphViewScreen(Screen):
    """
    A screen dedicated to displaying a graph of a patient's health metric evolution.
    """
    metric_name = StringProperty('')
    data_points = ListProperty([]) # Expects a list of (x, y) tuples

    def on_enter(self, *args):
        """Called when the screen is entered. It triggers the graph to be drawn."""
        self.populate_report()

    def populate_report(self):
        """Populates the report grid with the data points."""
        report_grid = self.ids.report_grid
        report_grid.clear_widgets()

        if not self.data_points:
            report_grid.add_widget(Label(text="Não há dados para exibir.", color=(0,0,0,1)))
            return

        # Add headers
        report_grid.add_widget(Label(text="[b]Dia[/b]", markup=True, color=(0,0,0,1)))
        
        header_label = Label(text=f"[b]Valor ({self.metric_name})[/b]", markup=True, color=(0,0,0,1))
        header_label.bind(width=lambda s, w: s.setter('text_size')(s, (w, None)))
        report_grid.add_widget(header_label)

        # Add blank rows for spacing
        report_grid.add_widget(Label(text=''))
        report_grid.add_widget(Label(text=''))
        report_grid.add_widget(Label(text=''))

        # Add data rows
        for i, (date_label, value) in enumerate(self.data_points):
            # Day number label
            day_num_label = Label(text=str(i + 1), color=(0,0,0,1))
            report_grid.add_widget(day_num_label)

            # Metric value label
            # Display as float with one decimal place, or as string if it's not a number (like for blood pressure)
            if isinstance(value, (int, float)):
                value_text = f"{value:.1f}"
            else:
                value_text = str(value)
            value_label = Label(text=value_text, color=(0,0,0,1))
            report_grid.add_widget(value_label)