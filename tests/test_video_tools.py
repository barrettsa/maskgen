from maskgen import video_tools,tool_set
import unittest
import numpy as np
import cv2
import os


class TestVideoTools(unittest.TestCase):


    def _init_write_file(self, name, start_time, start_position, amount, fps):
        writer = tool_set.GrayBlockWriter(name, fps)
        mask_set = list()
        amount = int(amount)
        increment = 1000 / float(fps)
        count = start_position
        for i in range(amount):
            mask = np.random.randint(255, size=(1090, 1920)).astype('uint8')
            mask_set.append(mask)
            writer.write(mask, start_time, count)
            start_time += increment
            count += 1
        writer.close()
        return writer.filename

    """
    def test_meta(self):
        meta,frames = video_tools.getMeta('tests/videos/sample1.mov',show_streams=True)
        self.assertEqual('yuv420p',meta[0]['pix_fmt'])

    def test_frame_binding(self):
        result = video_tools.getMaskSetForEntireVideo('tests/videos/sample1.mov')
        self.assertEqual(0.0, result[0]['starttime'])
        self.assertEqual(1, result[0]['startframe'])
        self.assertEqual(803,result[0]['frames'])
        self.assertEqual(803.0, result[0]['endframe'])
        self.assertEqual(59350.0, result[0]['endtime'])
        self.assertEqual('video', result[0]['type'])
        result = video_tools.getMaskSetForEntireVideo('tests/videos/sample1.mov',start_time='00:00:02.01')
        self.assertEqual(1982.0, round(result[0]['starttime']))
        self.assertEqual(24, result[0]['startframe'])
        self.assertEqual(803-24+1, result[0]['frames'])
        result = video_tools.getMaskSetForEntireVideo('tests/videos/sample1.mov', start_time='00:00:02.01:02')
        self.assertEqual(2195.0, round(result[0]['starttime']))
        self.assertEqual(26, result[0]['startframe'])
        self.assertEqual(803 - 26 + 1, result[0]['frames'])
        result = video_tools.getMaskSetForEntireVideo('tests/videos/sample1.mov', start_time='00:00:02.01',end_time='00:00:04')
        self.assertEqual(1982.0, round(result[0]['starttime']))
        self.assertEqual(24, result[0]['startframe'])
        self.assertEqual(3965.0, round(result[0]['endtime']))
        self.assertEqual(48, result[0]['endframe'])
        self.assertEqual(48 - 24 + 1, result[0]['frames'])
        result = video_tools.getMaskSetForEntireVideo('tests/videos/sample1.mov',
                                                      media_types=['audio'])
        self.assertEqual(0.0, result[0]['starttime'])
        self.assertEqual(1, result[0]['startframe'])
        self.assertEqual(2563, result[0]['frames'])
        self.assertEqual(2563.0, result[0]['endframe'])
        self.assertEqual(59348.0, round(result[0]['endtime']))
        self.assertEqual('audio', result[0]['type'])
        result = video_tools.getMaskSetForEntireVideo('tests/videos/sample1.mov', start_time='00:00:02.01',
                                                      end_time='00:00:04',
                                                      media_types=['audio'])
        self.assertEqual(2009.0, round(result[0]['starttime']))
        self.assertEqual(89, result[0]['startframe'])
        self.assertEqual(3983.0, round(result[0]['endtime']))
        self.assertEqual(174, result[0]['endframe'])
        self.assertEqual(174 - 89 + 1, result[0]['frames'])

    def test_before_dropping(self):

        amount = 30
        fileOne = self._init_write_file('test_ts_bd1',2500,75,30,30)
        fileTwo = self._init_write_file('test_ts_bd2', 4100,123,27,30)
        sets= []
        change = dict()
        change['starttime'] = 0
        change['startframe'] = 1
        change['endtime'] = 1000
        change['endframe'] = 31
        change['frames'] = 30
        change['rate'] = 30
        change['videosegment'] = ''
        change['type'] = 'video'
        sets.append(change)
        change = dict()
        change['starttime'] = 2500
        change['startframe'] = 75
        change['endtime'] = 3500
        change['endframe'] = change['startframe'] + amount
        change['frames'] = amount
        change['rate'] = 30
        change['videosegment'] = fileOne
        change['type'] = 'video'
        sets.append(change)
        change = dict()
        change['starttime'] = 4100
        change['startframe'] = 123
        change['endtime'] = 5000
        change['endframe'] = change['startframe'] + 27
        change['frames'] = int(27)
        change['rate'] = 30
        change['videosegment'] = fileTwo
        change['type'] = 'video'
        sets.append(change)

        result  = video_tools.dropFramesFromMask([{
            'startframe':90,
            'starttime':3000,
            'endframe':117,
            'endtime': 4000
        }],sets)
        self.assertEqual(3, len(result))
        self.assertEqual(15,result[1]['frames'])
        self.assertEqual(75, result[1]['startframe'])
        self.assertEqual(90, result[1]['endframe'])
        self.assertEqual(96, result[2]['startframe'])
        self.assertEqual(123, result[2]['endframe'])

        result = video_tools.dropFramesFromMask([{
            'startframe': 63,
            'starttime': 2100,
            'endframe': 90,
            'endtime': 3000
        }],sets)
        self.assertEqual(3, len(result))
        self.assertEqual(15, result[1]['frames'])
        self.assertEqual(63, result[1]['startframe'])
        self.assertEqual(78, result[1]['endframe'])
        self.assertEqual(96, result[2]['startframe'])
        self.assertEqual(123, result[2]['endframe'])

        result = video_tools.dropFramesFromMask([{
            'startframe': 87,
            'starttime': 2900,
            'endframe': 93,
            'endtime': 3100
        }],sets)

        self.assertEqual(4, len(result))
        self.assertEqual(12,result[1]['frames'])
        self.assertEqual(75, result[1]['startframe'])
        self.assertEqual(87, result[1]['endframe'])
        self.assertEqual(12, result[2]['frames'])
        self.assertEqual(87, result[2]['startframe'])
        self.assertEqual(99, result[2]['endframe'])
        self.assertEqual(117, result[3]['startframe'])
        self.assertEqual(144, result[3]['endframe'])


        result = video_tools.dropFramesFromMask([{
            'startframe': 87,
            'starttime': 2900,
            'endframe': 93,
            'endtime': 3100
        }], sets,keepTime=True)
        self.assertEqual(4, len(result))
        self.assertEqual(12, result[1]['frames'])
        self.assertEqual(12, result[2]['frames'])
        self.assertEqual(75, result[1]['startframe'])
        self.assertEqual(87, result[1]['endframe'])
        self.assertEqual(93, result[2]['startframe'])
        self.assertEqual(105, result[2]['endframe'])
        self.assertEqual(123, result[3]['startframe'])
        self.assertEqual(150, result[3]['endframe'])
        self.assertEqual(4, len(result))

        result = video_tools.dropFramesFromMask([{
            'startframe': 1,
            'starttime': 0,
            'endframe': 93,
            'endtime': 3100
        }], sets)
        self.assertEqual(2, len(result))
        self.assertEqual(12, result[0]['frames'])
        self.assertEqual(1, result[0]['startframe'])
        self.assertEqual(13, result[0]['endframe'])
        self.assertEqual(31, result[1]['startframe'])
        self.assertEqual(58, result[1]['endframe'])

        result = video_tools.dropFramesFromMask([{
            'startframe': 93,
            'starttime': 3100
        }], sets)
        self.assertEqual(2, len(result))
        self.assertEqual(30, result[0]['frames'])
        self.assertEqual(1, result[0]['startframe'])
        self.assertEqual(31, result[0]['endframe'])
        self.assertEqual(75, result[1]['startframe'])
        self.assertEqual(93, result[1]['endframe'])

        result = video_tools.dropFramesFromMask([{
            'startframe': 1,
            'starttime': 0,
            'endframe': 93,
            'endtime': 3100
        }], sets,keepTime=True)
        self.assertEqual(2, len(result))
        self.assertEqual(12, result[0]['frames'])
        self.assertEqual(93, result[0]['startframe'])
        self.assertEqual(105, result[0]['endframe'])
        self.assertEqual(123, result[1]['startframe'])
        self.assertEqual(150, result[1]['endframe'])

        result = video_tools.dropFramesFromMask([{
            'startframe': 93,
            'starttime': 3100,
        }], sets,keepTime=True)
        self.assertEqual(2, len(result))
        self.assertEqual(30, result[0]['frames'])
        self.assertEqual(1, result[0]['startframe'])
        self.assertEqual(31, result[0]['endframe'])
        self.assertEqual(18, result[1]['frames'])
        self.assertEqual(75, result[1]['startframe'])
        self.assertEqual(93, result[1]['endframe'])



    def test_before_dropping_nomask(self):
        amount = 30
        sets = []
        change = dict()
        change['starttime'] = 0
        change['startframe'] = 1
        change['endtime'] = 1000
        change['endframe'] = 31
        change['frames'] = 30
        change['rate'] = 30
        change['videosegment'] = ''
        change['type'] = 'video'
        sets.append(change)
        change = dict()
        change['starttime'] = 2500
        change['startframe'] = 75
        change['endtime'] = 3500
        change['endframe'] = change['startframe'] + amount
        change['frames'] = amount
        change['rate'] = 30
        change['videosegment'] = ''
        change['type'] = 'video'
        sets.append(change)
        change = dict()
        change['starttime'] = 4100
        change['startframe'] = 123
        change['endtime'] = 5000
        change['endframe'] = change['startframe'] + 27
        change['frames'] = int(27)
        change['rate'] = 30
        change['videosegment'] = ''
        change['type'] = 'video'
        sets.append(change)
        result  = video_tools.dropFramesWithoutMask([{
            'startframe': 87,
            'starttime': 2900,
            'endframe': 93,
            'endtime': 3100
        }],sets)
        self.assertEqual(4, len(result))
        self.assertEqual(12,result[1]['frames'])
        self.assertEqual(75, result[1]['startframe'])
        self.assertEqual(87, result[1]['endframe'])
        self.assertEqual(12, result[2]['frames'])
        self.assertEqual(87, result[2]['startframe'])
        self.assertEqual(99, result[2]['endframe'])
        self.assertEqual(117, result[3]['startframe'])
        self.assertEqual(144, result[3]['endframe'])

        result = video_tools.dropFramesWithoutMask([{
            'startframe': 63,
            'starttime': 2100,
            'endframe': 90,
            'endtime': 3000
        }],  sets)
        self.assertEqual(3, len(result))
        self.assertEqual(15, result[1]['frames'])
        self.assertEqual(63, result[1]['startframe'])
        self.assertEqual(78, result[1]['endframe'])
        self.assertEqual(96, result[2]['startframe'])
        self.assertEqual(123, result[2]['endframe'])

        result = video_tools.dropFramesWithoutMask([{
            'startframe': 87,
            'starttime': 2900,
            'endframe': 93,
            'endtime': 3100
        }],  sets, keepTime=True)
        self.assertEqual(4, len(result))
        self.assertEqual(12,  result[1]['frames'])
        self.assertEqual(12,  result[2]['frames'])
        self.assertEqual(75,  result[1]['startframe'])
        self.assertEqual(87,  result[1]['endframe'])
        self.assertEqual(93,  result[2]['startframe'])
        self.assertEqual(105, result[2]['endframe'])
        self.assertEqual(123, result[3]['startframe'])
        self.assertEqual(150, result[3]['endframe'])

        result = video_tools.dropFramesWithoutMask([{
            'startframe': 1,
            'starttime': 0,
            'endframe': 93,
            'endtime': 3100
        }],  sets)
        self.assertEqual(2, len(result))
        self.assertEqual(12, result[0]['frames'])
        self.assertEqual(1,  result[0]['startframe'])
        self.assertEqual(13, result[0]['endframe'])
        self.assertEqual(31, result[1]['startframe'])
        self.assertEqual(58, result[1]['endframe'])

        result = video_tools.dropFramesWithoutMask([{
            'startframe': 93,
            'starttime': 3100
        }] , sets)
        self.assertEqual(2, len(result))
        self.assertEqual(30, result[0]['frames'])
        self.assertEqual(1, result[0]['startframe'])
        self.assertEqual(31, result[0]['endframe'])
        self.assertEqual(18, result[1]['frames'])
        self.assertEqual(75, result[1]['startframe'])
        self.assertEqual(93, result[1]['endframe'])

        result = video_tools.dropFramesWithoutMask([{
            'startframe': 1,
            'starttime': 0,
            'endframe': 93,
            'endtime': 3100
        }],  sets,keepTime=True)
        self.assertEqual(2, len(result))
        self.assertEqual(12, result[0]['frames'])
        self.assertEqual(93, result[0]['startframe'])
        self.assertEqual(105, result[0]['endframe'])
        self.assertEqual(123, result[1]['startframe'])
        self.assertEqual(150, result[1]['endframe'])

        result = video_tools.dropFramesWithoutMask([{
            'startframe': 93,
            'starttime': 3100
        }], sets,keepTime=True)
        self.assertEqual(2, len(result))
        self.assertEqual(30, result[0]['frames'])
        self.assertEqual(1, result[0]['startframe'])
        self.assertEqual(31, result[0]['endframe'])
        self.assertEqual(18, result[1]['frames'])
        self.assertEqual(75, result[1]['startframe'])
        self.assertEqual(93, result[1]['endframe'])

    def after_general_all(self, sets, func):
        result = func(
            [{
                'startframe': 180,
                'starttime': 6000,
                'endframe': 210,
                'endtime': 7000
            }], sets)
        self.assertEqual(2, len(result))
        self.assertEqual(30, result[1]['frames'])

        result = func([{
            'startframe': 63,
            'starttime': 2100,
            'endframe': 90,
            'endtime': 3000
        }], sets)
        self.assertEqual(2, len(result))
        self.assertEqual(30, result[1]['frames'])
        self.assertEqual(102, result[1]['startframe'])

        result = func([{
            'startframe': 81,
            'starttime': 2700,
            'endframe': 111,
            'endtime': 3700
        }], sets)
        self.assertEqual(3, len(result))
        self.assertEqual(6, result[1]['frames'])
        self.assertEqual(75, result[1]['startframe'])
        self.assertEqual(24, result[2]['frames'])
        self.assertEqual(111, result[2]['startframe'])
        self.assertEqual(135, result[2]['endframe'])

        result = func([{
            'startframe': 1,
            'starttime': 0,
            'endframe': 63,
            'endtime': 2100
        }], sets)
        self.assertEqual(2, len(result))
        self.assertEqual(30, result[0]['frames'])
        self.assertEqual(30, result[1]['frames'])
        self.assertEqual(63, result[0]['startframe'])
        self.assertEqual(93, result[0]['endframe'])
        self.assertEqual(137, result[1]['startframe'])
        self.assertEqual(167, result[1]['endframe'])


    def test_after_dropping(self):
        amount = 30
        fileOne = self._init_write_file('test_ts_bd1', 0, 1, 30, 30)
        fileTwo = self._init_write_file('test_ts_bd2', 2500, 75, 30, 30)
        sets = []
        change = dict()
        change['starttime'] = 0
        change['startframe'] = 1
        change['endtime'] = 1000
        change['endframe'] = amount + 1
        change['frames'] = amount
        change['rate'] = 30
        change['type'] = 'video'
        change['videosegment'] = fileOne
        sets.append(change)
        change = dict()
        change['starttime'] = 2500
        change['startframe'] = 75
        change['endtime'] = 3500
        change['endframe'] = change['startframe'] + amount
        change['frames'] = amount
        change['rate'] = 30
        change['type'] = 'video'
        change['videosegment'] = fileTwo
        sets.append(change)
        self.after_general_all(sets,video_tools.insertFramesToMask)
        self.after_general_all(sets, video_tools.insertFramesWithoutMask)
"""
    def test_resize(self):
        fileOne = self._init_write_file('test_td_rs', 0,1, 30, 30)
        change = dict()
        change['starttime'] = 0
        change['startframe'] = 0
        change['endtime'] = 1000
        change['endframe'] = 30
        change['frames'] = 30
        change['rate'] = 29
        change['type'] = 'video'
        change['videosegment'] = fileOne
        result = video_tools.resizeMask([change], (1000, 1720))
        self.assertEqual(1, len(result))
        self.assertEqual(30, result[0]['frames'])
        self.assertEqual(0, result[0]['startframe'])


    def test_rotate(self):
        fileOne = self._init_write_file('test_td_rs', 0, 1,30, 30)
        change = dict()
        change['starttime'] = 0
        change['startframe'] = 0
        change['endtime'] = 1000
        change['endframe'] = 30
        change['frames'] = 30
        change['rate'] = 29
        change['type'] = 'video'
        change['videosegment'] = fileOne
        result = video_tools.rotateMask(-90,[change],expectedDims=(1920,1090))
        self.assertEqual(1, len(result))
        self.assertEqual(30, result[0]['frames'])
        self.assertEqual(0, result[0]['startframe'])


    def test_crop(self):
        fileOne = self._init_write_file('test_td_rs', 0,1, 30, 30)
        change = dict()
        change['starttime'] = 0
        change['startframe'] = 0
        change['endtime'] = 1000
        change['endframe'] = 30
        change['frames'] = 30
        change['rate'] = 29
        change['type'] = 'video'
        change['videosegment'] = fileOne
        result = video_tools.cropMask([change],(100,100,900,1120))
        self.assertEqual(1, len(result))
        self.assertEqual(30, result[0]['frames'])
        self.assertEqual(0, result[0]['startframe'])
        result = video_tools.insertMask( [change], (100, 100, 900, 1120),(1090,1920))
        self.assertEqual(1, len(result))
        self.assertEqual(30, result[0]['frames'])
        self.assertEqual(0, result[0]['startframe'])

if __name__ == '__main__':
    unittest.main()
