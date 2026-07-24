from src.view.ui import TrackerView
from src.controller.control import TrackerController

def main():
    """
    Application Entry Point.
    Wires up the MVC architecture and launches the GUI loop.
    """
    # 1. Instantiate the Controller
    app_controller = TrackerController()
    
    # 2. Instantiate the View and pass it the Controller
    app_view = TrackerView(controller=app_controller)
    
    # 3. Give the Controller a reference back to the View
    app_controller.set_view(app_view)
    
    # 4. Start the Application
    app_view.mainloop()

if __name__ == "__main__":
    main()