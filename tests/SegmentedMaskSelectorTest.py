import unittest
import os
from maskgen import plugins, image_wrap
import numpy
import tempfile


def widthandheight(img):
    a = numpy.where(img != 0)
    bbox = numpy.min(a[0]), numpy.max(a[0]), numpy.min(a[1]), numpy.max(a[1])
    h,w = bbox[1] - bbox[0], bbox[3] - bbox[2]
    return bbox[2],bbox[0],w,h

class SegmentedMaskSelectorTestCase(unittest.TestCase):

    def setUp(self):
        plugins.loadPlugins()

    filesToKill = []
    def test_something(self):
        img_wrapper = image_wrap.openImageFile('tests/images/Burning-rubber-free-license-CC0-483x322.jpg')
        img = img_wrapper.to_array()
        img_wrapper = image_wrap.ImageWrapper(img)
        target_wrapper = image_wrap.ImageWrapper(img)
        filename  = 'tests/images/Burning-rubber-free-license-CC0-483x322.jpg'
        filename_output = tempfile.mktemp(prefix='mstcr', suffix='.jpg', dir='.')
        self.filesToKill.extend([filename_output])
        target_wrapper.save(filename_output)

        args,error = plugins.callPlugin('SegmentedMaskSelector',
                            img_wrapper,
                           filename,
                           filename_output)
        wrapper = image_wrap.openImageFile(filename_output)
        output = wrapper.to_array()
        self.assertTrue(sum(sum(output[:,:,3])) > 255)
        x,y,w,h = widthandheight (output[:,:,3])
        self.assertTrue(sum(sum(output[0:,0:x-1, :, 3])) == 0)
        self.assertTrue(sum(sum(output[0:y-1, 0:, 3])) == 0)
        self.assertTrue(sum(sum(output[y+h+1:,x+w+1:, 3])) == 0)
        self.assertEqual(output.shape, img.shape)
        self.assertTrue('paste_x' in args and args['paste_x'] > 0)
        self.assertTrue('paste_y' in args and args['paste_y'] > 0)



    def  tearDown(self):
        for f in self.filesToKill:
            if os.path.exists(f):
                os.remove(f)

if __name__ == '__main__':
    unittest.main()
