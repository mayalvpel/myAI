import ctypes
import time

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

GetSystemTimes = kernel32.GetSystemTimes
GetSystemTimes.argtypes = [
    ctypes.POINTER(ctypes.c_ulonglong),
    ctypes.POINTER(ctypes.c_ulonglong),
    ctypes.POINTER(ctypes.c_ulonglong),
]
GetSystemTimes.restype = ctypes.c_bool


def get_times():
    idle = ctypes.c_ulonglong()
    kernel = ctypes.c_ulonglong()
    user = ctypes.c_ulonglong()

    if not GetSystemTimes(
        ctypes.byref(idle),
        ctypes.byref(kernel),
        ctypes.byref(user),
    ):
        raise ctypes.WinError()

    return (
        idle.value,
        kernel.value,
        user.value,
    )


idle1, kernel1, user1 = get_times()

time.sleep(0.15)

idle2, kernel2, user2 = get_times()

idle_delta = idle2 - idle1
kernel_delta = kernel2 - kernel1
user_delta = user2 - user1

total = kernel_delta + user_delta

if total <= 0:
    cpu = 0.0
else:
    busy = total - idle_delta
    cpu = (busy / total) * 100.0

cpu = max(0.0, min(100.0, cpu))

print(f"{cpu:.1f}%")
