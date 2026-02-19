import os
import pathspec

# Define the directory to clean and the ignore file (like .gitignore)
directory_to_clean = 'site'
ignore_file = f"{os.path.dirname(__file__)}/mkdocsignore"  # Path to your ignore file

if __name__ == '__main__':
    # Read the patterns from the ignore file
    with open(ignore_file, 'r') as f:
        ignore_patterns = f.read().splitlines()

    # Create a PathSpec object using the ignore patterns
    spec = pathspec.PathSpec.from_lines(pathspec.patterns.GitWildMatchPattern, ignore_patterns)

    # Walk through the directory and delete files that match the ignore patterns
    for root, dirs, files in os.walk(directory_to_clean):
        for file in files:
            file_path = os.path.relpath(os.path.join(root, file), directory_to_clean)
            if spec.match_file(file_path):  # Check if the file matches any ignore pattern
                if os.environ.get('DEBUG') == 'true':
                    print(f"Deleting {file_path}")
                os.remove(os.path.join(root, file))