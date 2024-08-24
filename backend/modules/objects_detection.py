#!/usr/bin/env python3
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import argparse
import re
import time
import os

import numpy as np
import cv2
from PIL import Image
from tflite_runtime.interpreter import Interpreter
import threading

from .utils import load_labels

CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480

default_model = '/opt/vilib/detect.tflite'
default_labels = '/opt/vilib/coco_labels.txt'

#######################################################
object_detection_list_parameter = []

def add_class_names(objects):
  labels = load_labels(default_labels)
  for object in objects:
    object["class_name"] = labels[object['class_id']]

def copy_list_into_list(source,destination):
  destination.clear()
  for i in source:
    destination.append(i)
#######################################################

def set_input_tensor(interpreter, image):
  """Sets the input tensor."""
  tensor_index = interpreter.get_input_details()[0]['index']
  input_tensor = interpreter.tensor(tensor_index)()[0]
  input_tensor[:, :] = image


def get_output_tensor(interpreter, index):
  """Returns the output tensor at the given index."""
  output_details = interpreter.get_output_details()[index]
  tensor = np.squeeze(interpreter.get_tensor(output_details['index']))
  return tensor


def __detect_objects(interpreter, image, threshold):
  """Returns a list of detection results, each a dictionary of object info."""
  set_input_tensor(interpreter, image)
  interpreter.invoke()

  # Get all output details
  boxes = get_output_tensor(interpreter, 0)
  classes = get_output_tensor(interpreter, 1)
  scores = get_output_tensor(interpreter, 2)
  count = int(get_output_tensor(interpreter, 3))

  results = []
  for i in range(count):
    if scores[i] >= threshold:
      result = {
          'bounding_box': boxes[i],
          'class_id': classes[i],
          'score': scores[i]
      }
      results.append(result)
      #global object_detection_list_parameter
  # Allow programmer to access the results
  copy_list_into_list(results,object_detection_list_parameter)
  add_class_names(object_detection_list_parameter)
  return results


colors = [(0,255,255),(255,0,0),(0,255,64),(255,255,0),
        (255,128,64),(128,128,255),(255,128,255),(255,128,128)]

def put_text(img,results,labels_map,width=CAMERA_WIDTH,height=CAMERA_HEIGHT):
    for i,obj in enumerate(results):
        # Convert the bounding box figures from relative coordinates
        # to absolute coordinates based on the original resolution
        ymin, xmin, ymax, xmax = obj['bounding_box']
        xmin = int(xmin * width)
        xmax = int(xmax * width)
        ymin = int(ymin * height)
        ymax = int(ymax * height)

        cv2.rectangle(img,(xmin, ymin), (xmax, ymax),colors[i%7],2)
        cv2.putText(img,
                    f"{labels_map[obj['class_id']]} {obj['score']:.2f}",
                    (xmin+6, ymin+18),
                    cv2.FONT_HERSHEY_PLAIN, #FONT_HERSHEY_DUPLEX
                    1.2,
                    colors[i%7],
                    1,
                    cv2.LINE_AA # line_type: LINE_8 (default), LINE_4, LINE_AA
                    ) 
    #     print('%s %.2f' % (labels_map[obj['class_id']], obj['score']))
    # print('\n')

    return img

# For static images:
def detect_objects(image, model=None, labels=None, width=CAMERA_WIDTH, height=CAMERA_HEIGHT, threshold=0.4):
  # loading model and corresponding label
  if model is None:
    model = default_model
  if labels is None:
    labels = default_labels

  if not os.path.exists(model):
    print('incorrect model path ')
    return image
  if not os.path.exists(labels):
    print('incorrect labels path ')
    return image
  labels = load_labels(labels)
  interpreter = Interpreter(model)
  interpreter.allocate_tensors()
  _, input_height, input_width, _ = interpreter.get_input_details()[0]['shape']  

  if len(image) != 0:
    # resize
    img = cv2.resize(image, (input_width, input_height))
    # classify
    results = __detect_objects(interpreter, img, threshold)
    # putText
    image = put_text(image, results, labels, width, height)
    
  return  image


# For webcam:
results = []
image = []
elapsed_ms = 0
run_flag = False

def imgshow_fuc(input_height, input_width,labels):

    global results
    global elapsed_ms
    global image
    global run_flag

    run_flag = True

    counter, fps = 0, 0
    start_time = time.time()
    fps_avg_frame_count = 10

    # open camera
    cap = cv2.VideoCapture(0)
    cap.set(3,CAMERA_WIDTH)
    cap.set(4,CAMERA_HEIGHT)
    print('start...')

    while cap.isOpened():
      ret,frame = cap.read()
      # frame = cv2.flip(frame, -1) # Flip camera vertically
      image = cv2.resize(frame,(input_width,input_height))

      counter += 1
      if counter % fps_avg_frame_count == 0:
          end_time = time.time()
          fps = fps_avg_frame_count / (end_time - start_time)
          start_time = time.time()

      img = put_text(frame,results,labels)
      cv2.putText(img, '%.1fms' % (elapsed_ms), (CAMERA_WIDTH-120, 40),cv2.FONT_HERSHEY_PLAIN,1, (255, 255, 225), 1)       
      cv2.putText(img, 'fps %s'%round(fps,1), (CAMERA_WIDTH-120, 20),cv2.FONT_HERSHEY_PLAIN,1,(255, 255, 225),1) 
      cv2.imshow('Detecting...', img)
      
      if cv2.waitKey(1) & 0xFF == ord('q'):
        break
      if cv2.waitKey(1) & 0xff == 27: # press 'ESC' to quit
        break
      if cv2.getWindowProperty('Detecting...',1) < 0:
        break

    run_flag = False
    cap.release()
    cv2.destroyAllWindows()


def main():
  # setting parameters of model and corresponding label
  parser = argparse.ArgumentParser(
      formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  parser.add_argument(
      '--model', 
      help='File path of .tflite file.',
      required=False,
      default=default_model)
  parser.add_argument(
      '--labels', 
      help='File path of labels file.',
      required=False,
      default=default_labels)
  parser.add_argument(
      '--threshold',
      help='Score threshold for detected objects.',
      required=False,
      type=float,
      default=0.4)
  args = parser.parse_args()

  # loading model and corresponding label
  labels = load_labels(args.labels)
  interpreter = Interpreter(args.model)
  interpreter.allocate_tensors()
  _, input_height, input_width, _ = interpreter.get_input_details()[0]['shape']

  imgshow_t = threading.Thread(target=imgshow_fuc,args=(input_height, input_width,labels))
  imgshow_t.start()

  global results
  global elapsed_ms
  global run_flag

  while True:

    if len(image) != 0:
      start_time = time.monotonic()
      results = __detect_objects(interpreter, image,args.threshold)
      elapsed_ms = (time.monotonic() - start_time) * 1000
      # print(results)

    if run_flag == False:
      print('\nend...')
      break


if __name__ == '__main__':
  main()


