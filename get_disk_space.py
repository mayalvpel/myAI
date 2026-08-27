import shutil

total, used, free = shutil.disk_usage("C:\\")

gb = 1024 ** 3

print(
    f"{free / gb:.2f} GB free of {total / gb:.2f} GB"
)
