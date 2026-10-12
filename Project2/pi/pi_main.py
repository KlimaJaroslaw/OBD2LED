import queue
from gpiozero import Button


command_queue = queue.Queue()

# Konfiguracja fizycznego przycisku GPIO
btn_next_program = Button(17)
btn_next_program.when_pressed = lambda: command_queue.put({"action": "next_program"})

initial_profile = {"theme": "default", "source": "cam", "program": "matrix", "device": "screen"}
run(initial_profile, command_queue=command_queue)