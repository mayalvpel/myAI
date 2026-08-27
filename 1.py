import os

# Create a file named '1.py' on the C drive
file_path = r'C:\1.py'
with open(file_path, 'w') as f:
    f.write('hello')

# Print the result
print(f'File created at: {file_path}')