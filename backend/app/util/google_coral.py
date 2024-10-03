import usb.core
import usb.util
from app.util.logger import Logger

logger = Logger(__name__)


def is_usb_device_connected(vendor_id: int, product_id: int) -> bool:
    """
    Checks if a USB device with a specific vendor ID and product ID is connected.

    This function leverages the `pyusb` library to scan for USB devices and check whether there
    is a device matching the provided vendor ID and product ID.

    Args:
        vendor_id (int): The vendor ID of the USB device.
        product_id (int): The product ID of the USB device.

    Returns:
        bool: True if a device matching the vendor ID and product ID is found; False otherwise.
    """
    try:
        device = usb.core.find(idVendor=vendor_id, idProduct=product_id)
        return device is not None

    except Exception as e:
        logger.log_exception(
            f"Error searching USB device with Vendor ID {vendor_id} and Product ID {product_id}: ",
            e,
        )
        return False


def is_google_coral_connected():
    """
    Verifies whether a Google Coral USB device is connected.

    This function checks for the presence of a Google Coral device by searching for the
    vendor string "Global Unichip Corp" using the `is_usb_device_connected` function.

    Returns:
        bool: True if a Google Coral USB device is detected; False otherwise.
    """
    GOOGLE_CORAL_VENDOR_ID = 0x1A6E
    GOOGLE_CORAL_PRODUCT_ID = 0x089A
    return is_usb_device_connected(GOOGLE_CORAL_VENDOR_ID, GOOGLE_CORAL_PRODUCT_ID)
