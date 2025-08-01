# PDF Text Replacer (RepliPDF)

[English](README.md) | [简体中文](README.zh-CN.md)

---

A user-friendly Windows desktop application for batch text replacement in PDF files, built with Python, Tkinter, and PyMuPDF. This tool makes it easy to find and replace text across multiple PDF documents while preserving the original fonts and layout.
 
![App Screenshot](img.png)

## ✨ Key Features

- **Intuitive GUI**: A simple graphical interface for all operations, no command line needed.
- **Dynamic Rule Editor**: Add, edit, or paste replacement rules (`old_text|new_text`) directly within the application.
- **Multiple Replacement Strategies**:
  - **`precise`**: (Default) Accurately finds and replaces text, preserving original fonts, sizes, and colors.
  - **`overlay`**: Covers the original text with a white rectangle before writing the new text, ensuring maximum compatibility.
  - **`hybrid`**: Automatically selects the best strategy for each replacement.
- **Custom Font Support**: Simply place your `.ttf` or `.otf` font files into the `fonts` folder to use them in replacements.
- **Live Logging**: See the replacement process, counts, and any potential issues in real-time.
- **Result Verification**: Optionally verify that all instances of the old text have been removed after the process is complete.
- **Standalone `.exe`**: Packaged with PyInstaller to run on Windows without a Python environment.

## 🚀 How to Use (For End-Users)

1.  Download and run `PDF Replacer.exe` from the [Releases](https://github.com/ShawnJim/PDFTextReplacer/releases) page.
2.  **Select Input PDF**: Click "Browse..." to choose the PDF file you want to modify.
3.  **Specify Output PDF**: An output path with an `_replaced` suffix is automatically generated. You can also click "Select..." to customize the destination.
4.  **Enter Replacement Rules**: In the "Replacement Rules" text box, enter your rules using the `old_text|new_text` format, one rule per line. For example:
    ```
    Old Company Name|New Company Name
    Manager A|Manager B
    ```
5.  **Choose Method**: Select a replacement method from the dropdown menu (`precise` is recommended).
6.  **Start Processing**: Click the "Start Processing" button. You can monitor the progress in the log view below.
7.  **Done**: A confirmation message will appear upon completion. Your modified PDF will be at the specified output location.

## 🛠️ How to Build (For Developers)

If you want to run from source or rebuild the application, follow these steps.

### 1. Prerequisites

- Python 3.8+ installed.
- Git installed.

### 2. Clone & Setup Environment

```bash
# Clone the repository
git clone https://github.com/your-username/your-repo.git
cd your-repo

# Create and activate a virtual environment (recommended)
python -m venv .venv
# On Windows
.venv\Scripts\activate
# On macOS/Linux
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
pip install pyinstaller
```

### 4. Run from Source

```bash
python gui.py
```

### 5. Package into an .exe File

Make sure the `fonts` folder (with any custom fonts) is in the project root. Then, run the following command:

```bash
pyinstaller --noconsole --onefile --name "PDF Replacer" --add-data "fonts;fonts" gui.py
```
- `--noconsole`: Prevents the command-line window from appearing when the .exe is run.
- `--onefile`: Bundles everything into a single executable file.
- `--add-data "fonts;fonts"`: Ensures the `fonts` folder is included in the package.

The final `PDF Replacer.exe` will be located in the `dist` folder.

## 命令行用法 (高级)

For automation or batch processing, you can use the core script directly from the command line. This requires a separate text file for rules.

**Usage:**
```bash
python pdf_replacer_pymupdf.py <input_pdf> <output_pdf> <rules_file> [--method <method>] [--verify]
```

**Example:**
```bash
# Use the default 'precise' method and verify the result
python pdf_replacer_pymupdf.py document.pdf document_updated.pdf rules.txt --verify
```

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.