from flask import Blueprint, Response
from time import sleep
from app.util.platform_adapters import Vilib

qrcode_bp = Blueprint("qrcode", __name__)


@qrcode_bp.route("/qrcode")
def qrcode_feed():
    qrcode_html = """
<!DOCTYPE html>
<html>
<head>
    <title>QRcode</title>
    <script>
        function refreshQRCode() {
            var imgElement = document.getElementById('qrcode-img');
            imgElement.src = '/qrcode.png?' + new Date().getTime();  // Add timestamp to avoid caching
        }
        var refreshInterval = 500;  // 2s

        window.onload = function() {
            refreshQRCode();
            setInterval(refreshQRCode, refreshInterval);
        };
    </script>
</head>
<body>
    <img id="qrcode-img" src="/qrcode.png" alt="QR Code" />
</body>
</html>
"""
    return Response(qrcode_html, mimetype="text/html")


def get_qrcode() -> bytes:
    """
    Get the encoded QR code image as a byte array. Waits until the QR code
    image is available.

    Returns:
        bytes: The QR code image in encoded bytes.
    """
    while Vilib.qrcode_img_encode is None:
        sleep(0.2)
    return Vilib.qrcode_img_encode


@qrcode_bp.route("/qrcode.png")
def qrcode_feed_png():
    """Video streaming route. Put this in the src attribute of an img tag."""
    if Vilib.web_qrcode_flag:
        # response = Response(get_qrcode(),
        #                 mimetype='multipart/x-mixed-replace; boundary=frame')
        response = Response(get_qrcode(), mimetype="image/png")
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response
    else:
        tip = """
    Please enable web display first:
        Vilib.display_qrcode(web=True)
"""
        html = f"<html><style>p{{white-space: pre-wrap;}}</style><body><p>{tip}</p></body></html>"
        return Response(html, mimetype="text/html")
