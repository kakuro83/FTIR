"""Pruebas de interfaz sin navegador: python -m unittest test_drx_ui.py -v."""
import io
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest


class UITests(unittest.TestCase):
    def test_empty(self):
        app = AppTest.from_file("DRX.py").run(timeout=30)
        self.assertEqual(len(app.exception), 0)
        self.assertGreater(len(app.info), 0)

    def test_upload_and_options(self):
        sample = io.BytesIO(b"# sample\n10 1\n20 3\n30 10\n40 3\n50 1\n")
        sample.name = "sample.xy"
        other = io.BytesIO(b"10 2\n20 4\n30 12\n40 4\n50 2\n")
        other.name = "second.xy"
        with patch("streamlit.file_uploader", return_value=[sample, other]):
            app = AppTest.from_file("DRX.py").run(timeout=30)
            self.assertEqual(len(app.exception), 0)
            self.assertEqual(len(app.dataframe[0].value), 2)
            for box in app.checkbox:
                if box.label in ["Normalizar intensidad (0–100)", "Modo apilado", "Etiquetar posiciones 2θ"]:
                    box.set_value(True)
            app.run(timeout=30)
            self.assertEqual(len(app.exception), 0)
            self.assertEqual(len(app.dataframe[0].value), 2)
            for box in app.checkbox:
                if box.label == "Limitar rango de 2θ":
                    box.set_value(True)
            for field in app.number_input:
                if field.label == "Mínimo (°)":
                    field.set_value(90.0)
            app.run(timeout=30)
            self.assertEqual(len(app.exception), 0)
            self.assertGreater(len(app.error), 0)


if __name__ == "__main__":
    unittest.main()
