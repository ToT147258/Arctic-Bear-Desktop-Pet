import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.app import PolarBearPetApp


def main():
    app = QApplication(sys.argv)
    window = PolarBearPetApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
