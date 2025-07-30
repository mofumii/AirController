# AirController/main.py
# Author: Mofumii
# Version 1.0
# If something does not work DM me or create an Issue


from AirStatus import main as pods
import signal
import sys
import logging
from enum import IntEnum
import subprocess
import time

CHECK_TIME = 2  # AirPods status check frequency
TIMEOUT = 5

class AudioStatus(IntEnum):
    DISCONNECTED = 0
    MONO = 1
    STEREO = 2


def handle_exit(signum, frame):
    logging.info("Shutting down AirController")
    success = delete_sink()

    if not success:
        logging.error("Could not delete sink on exit")
        sys.exit(2)  # Sink is not deleted

    if signum == signal.SIGINT:
        sys.exit(130)  # Ctrl+C
    elif signum == signal.SIGTERM:
        sys.exit(143)  # systemd kill
    else:
        sys.exit(0)

signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)

def delete_sink(sink_name: str="AirPods", timeout: int=TIMEOUT) -> bool:
    r"""Deletes AirPods sink if exists.

    :param sink_name: Name of sink to be searched.
    :param timeout: Timeout for sink delete attempt.
    :return: Success status
    :rtype: bool
    """

    logging.info(f"Deleting sink")

    try:
        connected_devices = subprocess.run(
            ['pactl', 'list', 'short', 'modules'],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False
            )
        
        if connected_devices.returncode != 0:
            logging.error(f"pactl list command failed: {connected_devices.stderr.strip()}")
            return False

        found_sink = False
        for line in connected_devices.stdout.splitlines():
            if sink_name in line:
                module_id = line.split()[0]
                if not module_id.isdigit():
                    logging.warning(f"Invalid module ID format in line {line}")
                    continue
                
                logging.debug(f"Unloading module ID {module_id} for sink '{sink_name}'")
                unload_result = subprocess.run(
                    ['pactl', 'unload-module', module_id],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    check=False
                )

                if unload_result.returncode == 0:
                    logging.info(f"Successfully unloaded module ID {module_id}")
                    found_sink = True
                else:
                    logging.error(f"Failed to unload module ID {module_id}: "
                                  f"{unload_result.stderr.strip()}")
                    return False
                
        if not found_sink:
            logging.debug(f"No sink found with name containing '{sink_name}'")
        return True
                    
    except subprocess.TimeoutExpired:
        logging.error(f"Subprocess timed out after {timeout}"
                       "seconds while deleting sink")
        return False
    except subprocess.SubprocessError as e:
        logging.error(f"Subproccess error occurred while deleting sink: {e}")
        return False
    except UnicodeDecodeError as e:
        logging.error(f"Unicode Decoding error occurred while deleting sink: {e}")
        return False
    except Exception as e:
        logging.error(f"Unexpected error occurred while deliting sink: {e}")
        return False
    
def stereo_audio(model_name, timeout: int=TIMEOUT) -> bool:
    r"""Creates new stereo audio sink.

    :param model_name: Name of the AirPods model.
    :param timeout: Timeout for sink remap attempt.
    :return: Success status
    :rtype: bool
    """

    logging.info(f"Switching to stereo audio for {model_name}")

    return create_sink(
        command=[
            'pactl', 'load-module', 'module-remap-sink',
            f'sink_name={model_name}', 'master=@DEFAULT_SINK@',
            'channels=2', 'channel_map=front-left,front-right',
            f'sink_properties=device.description="{model_name}"'
        ],
        channel="stereo",
        timeout=TIMEOUT
        )
    
def mono_audio(model_name, timeout: int=TIMEOUT) -> bool:
    r"""Creates new mono audio sink.

    :param model_name: Name of the AirPods model.
    :param timeout: Timeout for sink remap attempt.
    :return: Success status
    :rtype: bool
    """

    logging.info(f"Switching to mono audio for {model_name}")
    
    success = create_sink(
        command=[f'pactl', 'load-module', 'module-remap-sink',
        f'sink_name={model_name}', 'master=@DEFAULT_SINK@',
        'channels=1', 'channel_map=mono',
        f'sink_properties=device.description="{model_name}"',
        'latency_msec=2'],
        channel="mono",
        timeout=TIMEOUT
        )
    
    if not success:
        return False
    
    set_sink = (['pactl', 'set-default-sink', f'{model_name}'])
    try:
        subprocess.run(set_sink, capture_output=True, text=True, timeout=timeout)
        return True
    except subprocess.TimeoutExpired:
        logging.error(f"Subprocess timed out after {timeout}"
                       "seconds while creating mono sink")
        return False
    except subprocess.SubprocessError as e:
        logging.error(f"Subproccess error occurred while creating mono sink: {e}")
        return False
    except UnicodeDecodeError as e:
        logging.error(f"Unicode Decoding error occurred while creating mono sink: {e}")
        return False
    except Exception as e:
        logging.error(f"Unexpected error occurred while creating mono sink: {e}")
        return False

def create_sink(command, channel: str, timeout: int=TIMEOUT) -> bool:
    r"""Creates new audio sink.

    :param command: Command to be executed to create sink.
    :param channel: Mono/Stereo channel.
    :param timeout: Timeout for sink remap attempt.
    :return: Success status
    :rtype: bool
    """

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False
        )
        
        if result.returncode == 0:
            logging.info(f"{channel} sink successfully created")
            return True
        
    except subprocess.TimeoutExpired:
        logging.error(f"Subprocess timed out after {timeout}"
                       f"seconds while creating {channel} sink")
        return False
    except subprocess.SubprocessError as e:
        logging.error(f"Subproccess error occurred while creating {channel} sink: {e}")
        return False
    except UnicodeDecodeError as e:
        logging.error(f"Unicode Decoding error occurred while creating {channel} sink: {e}")
        return False
    except Exception as e:
        logging.error(f"Unexpected error occurred while creating {channel} sink: {e}")
        return False

def update_audio_status(status: int) -> int:
    r"""Retreives AirPods connection status and updates audio sink if changes noticed.

    :param status: Previous connection status. Disconnected(-0) by default.
    :return: Updated status
    :rtype: int
    """
    try:
        data = pods.get_data()
    except Exception as e:
        logging.error(f"Failed to retreive AirPods status: {e}")
        return status

    connection_status = data.get('status', False)

    if not connection_status:
        if status != AudioStatus.DISCONNECTED:
            delete_sink()
        return AudioStatus.DISCONNECTED

    model = data.get('model')
    left_status = data.get(('charge'), {}).get('left', -1)
    right_status = data.get(('charge'), {}).get('right', -1)
    charging_left = data.get('charging_left', False)
    charging_right = data.get('charging_right', False)

    if left_status == -1 or right_status == -1 or charging_left or charging_right:
        # Switching to mono
        if status != AudioStatus.MONO:
            delete_sink()
            if mono_audio(model):
                return AudioStatus.MONO
    else:
        # Switching to stereo
        if status != AudioStatus.STEREO:
            delete_sink()
            if stereo_audio(model):
                return AudioStatus.STEREO
        
    # If nothing changed or error occurred
    return status

def check_pactl_available():
    """
    Checks if pactl is installed.
    """
    if subprocess.call(['which', 'pactl'], stdout=subprocess.DEVNULL) != 0:
        logging.critical("pactl is not installed or not in PATH")
        sys.exit(1)

def main() -> None:
    status = AudioStatus.DISCONNECTED
    while True:
        status = update_audio_status(status)
        time.sleep(CHECK_TIME)

if __name__ == "__main__":
    check_pactl_available()
    main()

