import requests


LABELS_URL = "https://raw.githubusercontent.com/anishathalye/imagenet-simple-labels/master/imagenet-simple-labels.json"


response = requests.get(LABELS_URL)
labels = response.json()
