
from lumiscreen import LumiScreen
import threading
import concurrent.futures


if __name__ == "__main__":

	screen = LumiScreen()

	with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:


		for index in range(3):
			print(f"Before message {index}")
			# Returns right away but takes a long time to run
			executor.submit(screen.displayMessage, f"Message {index}")
			print(f"After message {index}")

