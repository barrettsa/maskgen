# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
#==============================================================================
import numpy as np
import cv2
import logging
import os
from scipy import spatial
from maskgen.cv2api import cv2api_delegate
from maskgen.image_wrap import ImageWrapper
from maskgen.tool_set import VidTimeManager, differenceInFramesBetweenMillisecondsAndFrame

import hashlib


def readFrames(in_file, start_time, end_time):
    """
     Function to read in video frames and store them in an array for later use.
     This limits the size of the video to just few minutes at most.
     Build a concatenated histogram of the GBR of each frame.
    :param in_file:
    :param offset_seconds: number of seconds to start search
    :return:
    @type offset_seconds: float
    """
    if not os.path.exists(in_file):
        raise ValueError(in_file + ' not found')
    cap = cv2api_delegate.videoCapture(in_file)
    frames = list()
    histograms = list()
    fps = 0.0
    startFrame = 0
    time_manager = VidTimeManager(startTimeandFrame=start_time, stopTimeandFrame=end_time)
    try:
        while (cap.grab()):
            fps = cap.get(cv2api_delegate.prop_fps)
            elapsed_time = float(cap.get(cv2api_delegate.prop_pos_msec))
            time_manager.updateToNow(elapsed_time)
            if not time_manager.isBeforeTime() and not time_manager.isPastTime():
                ret, frame = cap.retrieve()
                frames.append(frame)
                hist = np.asarray(np.histogram(frame[:, :, 0], 256, (0, 255)))[0]
                hist = np.append(hist, np.asarray(np.histogram(frame[:, :, 1], 256, (0, 255)))[0])
                hist = np.append(hist, np.asarray(np.histogram(frame[:, :, 2], 256, (0, 255)))[0])
                histograms.append(hist)
            else:
                startFrame += 1
            if time_manager.isPastTime():
                break
    finally:
        cap.release()
    if len(frames) == 0:
        raise ValueError(in_file + ' unreadable')
    return [frames, histograms, fps, startFrame]


def createOutput(in_file, out_file, timeManager, codec=None):
    """

    :param in_file:
    :param out_file:
    :param timeManager:
    :param codec:
    :return:
    @type in_file: str
    @type out_file: str
    @type timeManager: VidTimeManager
    """
    logger = logging.getLogger('maskgen')
    cap = cv2api_delegate.videoCapture(in_file)
    fourcc = cv2api_delegate.get_fourcc(str(codec)) if codec is not None else cap.get(cv2api_delegate.fourcc_prop)
    fps = cap.get(cv2api_delegate.prop_fps)
    height = int(np.rint(cap.get(cv2api_delegate.prop_frame_height)))
    width = int(np.rint(cap.get(cv2api_delegate.prop_frame_width)))
    out_video = cv2api_delegate.videoWriter(out_file, fourcc, fps, (width, height), isColor=1)
    if not out_video.isOpened():
        err = out_file + " fourcc: " + str(fourcc) + " FPS: " + str(fps) + \
              " H: " + str(height) + " W: " + str(width)
        raise ValueError('Unable to create video ' + err)
    try:
        writecount = 0
        dropcount = 0
        while (cap.grab()):
            ret, frame = cap.retrieve()
            elapsed_time = float(cap.get(cv2api_delegate.prop_pos_msec))
            timeManager.updateToNow(elapsed_time)
            if timeManager.isBeforeTime() or timeManager.isPastTime():
                out_video.write(frame)
                writecount += 1
            else:
                dropcount += 1
        logger.debug('Drop {} frames; Wrote {} frames'.format(dropcount, writecount))
    finally:
        cap.release()
        out_video.release()


def scanHistList(histograms, distance, offset, saveHistFile=None):
    """
        Function to compare frame image histograms and produce an array of the
        standard deviation of the differences.
    :param histograms:  an array of concatenated GBR histograms
    :param distance:  minimum number of frames apart to start the comparison
    :param offset:  Number of frames to skip at the start of the list
    :return: Nx4 matrix where each column in start,end,length and std_flow.
    """
    import math
    if distance >= len(histograms):
        raise ValueError('Video is to short for the distance provided.')
    history = np.zeros(((len(histograms) - (offset + distance)) * (len(histograms) - (offset + distance) + 1) // 2,
                        4), np.int)
    h_count = 0
    # front frame to compare. skip the first 30
    for i in range(offset, len(histograms) - distance):
        for j in range(i + distance, len(histograms)):
            std_flow = np.std(histograms[i] - histograms[j])
            history[h_count, :] = [i, j, j - i, std_flow]
            h_count += 1

    if saveHistFile is not None:
        np.savetxt(saveHistFile, history, delimiter=",", fmt='%2.3f')
    return history


def computeNormalDiffs(histograms, num_frames, logger=None):
    """
    Return the average and standard deviation for the first number of frame
    histogram differences
    :param histograms:
    :param num_frames:
    :return:
    """
    flow_list = np.zeros(num_frames)
    for i in range(1, num_frames):
        flow_list[i] = np.std(histograms[i] - histograms[i + 1])

    avg_flow = np.mean(flow_list)
    sigma_flow = np.std(flow_list)
    if logger is not None:
        logger.debug("mean flow {} with {} sigma".format(avg_flow, sigma_flow))
    return [avg_flow, sigma_flow]


def selectBestMatches(differences, selection=50):
    """
     return the 'selection' best results. Needs to be updated to try to find the longest
     rop that should work
    :param differences: histogram difference matrix
    :param selection: how manny to return
    :return: selectionX4 matrix of the best (least different)
    """
    sort = differences[:, 3].argsort(axis=None)
    return differences[sort[:selection]]


# best flow defined as the lowest sigam of the optical flow between frames
def selectBestFlow(frames, best_matches, logger):
    flow_list = np.zeros(best_matches.shape[0])
    for i in range(best_matches.shape[0]):
        past = cv2.cvtColor(frames[best_matches[i, 0]], cv2.COLOR_BGR2GRAY)
        future = cv2.cvtColor(frames[best_matches[i, 1]], cv2.COLOR_BGR2GRAY)
        flow = cv2api_delegate.calcOpticalFlowFarneback(past, future,
                                                        0.8, 7, 15, 3, 7, 1.5)
        flow_list[i] = np.std(flow)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('FOR {} to {}, STD={}'.format(best_matches[i, 0], best_matches[i, 1], flow_list[i]))
    return np.argmin(flow_list)


def getNormalFlow(frames):
    flow_list = np.zeros(len(frames) - 1)
    future = cv2.cvtColor(frames[0], cv2.COLOR_BGR2GRAY)
    for i in range(1, len(frames)):
        past = future
        future = cv2.cvtColor(frames[i], cv2.COLOR_BGR2GRAY)
        flow = cv2api_delegate.calcOpticalFlowFarneback(past, future,
                                                        0.8, 7, 15, 3, 7, 1.5)
        flow_list[i - 1] = np.std(flow)
    return np.mean(flow_list)


def calculateOptimalFrameReplacement(frames, start, stop):
    avg_flow = getNormalFlow(frames[start:stop])
    prev_frame = cv2.cvtColor(frames[start], cv2.COLOR_BGR2GRAY)
    next_frame = cv2.cvtColor(frames[stop], cv2.COLOR_BGR2GRAY)
    jump_flow = cv2api_delegate.calcOpticalFlowFarneback(prev_frame, next_frame,
                                                         0.8, 7, 15, 3, 7, 1.5, flags=2)
    std_jump_flow = np.std(jump_flow)
    frames_to_add = int(np.rint(std_jump_flow / avg_flow))
    return frames_to_add


def dumpFrames(frames, file):
    with open(file, 'w') as fp:
        i = 1
        for frame in frames:
            fp.write('{},{}\n'.format(i, hashlib.sha256(frame).hexdigest()))
            i += 1


def smartDropFrames(in_file, out_file,
                    start_time,
                    end_time,
                    seconds_to_drop,
                    savehistograms=False,
                    codec=None,
                    drop=True):
    """
    :param in_file: is the full path of the video file from which to drop frames
    :param out_file: resulting video file
    :param start_time: (milli,frame no) for search space
    :param end_time: (milli,frame no) for search space
    :param seconds_to_drop:
    :param savehistograms: save histograms differences to file
    :param codec:
    :return: first and last frame numbers dropped, and the optimal number to add back/replace
    """
    logger = logging.getLogger('maskgen')
    logger.info('Read {} frames into memory'.format(in_file))
    frames, histograms, fps, start = readFrames(in_file, start_time, end_time)
    dumpFrames(frames, in_file[0:in_file.rfind('.')] + '-frames.csv')
    distance = int(round(fps * seconds_to_drop))
    logger.info('Distance {} for {} frames to drop with {} fps'.format(distance, seconds_to_drop, fps))
    offset = int(round(fps * seconds_to_drop))
    # avg_diffs, sigma_diffs = computeNormalDiffs(histograms, 60)
    logger.info('starting histogram computational')
    differences = scanHistList(histograms, distance, offset,
                               saveHistFile=in_file[0:in_file.rfind('.')] + '-hist.csv' if savehistograms else None)
    logger.info('Finding best matches')
    best_matches = selectBestMatches(differences, selection=50)
    logger.info('Starting optical flow search')
    if best_matches is not None:
        best_flow = selectBestFlow(frames, best_matches, logger)
        logger.info('best pair: {}'.format(str(best_matches[best_flow])))
        frames_to_add = calculateOptimalFrameReplacement(frames, best_matches[best_flow][0],
                                                         best_matches[best_flow][1])
        # add 2: one to advance to frame no and one to advance to first dropped frame
        firstFrametoDrop = best_matches[best_flow][0] + start + 2
        lastFrametoDrop = best_matches[best_flow][1] + start
        if drop:
            time_manager = VidTimeManager(startTimeandFrame=(0, firstFrametoDrop),
                                          stopTimeandFrame=(0, lastFrametoDrop))
            createOutput(in_file, out_file, time_manager, codec=codec)
        return firstFrametoDrop, lastFrametoDrop, frames_to_add


def dropFrames(in_file, out_file,
               start_time,
               end_time,
               codec=None):
    """
    :param in_file: is the full path of the video file from which to drop frames
    :param out_file: resulting video file
    :param start_time: (milli,frame no) for search space
    :param end_time: (milli,frame no) for search space
    :param codec:
    :return:
    """
    time_manager = VidTimeManager(startTimeandFrame=start_time, stopTimeandFrame=end_time)
    createOutput(in_file, out_file, time_manager, codec=codec)


class OpticalFlow:
    def __init__(self, prvs_frame, next_frame, flow, bkflow):
        self.prvs_frame = prvs_frame
        self.next_frame = next_frame
        self.flow = flow
        self.bkflow = bkflow
        self.hight = flow.shape[0]
        self.width = flow.shape[1]
        h, w = flow.shape[:2]
        self.coords = (np.swapaxes(np.indices((w, h), np.float32), 0, 2))

    def setFrames(self, prvs_frame, next_frame, flow, bkflow):
        self.prvs_frame = prvs_frame
        self.next_frame = next_frame
        self.flow = flow
        self.bkflow = bkflow

    def warpFlow(self, img, flow):
        adj = self.coords + flow
        underoverflow_width = np.logical_or(adj[:, :, 0] >= self.coords.shape[1],
                                            adj[:, :, 0] < 0)
        underoverflow_height = np.logical_or(adj[:, :, 1] >= self.coords.shape[0],
                                             adj[:, :, 1] < 0)
        adj[underoverflow_width] = self.coords[underoverflow_width]
        adj[underoverflow_height] = self.coords[underoverflow_height]
        return cv2.remap(img, adj, None, cv2.INTER_LINEAR)

    def setTime(self, frame_time):
        forward_flow = np.multiply(self.flow, 1 - frame_time)
        backward_flow = np.multiply(self.bkflow, frame_time)
        from_prev = self.warpFlow(self.prvs_frame, backward_flow)
        from_next = self.warpFlow(self.next_frame, forward_flow)
        from_prev = np.multiply(from_prev, (1 - frame_time))
        from_next = np.multiply(from_next, frame_time)
        frame = (np.add(from_prev, from_next)).astype(np.uint8)

        return frame

        # return the average sigma(optical flow)

class kdtreeOpticalFlow:
    def __init__(self, prvs_frame, next_frame, flow, bkflow):
        self.logger = logging.getLogger('maskgen')
        self.prvs_frame = prvs_frame
        self.next_frame = next_frame
        self.flow = flow
        self.bkflow = bkflow
        self.hight = flow.shape[0]
        self.width = flow.shape[1]
        self.count = 0
        h, w = flow.shape[:2]
        self.coords = (np.swapaxes(np.indices((w, h), np.float32), 0, 2))

    def setFrames(self, prvs_frame, next_frame, flow, bkflow):
        self.prvs_frame = prvs_frame
        self.next_frame = next_frame
        self.flow = flow
        self.bkflow = bkflow

    def warpFlow(self, img, flow):
        #s = time.time()
        res = self.adjustFlow_G(flow)
        #d = time.time() - s
        #self.logger.info('Inverse Took {} seconds'.format(d))
        adj = res[0] + self.coords
        mp = res[1]
        return cv2.remap(img, adj, None, cv2.INTER_LINEAR), mp

    def adjustFlow_G(self, flow, p=3.0, k=5):
        p = p
        k = k
        h, w = flow.shape[:2]
        coord = (np.swapaxes(np.indices((w, h), np.float32), 0, 2))
        cpy = np.copy(flow)
        cpy += coord
        ktree = spatial.cKDTree(np.reshape(cpy, (w * h, 2)))
        reverse = np.swapaxes(np.indices((w, h), np.float32), 0, 2)
        reverse[:][:] = -1000.0
        nearest = ktree.query(coord, k=k)  # ,distance_upper_bound=2.0**0.5)
        mp = np.any((nearest[0] < 1.0), axis=2)
        # identify points that have source points close enough to use
        close_enough = np.any((nearest[0] < 1.0), axis=2)
        # id points that have at least one match 0 away
        exact = np.any((nearest[0] == 0.0), axis=2)
        values = np.asarray([nearest[1] % w, nearest[1] / w])

        for x in range(h):
            for y in range(w):
                found = False
                dist = nearest[0][x, y]
                # skip points too far away
                if not close_enough[x, y]:
                    continue

                # process exact matches
                if exact[x, y]:
                    # find max distance of the k closest source points
                    md_k = np.argmax(((values[1, x, y] - x) ** 2 + (values[0, x, y] - y) ** 2) ** .5)

                    # if mapped distance ==0 and source distance is the greatest, use it
                    if dist[md_k] == 0:
                        reverse[x, y, :] = values[:, x, y, md_k]
                        #                       reverse[x][y][0] = values[0,x,y,md_k]
                        found = True

                # process interpolation points
                if not found:
                    weight_accum = np.sum(1 / dist[np.where(dist[:] > 0)] ** p)
                    w_xyk = np.sum((values[:, x, y, np.where(dist[:] > 0)]) /
                                   (dist[np.where(dist[:] > 0)] ** p), axis=2)
                    reverse[x][y] = (w_xyk / weight_accum)[:, 0]

        return reverse - coord, mp

    def setTime(self, frame_time, truth=None):
        forward_flow = np.multiply(self.flow, 1 - frame_time)
        # cv2.imwrite('fwd_frame.png',imageafy(forward_flow,self.next_frame))
        backward_flow = np.multiply(self.bkflow, frame_time)
        # cv2.imwrite('bwd_frame.png', imageafy(backward_flow, self.next_frame))
        from_prev, mpp = self.warpFlow(self.prvs_frame, backward_flow)
        from_next, mpn = self.warpFlow(self.next_frame, forward_flow)
        # cv2.imwrite('bwd_frame_real' + 'new' + str(self.count) + '.png', from_prev)
        # cv2.imwrite('fwd_frame_real' + 'new' + str(self.count) + '.png', from_next)
        truth = self.next_frame if truth is None else truth
        f = self.frameadjust(from_next, self.prvs_frame, mpp)
        n = self.frameadjust(from_prev, truth, mpn)
        from_next = f
        from_prev = n
        from_prev = np.multiply(from_prev, (1 - frame_time))
        from_next = np.multiply(from_next, frame_time)

        frame = (np.add(from_prev, from_next)).astype(np.uint8)
        self.count += 1
        return frame

    def frameadjust(self, frame, alterframe, mp):
        cpy = np.copy(frame)
        for x in range(len(frame)):
            for y in range(len(frame[0])):
                if np.array_equal(frame[x][y], np.zeros(len(frame[x][y]))):
                    cpy[x][y] = alterframe[x][y]
        return cpy


class FrameAnalyzer:
    def __init__(self, start_time, end_time, fps):
        self.last_frames = []
        self.start_time = start_time
        self.end_time = end_time
        self.fps = fps

    def addFrame(self, frame):
        if self.end_time is not None:
            return
        self.last_frames.append(frame)
        if len(self.last_frames) > 50:
            self.last_frames = self.last_frames[1:]

    def framesToAdd(self):
        if self.end_time is not None:
            return differenceInFramesBetweenMillisecondsAndFrame(self.end_time, self.start_time, self.fps) + 1
        avg_flow = getNormalFlow(self.last_frames)
        std_jump_flow = np.std(self.jump_flow)
        return int(np.rint(std_jump_flow / avg_flow))

    def updateFlow(self, last_frame, next_frame, direction):
        if direction != 'forward':
            prev_frame_gray = cv2.cvtColor(next_frame, cv2.COLOR_BGR2GRAY)
            next_frame_gray = cv2.cvtColor(last_frame, cv2.COLOR_BGR2GRAY)
        else:
            prev_frame_gray = cv2.cvtColor(last_frame, cv2.COLOR_BGR2GRAY)
            next_frame_gray = cv2.cvtColor(next_frame, cv2.COLOR_BGR2GRAY)
        self.jump_flow = cv2api_delegate.calcOpticalFlowFarneback(prev_frame_gray,
                                                                  next_frame_gray,
                                                                  0.8, 7, 15, 3, 7, 1.5, 2)
        self.back_flow =self.jump_flow
        self.jump_flow = cv2api_delegate.calcOpticalFlowFarneback(next_frame_gray,
                                                                  prev_frame_gray,
                                                                  0.8, 7, 15, 3, 7, 1.5, 2)


def smartAddFrames(in_file,
                   out_file,
                   start_time,
                   end_time,
                   codec=None,
                   direction='forward'):
    """
    :param in_file: is the full path of the video file from which to drop frames
    :param out_file: resulting video file
    :param start_time: (milli,frame no) start to fill
    :param end_time: (milli,frame no) end to fill
    :param codec:
    :return:
    """
    logger = logging.getLogger('maskgen')
    import time
    cap = cv2api_delegate.videoCapture(in_file)
    fourcc = cv2api_delegate.get_fourcc(str(codec)) if codec is not None else cap.get(cv2api_delegate.fourcc_prop)
    fps = cap.get(cv2api_delegate.prop_fps)
    height = int(np.rint(cap.get(cv2api_delegate.prop_frame_height)))
    width = int(np.rint(cap.get(cv2api_delegate.prop_frame_width)))
    out_video = cv2api_delegate.videoWriter(out_file, fourcc, fps, (width, height), isColor=1)
    time_manager = VidTimeManager(startTimeandFrame=start_time, stopTimeandFrame=end_time)
    if not out_video.isOpened():
        err = out_file + " fourcc: " + str(fourcc) + " FPS: " + str(fps) + \
              " H: " + str(height) + " W: " + str(width)
        raise ValueError('Unable to create video ' + err)
    try:
        last_frame = None
        frame_analyzer = FrameAnalyzer(start_time, end_time, fps)
        written_count = 0
        while (cap.grab()):
            ret, frame = cap.retrieve()
            frame_analyzer.addFrame(frame)
            elapsed_time = float(cap.get(cv2api_delegate.prop_pos_msec))
            time_manager.updateToNow(elapsed_time)
            if not time_manager.isBeforeTime():
                break
            out_video.write(frame)
            written_count += 1
            last_frame = frame
        next_frame = frame
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('Written {} frames '.format(written_count))
            logger.debug('Smart Add Frames ' + str(start_time) + '  to ' + str(end_time))
            logger.debug("Selected Before {}".format(hashlib.sha256(last_frame).hexdigest()))
            logger.debug("Selected After {}".format(hashlib.sha256(next_frame).hexdigest()))
            ImageWrapper(last_frame).save('before_' + str(time.clock()) + '.png')
            ImageWrapper(next_frame).save('after_' + str(time.clock()) + '.png')
            logger.debug("STD after and before {}".format(np.std(last_frame - next_frame)))
        frame_analyzer.updateFlow(last_frame, next_frame, direction)
        opticalFlow = kdtreeOpticalFlow(last_frame, next_frame, frame_analyzer.jump_flow, frame_analyzer.back_flow)
        frames_to_add = frame_analyzer.framesToAdd()
        lf = last_frame
        written_count = 0
        for i in range(1, int(frames_to_add + 1)):
            frame_scale = i / (1.0 + frames_to_add)
            frame = opticalFlow.setTime(frame_scale)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("frame {}".format(np.std(frame - lf)))
            out_video.write(frame)
            lf = frame
        out_video.write(next_frame)
        written_count+=1
        while (cap.grab()):
            ret, frame = cap.retrieve()
            out_video.write(frame)
            written_count += 1
        logger.debug('Written additioning {} frames '.format(written_count))
    finally:
        cap.release()
        out_video.release()
    return frames_to_add, frames_to_add * (1000.0 / fps)


def copyFrames(in_file,
               out_file,
               start_time,
               end_time,
               paste_time,
               codec=None):
    """
    :param in_file: is the full path of the video file from which to drop frames
    :param out_file: resulting video file
    :param start_time: (milli,frame no) to start to fill
    :param end_time: (milli,frame no) end fil
    :param codec:
    :return:
    """
    import time
    logger = logging.getLogger('maskgen')
    frames_to_write = []
    frames_to_copy = []
    cap = cv2api_delegate.videoCapture(in_file)
    fourcc = cv2api_delegate.get_fourcc(str(codec)) if codec is not None else cap.get(cv2api_delegate.fourcc_prop)
    fps = cap.get(cv2api_delegate.prop_fps)
    height = int(np.rint(cap.get(cv2api_delegate.prop_frame_height)))
    width = int(np.rint(cap.get(cv2api_delegate.prop_frame_width)))
    out_video = cv2api_delegate.videoWriter(out_file, fourcc, fps, (width, height), isColor=1)
    if not out_video.isOpened():
        err = out_file + " fourcc: " + str(fourcc) + " FPS: " + str(fps) + \
              " H: " + str(height) + " W: " + str(width)
        raise ValueError('Unable to create video ' + err)
    copy_time_manager = VidTimeManager(startTimeandFrame=start_time, stopTimeandFrame=end_time)
    paste_time_manager = VidTimeManager(startTimeandFrame=paste_time)
    write_count = 0
    try:
        while (not copy_time_manager.isPastTime() and cap.grab()):
            ret, frame = cap.retrieve()
            elapsed_time = float(cap.get(cv2api_delegate.prop_pos_msec))
            copy_time_manager.updateToNow(elapsed_time)
            paste_time_manager.updateToNow(elapsed_time)
            if not copy_time_manager.isBeforeTime() and not copy_time_manager.isPastTime():
                frames_to_copy.append(frame)
            if not paste_time_manager.isBeforeTime():
                frames_to_write.append(frame)
            else:
                out_video.write(frame)
                write_count += 1
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("First to copy {}".format(hashlib.sha256(frames_to_copy[0]).hexdigest()))
            logger.debug("Last to copy {}".format(hashlib.sha256(frames_to_copy[-1]).hexdigest()))
            ImageWrapper(frames_to_copy[0]).save('first_' + str(time.clock()) + '.png')
            ImageWrapper(frames_to_copy[-1]).save('last_' + str(time.clock()) + '.png')
        if len(frames_to_write) > 0:
            # paste prior to copy
            for copy_frame in frames_to_copy:
                out_video.write(copy_frame)
            for write_frame in frames_to_write:
                out_video.write(write_frame)
        else:
            # paste after to copy
            frame = None
            while (paste_time_manager.isBeforeTime() and cap.grab()):
                ret, frame = cap.retrieve()
                elapsed_time = float(cap.get(cv2api_delegate.prop_pos_msec))
                paste_time_manager.updateToNow(elapsed_time)
                if paste_time_manager.isBeforeTime():
                    out_video.write(frame)
                    write_count += 1
            for copy_frame in frames_to_copy:
                out_video.write(copy_frame)
            if frame is not None:
                out_video.write(frame)
        while (cap.grab()):
            ret, frame = cap.retrieve()
            out_video.write(frame)
    finally:
        cap.release()
        out_video.release()
    return write_count
