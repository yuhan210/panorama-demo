import os
import sys
sys.path.append('lib')
import math
import pickle
import inflection
import redis
from utils import load_all_modules_dict_local, word_pref_to_stopword_pref_dict
from nlp import get_stopwords

r = redis.StrictRedis()
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

def get_features(msr, vgg, rcnn, start_fid, end_fid, width, height):

    # object tags
    obj_tags = normalize_objtags(msr, vgg, rcnn, start_fid, end_fid)

    # visual features
    get_visual_features(rcnn, start_fid, end_fid, width, height)

def get_visual_features(rcnn, start_fid, end_fid, width, height):
    #rcnn_tfs += [{'score': score, 'bbox': bbox, 'obj': obj}]
    rcnn_objtags = list(set([rcnn[x]['obj'] for x in xrange(start_fid, end_fid)]))
    obj_features = dict(zip(rcnn_objtags, [{} for x in rcnn_objtags]))

    for target_objtag in rcnn_objtags:
        sizes = [] 
        dwell_frames = []
        moving_speed = []
        prev_obj = None 
        for fid in xrange(start_fid, end_fid):  
            # dwell time, size (biggest obj), moving speed (biggest obj)

            # get biggest object in this frame
            max_obj_size = -1
            max_obj_bbx = None
            for obj_idx, obj in enumerate(rcnn[fid]):
                if obj['obj'] == target_objtag:
                    dwell_frames += [fid]

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

                if prev_obj == None: 
                    prev_obj = (fid, (max_obj_bbx[2] + max_obj_bbx[0])/2, (max_obj_bbx[3] + max_obj_bbx[1])/2)
                else:
                 
                    
        dwell_time = len(list(set(dwell_frames)))

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


def store_feature_index(video_name, msr, vgg, rcnn, video_len):
    WINDOW_STEP = 1 * int(round(video_frame_rate[video_name][0]))
    WINDOW_SIZE = 5 * int(round(video_frame_rate[video_name][0]))
    width = video_frame_rate[video_name][1]    
    height = video_frame_rate[video_name][2] 
 
    end_fid = WINDOW_SIZE
    while end_fid < video_len:
        start_fid = end_fid - WINDOW_SIZE 
        get_features(msr, vgg, rcnn, start_fid, end_fid, width, height)
        
        end_fid += WINDOW_STEP 

if __name__ == "__main__":

    #vid = [1,2,3,4]
    #key = "123-dog"
    #r.sadd(key, *vid)
    #p = r.smembers(key)

    for video_name in video_names:
        print video_name
        video_len = video_lengths[video_name]
        rcnn_dict, vgg_dict, dummy, msr_cap_dict, (rcnn_bbx_data, rcnn_bbx_dict) = load_all_modules_dict_local(video_name)
        msr, vgg, rcnn = get_objtags(video_name, vgg_dict, msr_cap_dict, rcnn_bbx_dict, video_len)

        store_feature_index(video_name, msr, vgg, rcnn, video_len)

