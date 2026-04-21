
values_yaml_file = f"values.yaml"
python_code_file = f"spawner.py"
output_file = f"config.yaml"

# Read the Python code from the file
with open(python_code_file, "r") as py_file:
    python_code_lines = py_file.readlines()

# Ensure each line of the Python code is properly indented for YAML
indented_python_code = "".join(["        " + line for line in python_code_lines])

# Read the values.yaml file
with open(values_yaml_file, "r") as yaml_file:
    values_yaml_content = yaml_file.read()

# Replace the placeholder in the values.yaml with the properly indented Python code
updated_yaml_content = values_yaml_content.replace(f"# spawner.py code here", indented_python_code)

# Write the updated content to a new YAML file
with open(output_file, "w") as output_yaml_file:
    output_yaml_file.write(updated_yaml_content)

print(f"Updated {values_yaml_file} with Python code {python_code_file}, written to {output_file}")