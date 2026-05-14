import sys

from PySide6.QtWidgets import QApplication

from src.app import PolarBearPetApp


def main():
    app = QApplication(sys.argv)
    window = PolarBearPetApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
