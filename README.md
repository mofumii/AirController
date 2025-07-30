# AirController for Linux

**AirController** is a tool that automatically switches your AirPods between mono and stereo modes.

> 🐧 **Note**: AirController is designed to work on **Linux** systems using **PulseAudio/PipeWire** and **pactl**. It is not compatible with Windows or macOS.

## Features

- Detects AirPods status in real-time
- Switches to mono mode when one earbud is missing or charging
- Switches to stereo when both earbuds are in User
- Can be ran as background process

---

## Installation

1. **Clone the repositor**:
```bash
git clone https://github.com/mofumii/AirController
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

## Running as a service

1. **Create a systemd service file (as root):**
```
# /etc/systemd/system/aircontroller.service
[Unit]
Description=AirPods Channel Controller
After=network.target sound.target

[Service]
ExecStart=/usr/bin/python3 /PATH/TO/AirController/main.py
WorkingDirectory=/PATH/TO/AirController
StandardOutput=append:/tmp/aircontroller.out
StandardError=append:/tmp/aircontroller.err
Restart=on-failure
RestartSec=3
User=yourusername
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=default.target
```
Change /PATH/TO/AirContoller to actual path

2. **Reload and start the service:**
```bash
sudo systemctl daemon-reexec
sudo systemctl start aircontroller
```

3. **Enable service on boot:**
```bash
sudo systemctl enable aircontroller
```


## Configuration
- You can customize timeouts and sink names by editing variables inside main.py
- Default polling interval: 2 seconds.

## Troubleshooting
- Make sure pactl and PulseAudio/PipeWire are installed.
- Ensure your user has permission to acces bluetooth devices.
- Check if your AirPods are visible via bluetoothctl or similar tools.

## Contributing

Pull requests are welcome!

If you encounter any issues or bugs, feel free to [open an issue](https://github.com/mofumii/AirController) or contact me directly

Thank you for your input!

## License

This project includes code from the [AirStatus project](https://github.com/delphiki/AirStatus) (GPLv3).  
Therefore, this project is licensed under the GNU General Public License v3.0. 
See the [LICENSE](./LICENSE) file for details.