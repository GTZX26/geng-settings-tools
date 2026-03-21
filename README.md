# Geng Settings Tools v2.1.0: Multi-Language Support

![Geng Settings Tools Icon](assets/icon.png)

## 🌟 Overview

Geng Settings Tools is a comprehensive utility designed for Linux Mint Cinnamon users, offering a streamlined approach to managing system settings, enhancing productivity, and customizing the desktop experience. With the release of **v2.1.0**, this tool now proudly supports over 30 languages, making it accessible to a global audience. From keyboard configurations to system updates and media downloads, Geng Settings Tools provides an intuitive graphical interface to simplify complex tasks.

## ✨ Key Features

*   **🌐 Multi-Language Support (New in v2.1.0):** Seamlessly switch between over 30 languages, including Thai, English, Lao, Japanese, Korean, Chinese, French, German, Spanish, Arabic, and many more. The entire user interface, including menus and labels, dynamically updates to reflect the chosen language.
*   **⌨️ Keyboard Settings Management:** Easily configure keyboard layouts, shortcuts, and other input preferences.
*   **🔄 System Updates:** Keep your system up-to-date with integrated update functionalities.
*   **⬇️ Media Downloader:** Download videos and audio from various online sources directly through the application.
*   **⚙️ General System Utilities:** Access a suite of tools for common system maintenance and customization tasks.
*   **🖥️ Intuitive GUI:** A user-friendly graphical interface built with PyQt6 ensures ease of use for both novice and experienced users.

## 🚀 Installation

### Prerequisites

Before installing Geng Settings Tools, ensure you have the following dependencies:

*   **Python 3:** The application is built with Python 3.
*   **PyQt6:** The graphical user interface framework.
*   **pkexec:** For securely executing commands with administrative privileges.
*   **yt-dlp:** For media downloading functionalities.

### Installation Steps (for Debian/Ubuntu-based systems like Linux Mint)

1.  **Download the `.deb` package:**
    Download the latest `GST.deb` package from the [GitHub Releases page](https://github.com/GTZX26/geng-settings-tools/releases/tag/v2.1.0).

2.  **Open Terminal:**
    Press `Ctrl + Alt + T` to open a new terminal window.

3.  **Navigate to the download directory:**
    ```bash
    cd ~/Downloads
    ```
    (Replace `~/Downloads` with the actual path if you saved it elsewhere.)

4.  **Install the package:**
    ```bash
    sudo dpkg -i GST.deb
    ```
    You may be prompted for your user password. Enter it and press `Enter`.

5.  **Resolve dependencies (if any):**
    If `dpkg` reports any missing dependencies, run the following command:
    ```bash
    sudo apt install -f
    ```

## 💡 Usage

After installation, you can launch Geng Settings Tools from your applications menu. Look for "Geng Settings Tools" or search for it.

### Changing Language

1.  Locate the language dropdown menu (usually indicated by a globe icon 🌐) within the application\'s interface.
2.  Click on the dropdown and select your preferred language (e.g., `🇱🇦 ລາວ`, `🇯🇵 日本語`, `🇰🇷 한국어`).
3.  The application\'s interface will instantly update to the selected language.

## ⚠️ Troubleshooting

*   **Application not launching or PyQt6 errors:** Ensure `python3-pyqt6` is correctly installed. You might need to run `sudo apt install python3-pyqt6`.
*   **Media download features not working:** Verify that `yt-dlp` is installed (`sudo apt install yt-dlp`).
*   **Frequent password prompts:** This is normal for functions requiring administrative privileges. `pkexec` is used to handle these securely.
*   **Incorrect translations:** While extensive efforts have been made for accurate translations, some phrases might appear awkward due to automated translation. Please report any issues, and contributions for better translations are always welcome!

## 🤝 Contributing

We welcome contributions to Geng Settings Tools! If you have suggestions, bug reports, or would like to contribute code or translations, please visit our [GitHub Repository](https://github.com/GTZX26/geng-settings-tools).

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## 📞 Contact

For support or inquiries, please contact Thammasorn Musikapun at gtzx26@gmail.com.

---

**Developed by:**   
** 𝙂𝙀𝙉𝙂 𝕀𝕟𝕗𝕚𝕟𝕚𝕥𝕪 (คุณเก่ง)**  
** DeepSeek AI**  
** Manus AI (น้องเกต)**  
** Version:** 2.1.0  
** Date:** March 21, 2026  
  

