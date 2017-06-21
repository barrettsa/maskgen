import shutil
import os
import numpy
from maskgen import tool_set
from maskgen.image_wrap import ImageWrapper

"""
Convenience plugin to perform select region given a mask.
"""

def transform(img,source,target, **kwargs):
    mask = numpy.asarray(tool_set.openImageFile(kwargs['inputmaskname']).to_mask())
    img_array = img.to_array()
    result = None
    if len(img_array.shape) == 2:
        # grey
        result = numpy.zeros((img_array.shape[0],img_array.shape[1],2)).astype('uint8')
        result[:,:,0] = img_array
        result[:,:,1] = mask
    elif len(img_array.shape) == 3:
        if img_array.shape[2] == 4:
            result = img_array
            result[:,:,4] = mask
        else:
            result = numpy.zeros((img_array.shape[0],img_array.shape[1],4)).astype('uint8')
            result[:,:,0] = img_array[:,:,0]
            result[:, :, 1] = img_array[:, :, 1]
            result[:, :, 2] = img_array[:, :, 2]
            result[:,:,3] = mask
    ImageWrapper(result).save(target)
    return None,None
    
def operation():
    return {'name':'SelectRegion',
            'category':'Select',
            'arguments':{
                'inputmaskname': {
                    "type": "file:image",
                    "description": "An image file containing a mask describing the areas affected."
                }
           },
           'description':'Create a limited selection in a donor image.  The result should be preserved in PNG.  Best practice involves using an alpha channel to mask out unselected regions.  The image can then be spliced into a series if frames.',
           'transitions': [
                'image.image'
            ]
         }

def suffix():
    return None
