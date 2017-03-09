import cv2
from PIL import Image
import numpy
from random import randint,choice

def build_mask(percentageWidth,percentageHeight, shape,target):
    pixelWidth = int(shape[1] * percentageWidth)
    pixelHeight = int(shape[0] * percentageHeight)
    r_x = randint(1, abs(shape[1] - pixelWidth))
    r_y = randint(1, abs(shape[0] - pixelHeight))

    mask = numpy.zeros((shape[0], shape[1]))
    mask[r_y:r_y + pixelHeight, r_x:r_x + pixelWidth] = 255
    Image.fromarray(mask.astype('uint8')).save(target)

    trial_boxes = [
        [0, 0, r_x-pixelWidth, shape[0] - pixelHeight],
        [0, 0, shape[1] - pixelWidth, r_y - pixelHeight],
        [r_x + pixelWidth, 0, shape[1] - pixelWidth, shape[0] - pixelHeight],
        [0, r_y + pixelHeight, shape[1] - pixelWidth, shape[0] - pixelHeight]
    ]

    boxes = [box for box in trial_boxes \
             if (box[2] - box[0]) > pixelWidth and (box[3] - box[1]) > pixelHeight]

    box = choice(boxes)

    new_position_x = randint(box[0], box[2])
    new_position_y = randint(box[1], box[3])
    return (new_position_x,new_position_y)

def transform(img,source,target,**kwargs):
    percentageWidth = float(kwargs['percentage_width'])
    percentageHeight = float(kwargs['percentage_height'])
    cv_image = numpy.array(img)
    new_position_x,new_position_y= build_mask(percentageWidth,percentageHeight,cv_image.shape,target)
    return {'paste_x': new_position_x, 'paste_y': new_position_y},None

def operation():
  return {
          'category': 'Select',
          'name': 'SelectRegion',
          'description':'Mask Selector: ',
          'software':'OpenCV',
          'version':'2.4.13',
          'arguments':{'pixel_width': {'type': "int[1:10]", 'description':'percentage of width to crop'},'pixel_height': {'type': "int[1:15]", 'description':'percentage of width to crop'}},
          'transitions': [
              'image.image'
          ]
          }

def suffix():
    return '.png'
