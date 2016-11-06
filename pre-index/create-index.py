import os
import sys
sys.path.append('lib')
import math
import pickle
import inflection
import redis
import numpy as np
from utils import load_all_modules_dict_local, word_pref_to_stopword_pref_dict
from nlp import get_stopwords

_redis = redis.StrictRedis()
stop_words = get_stopwords(1)
wptospd = word_pref_to_stopword_pref_dict()

with open('../data/stream_rates.pickle') as fh:
    video_frame_rate = pickle.load(fh)    

with open('./lib/data/video_frame_num.pickle') as fh:
    video_lengths = pickle.load(fh)

with open('./lib/data/video_list.txt') as fh:
    video_names = fh.read().split()

'''
1. Assume all videos start at the same time
2. Every second - store features in feature table (key: ts-vid, value: features) 
3. Every second - create reverse table (key: ts-tag, value: a list of sid)  
'''

def get_objtags(video_name, vgg_dict, msr_cap_dict, rcnn_bbx_dict, video_len, VGG_THRESH = 0.8, MSR_THRESH = 0.6, RCNN_THRESH = 0.5):

    msr = {}
    vgg = {}
    rcnn = {}

    for fid in xrange(video_len):
        vgg_tfs = {}
        msr_tfs = {}
        rcnn_tfs = []

        frame_path = '/mnt/frames/' + video_name + '/' + str(fid) + '.jpg'

        vgg_data = vgg_dict[frame_path]
        msr_data = msr_cap_dict[frame_path]
        if frame_path in rcnn_bbx_dict:
            rcnn_data = rcnn_bbx_dict[frame_path]
        else:
            rcnn_data = None 

        if rcnn_data is not None:
            for rcnn_frame_data in rcnn_data['pred']:
                score = rcnn_frame_data['score']
                bbox = rcnn_frame_data['bbox']
                obj = rcnn_frame_data['class']
                if score > RCNN_THRESH and obj.find('background') < 0:
                    rcnn_tfs += [{'score': score, 'bbox': bbox, 'obj': obj}]

        for wid, w in enumerate(vgg_data['pred']['text']):
            w = wptospd[w]
            prob = (-1)*vgg_data['pred']['conf'][wid]
            if w in stop_words:
                continue
            if w not in vgg_tfs:
                vgg_tfs[w] = prob
            else:
                vgg_tfs[w] += prob


        MSRTOPK = 60
        deno = sum([math.exp(msr_data['words']['prob'][wid]) for wid, w in enumerate(msr_data['words']['text'][:MSRTOPK])])
        for wid, w in enumerate(msr_data['words']['text'][:MSRTOPK]):
            w = inflection.singularize(w)
            if w not in stop_words:
                exp_prob = math.exp(msr_data['words']['prob'][wid])/deno

                if w not in msr_tfs:
                    msr_tfs[w] = exp_prob
                else:
                    msr_tfs[w] += exp_prob
        msr_tfs = [(x, msr_tfs[x]) for x in msr_tfs if msr_tfs[x] > MSR_THRESH]
        vgg_tfs = [(x, vgg_tfs[x]) for x in vgg_tfs if vgg_tfs[x] > VGG_THRESH]

        msr[fid] = msr_tfs
        vgg[fid] = vgg_tfs
        rcnn[fid] = rcnn_tfs

    return msr, vgg, rcnn

def get_features(msr, vgg, rcnn, start_fid, end_fid, width, height, fps):

    # object tags
    obj_tags = normalize_objtags(msr, vgg, rcnn, start_fid, end_fid)

    # visual features
    obj_vis_features = get_visual_features(rcnn, start_fid, end_fid, width, height, fps)

    return obj_tags, obj_vis_features

def get_visual_features(rcnn, start_fid, end_fid, width, height, fps):
    #rcnn_tfs += [{'score': score, 'bbox': bbox, 'obj': obj}]
    rcnn_objtags = []
    for x in xrange(start_fid, end_fid):
        for obj_info in rcnn[x]:
            if obj_info['obj'] not in rcnn_objtags:
                rcnn_objtags += [obj_info['obj']]
    obj_features = dict(zip(rcnn_objtags, [{} for x in rcnn_objtags]))

    for target_objtag in rcnn_objtags:
        sizes = [] 
        dwell_frames = []
        moving_speeds = []
        prev_obj = None 
        for fid in xrange(start_fid, end_fid):  
            # dwell time, size (biggest obj), moving speed (biggest obj)

            # get biggest object in this frame
            max_obj_size = -1
            max_obj_bbx = None
            for obj_idx, obj in enumerate(rcnn[fid]):
                if obj['obj'] == target_objtag:

                    bbox = obj['bbox']
                    bbox_w = (bbox[2] - bbox[0])/(width * 1.0)
                    bbox_h = (bbox[3] - bbox[1])/(height * 1.0)
                    size = bbox_w * bbox_h

                    if size > max_obj_size:    
                        max_obj_size = size
                        max_obj_bbx = bbox

            # the target obj tag is in this frame
            if max_obj_size > 0:
                sizes += [max_obj_size]
                dwell_frames += [fid]

                if prev_obj == None: 
                    prev_obj = (fid, (max_obj_bbx[2] + max_obj_bbx[0])/2, (max_obj_bbx[3] + max_obj_bbx[1])/2)
                else:
                    dist = get_dist(prev_obj, max_obj_bbx, width, height) 
                    time = (fid - prev_obj[0])/float(fps)
                    speed = dist/time
                    moving_speeds += [speed] 
                    
        dwell_time = len(dwell_frames)
        ave_moving_speed = np.mean(moving_speeds)
        ave_size = np.mean(sizes)

        obj_features[target_objtag] = {'moving_speed': ave_moving_speed, 'dwell_time': dwell_time, 'size': ave_size}
    return obj_features

def get_dist(x, y, w, h):
    return math.sqrt( ((x[1] - y[1])/(w * 1.0))** 2 + ((x[2]-y[2])/(h * 1.0)) ** 2)

def normalize_objtags(msr, vgg, rcnn, start_fid, end_fid, OCCUR_PERC = 0.3):

    objs = {}
    for fid in xrange(start_fid, end_fid):
        frame_objs = []
        frame_objs = [tup[0] for tup in msr[fid]]
        frame_objs += [tup[0] for tup in vgg[fid]]
        frame_objs += [d['obj'] for d in rcnn[fid]]

        for obj in list(set(frame_objs)):
            if obj not in objs:
                objs[obj] = 1
            else:
                objs[obj] += 1

    window_size = end_fid - start_fid
    window_objs = [x for x in objs if objs[x] > window_size * OCCUR_PERC]
    #print 'smoothing- ', window_objs     
    return window_objs


def create_feature_index(vid, video_name, msr, vgg, rcnn, video_len):
    fps = int(round(video_frame_rate[video_name][0]))
    WINDOW_STEP = 1 * fps
    WINDOW_SIZE = 5 * fps
    width = video_frame_rate[video_name][1]    
    height = video_frame_rate[video_name][2] 

    end_fid = WINDOW_SIZE
    ts = 5
    while end_fid < video_len:
        start_fid = end_fid - WINDOW_SIZE 
        print start_fid, end_fid
        obj_tags, obj_vis_features = get_features(msr, vgg, rcnn, start_fid, end_fid, width, height, fps)
        # feature table
        redis_feature_value = {'obj_tags': obj_tags, 'obj_vis_features': obj_vis_features}   
        redis_feature_key = str(ts) + ':' + str(vid)
        _redis.set(redis_feature_key, pickle.dumps(redis_feature_value))
        
        # reverse table
        for tag in obj_tags:
            redis_reverse_key = str(ts) + ':' + str(tag)
            _redis.sadd(redis_reverse_key, vid)

        end_fid += WINDOW_STEP 
        ts += 1


if __name__ == "__main__":
    '''
    vid = [1,2]
    key = "123-dog"
    _redis.sadd(key, *vid)
    p = _redis.smembers(key)
    print p
    vid = [2,3,5]
    _redis.sadd(key, *vid)
    p = _redis.smembers(key)
    print p
    '''

    for vid, video_name in enumerate(video_names):
        print vid, video_name

        video_len = video_lengths[video_name]
        rcnn_dict, vgg_dict, dummy, msr_cap_dict, (rcnn_bbx_data, rcnn_bbx_dict) = load_all_modules_dict_local(video_name)
        msr, vgg, rcnn = get_objtags(video_name, vgg_dict, msr_cap_dict, rcnn_bbx_dict, video_len)

        create_feature_index(vid, video_name, msr, vgg, rcnn, video_len)
