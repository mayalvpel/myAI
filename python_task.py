import pyautogui
import time

# Open Telegram
pyautogui.hotkey('win', 't')
pyautogui.write('telegram')
pyautogui.press('enter')

# Wait for Telegram to load
time.sleep(5)

# Type the password
pyautogui.write('your_password')
pyautogui.press('enter')

# Wait for login to complete
time.sleep(5)

# Print the useful final result
print("Telegram has been opened and logged in successfully.")