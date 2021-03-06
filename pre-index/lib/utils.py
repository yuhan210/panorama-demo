from nlp import *
from wordnet import *
from vision import *
import inflection 
import math
import json
import csv
import os
import cv2

BAD_WORDS = ['none', 'blurry', 'dark']

def remove_start_end_fid(video_s_e):
    if video_s_e.find('.mp4') >= 0:
        video_s_e = video_s_e[:-4]

    pos = [i for i, w in enumerate(video_s_e) if w == '_']
    return video_s_e[:pos[-2]], video_s_e[pos[-2]+1 : pos[-1]], video_s_e[pos[-1]+1:]

def combine_all_modeldicts(_vgg_data, _msr_data, _rcnn_data, _fei_data, frame_paths, stop_word_choice = 0):

    stop_words = get_stopwords(stop_word_choice)
    wptospd = word_pref_to_stopword_pref_dict()
    convert_dict = convert_to_equal_word()

    tf_list = {}
    for frame_path in frame_paths:

        frame_name = frame_path.split('/')[-1]
        rcnn_data = _rcnn_data[frame_path]
        vgg_data = _vgg_data[frame_path]
        msr_data = _msr_data[frame_path]
        #fei_data = _fei_data[frame_path]
   
        # combine words
        rcnn_ws = []
        if len(rcnn_data) > 0:
            for rcnn_idx, word in enumerate(rcnn_data['pred']['text']):
                ## the confidence is higher than 10^(-3) and is not background
                if rcnn_data['pred']['conf'][rcnn_idx] > 0.0005 and word not in stop_words:
                    rcnn_ws += [word]

        vgg_ws = []
        if len(vgg_data) > 0:
            for vgg_idx, w in enumerate(vgg_data['pred']['text']):
                w = wptospd[w]
                if w in convert_dict:
                    w = convert_dict[w]
                prob = (-1)*vgg_data['pred']['conf'][vgg_idx]
                if w not in stop_words and prob > 0.01:
                    vgg_ws += [w]

        
        fei_ws = []
        ''' 
        if len(fei_data) > 0:
            str_list = fei_data['candidate']['text']
            for s in str_list:
                for w in s.split(' '):
                    w = inflection.singularize(w)
                    if w not in stop_words and w not in fei_ws:
                        fei_ws += [w]         
        '''
        msr_ws = [] 
        if len(msr_data) > 0:
            for msr_idx, w in enumerate(msr_data['words']['text']):
                w = inflection.singularize(w)

                prob = msr_data['words']['prob'][msr_idx]
                if w in convert_dict:
                    w = convert_dict[w]
                if w not in stop_words and len(w) != 0 and prob > -5 and msr_idx < 30:
                    msr_ws += [w]

        words = {}
        for w in rcnn_ws:
            if w not in words:
                words[w] = 1
            else:
                words[w] += 1
        for w in vgg_ws:
            if w not in words:
                words[w] = 1
            else:
                words[w] += 1
        
        for w in fei_ws:
            if w not in words:
                words[w] = 1
            else:
                words[w] += 1
    
        for w_idx, w in enumerate(msr_ws):
            if w not in words:
                words[w] = 1
            else:
                words[w] += 1

        if '' in words:
            words.pop('', None)

        tf_list[frame_name] = words
    
    return tf_list



def get_combined_tfs(tfs_dict):

    combined_tfs = {}
    # normalize
    deno = len(tfs_dict)
    for frame_name in tfs_dict:
        tf = tfs_dict[frame_name]
        for w in tf:
            if w not in combined_tfs:
                combined_tfs[w] = 1
            else:
                combined_tfs[w] += 1

    for w in combined_tfs:
        combined_tfs[w] /= (deno * 1.0)
 
    return combined_tfs


'''
# of subsampled words/# of all words
'''
def detailed_measure(all_tf, subsampled_tf):
    match_count = 0
    for w in all_tf:
        if w in subsampled_tf:
            match_count += 1
 
    if len(all_tf) == 0:
        return -1

    return match_count/(len(all_tf) * 1.0)
    


def get_video_fps(video_name):
    if video_name.find('.mp4') >= 0:
        video_name = video_name[:-4]
    with open('/home/t-yuche/lib/data/video_metadata.pickle') as fh:
        info = pickle.load(fh)
    
    return info[video_name]
    '''
    video_path = os.path.join('/mnt/videos', video_name)
    if video_path.find('.mp4') < 0:
        video_path += '.mp4'
    cap = cv2.VideoCapture(video_path)    
    fps  = cap.get(cv2.cv.CV_CAP_PROP_FPS) 
    w  = int(cap.get(cv2.cv.CV_CAP_PROP_FRAME_WIDTH))
    h  = int(cap.get(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT))
    return fps, w, h
    '''
def get_video_frame_num(video_name):
    return len(os.listdir(os.path.join('/mnt/frames', video_name)))

def get_video_res(video_name):
    mv_data, enc_data = getCompressedInfoFromLog(video_name)

    return enc_data['metadata']['w'], enc_data['metadata']['h']

def deprecation(message):
    from warnings import warn
    warn(message, DeprecationWarning, stacklevel=2)

def naive_subsample_frames(all_frames, FRAME_RETAIN_RATE):

    all_frames = sorted(all_frames, key=lambda x: int(x.split('.')[0]))
    n_picked_frames = len(all_frames) * FRAME_RETAIN_RATE
    step = n_picked_frames/((len(all_frames) ) * 1.0)
    track = 0
    counter = 0
    retained_frames = [] 
    for idx, frame_name in enumerate(all_frames):
        if int(track) == counter:
            retained_frames += [frame_name]
            counter += 1
        track += step

    retained_frames = sorted(retained_frames, key=lambda x: int(x.split('.')[0]))
    return retained_frames


def isbadframe(_turker_data, tfs_obj):
    # tfs_obj = {'frame_name': , 'tf':}
    # _turker_data [{"gt_labels": [], "frame_name": "0.jpg"}, {"gt_labels": ["street sign", "sign"], "frame_name": "30.jpg"}]

    frame_name = tfs_obj['frame_name']
    tf = tfs_obj['tf']
    #  first check if it is a turker labeled frame 
    for turker_obj in _turker_data:
        if turker_obj['frame_name'] == frame_name:
            if turker_isbadframe(turker_obj['gt_labels']):
                return True
     
    # idenitify bad frame based on some heuristics
    # TODO: think deeper about it
    
    #for w in tf: 
    #    if w in BAD_WORDS:
    #        return True

    return False

def turker_isbadframe(gt_labels): 
    # only work for turker labled frames
     
    for bw in BAD_WORDS:
        if bw in gt_labels:
            return True
   
    stop_words = get_stopwords() 
    for sw in stop_words:
        if sw in gt_labels:
            gt_labels.remove(sw) 
    
    if len(gt_labels) == 0:
        return True

    return False

def load_video_rcnn_bbx(rcnn_bbx_folder, video_name):
    # bbx is [x1, y1, x2, y2] 

    file_pref = os.path.join(rcnn_bbx_folder, video_name)    
    filepath = file_pref + '_rcnnbbx.json'

    if not os.path.exists(filepath):
        return [], {}

    # load rcnn bbx
    with open(file_pref + '_rcnnbbx.json') as json_file:
        rcnn_bbx_data = json.load(json_file)

    rcnn_bbx_data = sorted(rcnn_bbx_data['imgblobs'], key=lambda x: int(x['img_path'].split('/')[-1].split('.')[0]))

    rcnn_bbx_dict = {}
    for item in rcnn_bbx_data:
        image_path = item['img_path']
        rcnn_bbx_dict[image_path] = {'pred': item['pred'], 'rcnn_time': item['rcnn_time']}

    return rcnn_bbx_data, rcnn_bbx_dict


def cos_similarty(a_dict, b_dict):
    '''
    Compute the cos similarity between two tfs (two dictionary)
    '''   
 
    space = list(set(a_dict.keys()) | set(b_dict.keys()))
    # compute consine similarity (a dot b/ ||a|| * ||b||)
    sumab = 0.0
    sumaa = 0.0
    sumbb = 0.0

    for dim in space:

        a = 0.0
        b = 0.0
        if dim in a_dict:
            a = a_dict[dim]
        if dim in b_dict:
            b = b_dict[dim]
        
        sumab += a * b
        sumaa += a * a
        sumbb += b * b        
  
    if sumab == 0:
        return 0
    else: 
        return sumab/(math.sqrt(sumaa) * math.sqrt(sumbb))
 


def combine_all_models_tmp(video_name, _vgg_data, _msr_data, _rcnn_data, _fei_data):

    stop_words = get_stopwords()
    wptospd = word_pref_to_stopword_pref_dict()
    convert_dict = convert_to_equal_word()

    tf_list = []
    assert(len(_vgg_data) == len(_msr_data))
    assert(len(_rcnn_data) == len(_fei_data))
    assert(len(_vgg_data) == len(_fei_data))

    for fid in xrange(len(_vgg_data)):

        rcnn_data = _rcnn_data[fid]
        vgg_data = _vgg_data[fid]
        msr_data = _msr_data[fid]
        fei_data = _fei_data[fid]
   
        frame_name = rcnn_data['image_path'].split('/')[-1]
        assert(rcnn_data['image_path'] == vgg_data['img_path'])
        assert(rcnn_data['image_path'] == msr_data['img_path'])
        assert(rcnn_data['image_path'] == fei_data['img_path'])

        # combine words
        rcnn_ws = []
        if len(rcnn_data) > 0:
            for rcnn_idx, word in enumerate(rcnn_data['pred']['text']):
                ## the confidence is higher than 10^(-3) and is not background
                if rcnn_data['pred']['conf'][rcnn_idx] > 0.0005 and word not in stop_words:
                    rcnn_ws += [word]
 
        vgg_ws = []
        if len(vgg_data) > 0:        
            vgg_ws = [w for w in vgg_data['pred']['text']]
    
        fei_ws = [] 
        if len(fei_data) > 0:
            str_list = fei_data['candidate']['text']
            for s in str_list:
                for w in s.split(' '):
                    w = inflection.singularize(w)
                    if w not in stop_words and w not in fei_ws:
                        fei_ws += [w]         

        msr_ws = [] 
        if len(msr_data) > 0:
            for msr_idx, w in enumerate(msr_data['words']['text']):
                w = inflection.singularize(w)
                prob = msr_data['words']['prob'][msr_idx]
                if w not in stop_words and w not in msr_ws:
                    msr_ws += [w]

        words = {}
        for w in rcnn_ws:
            if w not in words:
                words[w] = 1
            else:
                words[w] += 1
        for w in vgg_ws:
            
            w = wptospd[w]
            if w in convert_dict:
                w = convert_dict[w]
            if w not in words:
                words[w] = 1
            else:
                words[w] += 1
        
        for w in fei_ws:
            if w not in words:
                words[w] = 1
            else:
                words[w] += 1
    
        for w_idx, w in enumerate(msr_ws):
            if w not in words:
                words[w] = 1
            else:
                words[w] += 1

        if '' in words:
            words.pop('', None)

        tf_list += [{'frame_name': frame_name, 'tf': words}]

    return tf_list

def combine_all_models(video_name, _vgg_data, _msr_data, _rcnn_data, _fei_data):

    stop_words = get_stopwords()
    wptospd = word_pref_to_stopword_pref_dict()
    convert_dict = convert_to_equal_word()

    tf_list = []
    assert(len(_vgg_data) == len(_msr_data))
    assert(len(_rcnn_data) == len(_fei_data))
    assert(len(_vgg_data) == len(_fei_data))

    for fid in xrange(len(_vgg_data)):

        rcnn_data = _rcnn_data[fid]
        vgg_data = _vgg_data[fid]
        msr_data = _msr_data[fid]
        fei_data = _fei_data[fid]
   
        frame_name = rcnn_data['image_path'].split('/')[-1]
        assert(rcnn_data['image_path'] == vgg_data['img_path'])
        assert(rcnn_data['image_path'] == msr_data['img_path'])
        assert(rcnn_data['image_path'] == fei_data['img_path'])

        # combine words
        rcnn_ws = []
        if len(rcnn_data) > 0:
            for rcnn_idx, word in enumerate(rcnn_data['pred']['text']):
                ## the confidence is higher than 10^(-3) and is not background
                if rcnn_data['pred']['conf'][rcnn_idx] > 0.0005 and word not in stop_words:
                    rcnn_ws += [word]
        vgg_ws = []
        if len(vgg_data) > 0:        
            vgg_ws = [w for w in vgg_data['pred']['text']]
   
        fei_ws = [] 
        '''
        if len(fei_data) > 0:
            str_list = fei_data['candidate']['text']
            for s in str_list:
                for w in s.split(' '):
                    w = inflection.singularize(w)
                    if w not in stop_words and w not in fei_ws:
                        fei_ws += [w]         
        '''
        msr_ws = [] 
        if len(msr_data) > 0:
            for msr_idx, w in enumerate(msr_data['words']['text']):
                w = inflection.singularize(w)
                prob = msr_data['words']['prob'][msr_idx]
                if w not in stop_words and w not in msr_ws and prob > -5:
                    msr_ws += [w]

        words = {}
        for w in rcnn_ws:
            if w not in words:
                words[w] = 1
            else:
                words[w] += 1
        for w in vgg_ws:
            
            w = wptospd[w]
            if w in convert_dict:
                w = convert_dict[w]
            if w not in words:
                words[w] = 1
            else:
                words[w] += 1
        
        for w in fei_ws:
            if w not in words:
                words[w] = 1
            else:
                words[w] += 1
    
        for w_idx, w in enumerate(msr_ws):
            if w not in words:
                words[w] = 1
            else:
                words[w] += 1

        if '' in words:
            words.pop('', None)

        tf_list += [{'frame_name': frame_name, 'tf': words}]

    return tf_list


def getwnid(w):

    with open('/home/t-yuche/caffe/data/ilsvrc12/synset_words.txt') as f:
        for l in f.readlines():
            wnid = l.strip().split(' ')[0]
            name = [x.strip() for x in ' '.join(l.strip().split(' ')[1:]).split(',')][0]

            if name == w:
                return wnid


def loadKeyFrames(video_name):

    KEYFRAME_FOLDER = '/home/t-yuche/gt-labeling/frame-subsample/keyframe-info'
    keyframe_file = os.path.join(KEYFRAME_FOLDER, video_name + '_uniform.json')

    with open(keyframe_file) as json_file:
        keyframes = json.load(json_file)

    FRAME_FOLDER = '/mnt/frames'
    keyframe_filenames = [ os.path.join(FRAME_FOLDER, video_name, x['key_frame']) for x in keyframes['img_blobs'] ]

    return keyframe_filenames





#TODO: also load rcnn bbx
def load_all_modules(video_name):
   
    if not os.path.exists(os.path.join('/mnt/tags/rcnn-info-all', video_name + '_rcnnrecog.json')) or not os.path.exists(os.path.join('/mnt/tags/vgg-classify-all', video_name + '_recog.json')) or not os.path.exists(os.path.join('/mnt/tags/msr-caption-all', video_name + '_msrcap.json')) or not os.path.exists(os.path.join('/mnt/tags/fei-caption-all', video_name + '_5_caption.json')): #or not os.path.exists(os.path.join('/mnt/tags/rcnn-bbx-tmp', video_name + '_rcnnbbx.json')):
        return None, None, None, None, None

    rcnn_data, rcnn_dict = load_video_rcnn('/mnt/tags/rcnn-info-all', video_name)
    vgg_data, vgg_dict = load_video_recog('/mnt/tags/vgg-classify-all', video_name)
    fei_caption_data, fei_caption_dict = load_video_caption('/mnt/tags/fei-caption-all', video_name)
    msr_cap_data, msr_cap_dict = load_video_msr_caption('/mnt/tags/msr-caption-all', video_name)
    #rcnn_bbx = load_video_rcnn_bbx('/mnt/tags/rcnn-bbx-tmp', video_name) 

    return rcnn_data, vgg_data, fei_caption_data, msr_cap_data, None

def load_all_modules_dict_local(video_name):
   
    rcnn_data, rcnn_dict = load_video_rcnn('/home/ubuntu/tags/rcnn-info-all', video_name)
    vgg_data, vgg_dict = load_video_recog('/home/ubuntu/tags/vgg-classify-all', video_name)
    #fei_caption_data, fei_caption_dict = load_video_caption('/mnt/tags/fei-caption-all', video_name)
    msr_cap_data, msr_cap_dict = load_video_msr_caption('/home/ubuntu/tags/msr-caption-all', video_name)
    rcnn_bbx_data, rcnn_bbx_dict = load_video_rcnn_bbx('/home/ubuntu/tags/rcnn-bbx-all', video_name) 

    return rcnn_dict, vgg_dict, None, msr_cap_dict, (rcnn_bbx_data, rcnn_bbx_dict)

#TODO: also load rcnn bbx
def load_all_modules_dict(video_name):
   
    if not os.path.exists(os.path.join('/mnt/tags/rcnn-info-all', video_name + '_rcnnrecog.json')) or not os.path.exists(os.path.join('/mnt/tags/vgg-classify-all', video_name + '_recog.json')) or not os.path.exists(os.path.join('/mnt/tags/msr-caption-all', video_name + '_msrcap.json')) or not os.path.exists(os.path.join('/mnt/tags/fei-caption-all', video_name + '_5_caption.json')): #or not os.path.exists(os.path.join('/mnt/tags/rcnn-bbx-tmp', video_name + '_rcnnbbx.json')):
        return None, None, None, None, None

    rcnn_data, rcnn_dict = load_video_rcnn('/mnt/tags/rcnn-info-all', video_name)
    vgg_data, vgg_dict = load_video_recog('/mnt/tags/vgg-classify-all', video_name)
    #fei_caption_data, fei_caption_dict = load_video_caption('/mnt/tags/fei-caption-all', video_name)
    msr_cap_data, msr_cap_dict = load_video_msr_caption('/mnt/tags/msr-caption-all', video_name)
    #rcnn_bbx = load_video_rcnn_bbx('/mnt/tags/rcnn-bbx-tmp', video_name) 

    return rcnn_dict, vgg_dict, None, msr_cap_dict, None

def load_all_labels(video_name):
    deprecation("Using local_all_moduels(video_name) instead")

    rcnn_data = load_video_rcnn('/mnt/tags/rcnn-info-all', video_name)
    vgg_data = load_video_recog('/mnt/tags/vgg-classify-keyframe', video_name)
    fei_caption_data = load_video_caption('/mnt/tags/fei-caption-keyframe', video_name)
    msr_cap_data = load_video_msr_caption('/mnt/tags/msr-caption-keyframe', video_name)

    return rcnn_data, vgg_data, fei_caption_data, msr_cap_data 
    

def loadKeyFrameFilenames(video_name):

    KEYFRAME_FOLDER = '/home/t-yuche/gt-labeling/frame-subsample/keyframe-info'
    keyframe_file = os.path.join(KEYFRAME_FOLDER, video_name + '_uniform.json')

    with open(keyframe_file) as json_file:
        keyframes = json.load(json_file)['img_blobs']

    return keyframes

def load_suggested_labels(video_name, anno_folder="/home/t-yuche/gt-labeling/suggested-labels"):

    files = os.listdir(os.path.join(anno_folder, video_name))
    files = sorted(files, key=lambda x: int(x.split('.')[0])) 
   
    ds = {}
    for f in files:
        with open(os.path.join(anno_folder, video_name, f)) as json_file:
            anno_data = json.load(json_file)  
            ds[f.split('.')[0] + '.jpg'] = anno_data['choices']
                     
    return ds



def load_video_processed_turker(video_name, turker_folder = '/mnt/tags/turker-all'):
    '''
    Return singularized turker label (after wordnet processing)
    labelobj_list = [{"gt_labels": [], "frame_name": "0.jpg"}, {"gt_labels": ["street sign", "sign"], "frame_name": "30.jpg"}]
    labeldict = ["0.jpg": [], "30.jpg": ["street sign", "sign"]]
    '''
    file_path = os.path.join(turker_folder, video_name + '.json')
        
    if not os.path.exists(file_path):
        return None    

    with open(file_path) as fh:
        labelobj_list = json.load(fh) 

    label_dict = {}
    for labelobj in labelobj_list:
        label_dict[labelobj['frame_name']] = labelobj['gt_labels']

    return labelobj_list, label_dict

def load_video_turker(turker_folder, video_name):
    '''
    Return a dict: 
    key: frame_id (str)
    value: a list of smaller lists(each list is a choice)
    '''
    
    folder = os.path.join(turker_folder, video_name)
    
    ds = {}
    if not os.path.exists(folder):
        return ds

    files = sorted(os.listdir(folder), key = lambda x: int(x.split('.')[0]))
    for f in files:
        f_path = os.path.join(folder, f)
        with open(f_path) as json_file:
            turker_data = json.load(json_file)
            ds[f.split('.')[0] + '.jpg'] = turker_data['gt_labels'] 

    return ds

def load_turker_labels(amtresults_folder):
    
    ds = {}
    for f in os.listdir(amtresults_folder):
        csv_file = open(os.path.join(amtresults_folder, f))
        csv_reader = csv.DictReader(csv_file, delimiter="\t")
        
        for row in csv_reader:
            if row['Answer.n_selections'] != None and len(row['Answer.n_selections']) > 0:
                video_name = row['Answer.video']
                frame_name = row['Answer.frame_name']
                selections = row['Answer.selections'].split(',')
    
                if video_name not in ds:
                    ds[video_name] = []
                
                img_blob = {}
                img_blob['frame_name'] = frame_name
                img_blob['selections'] = selections
                ds[video_name] += [img_blob]
    
             
                #ds[video_name +  frame_name] = selections
        csv_file.close()
                 
    return ds            



def getVerbTfFromCaps(captions, method = 'equal'):
    #TODO: implement weighted version
  
    verb_tf = {}
    for sentence in captions:

        verbs = getVerbFromStr(sentence)
        for verb in verbs:
            if verb not in verb_tf:
                verb_tf[verb] = 1
            else:
                verb_tf[verb] += 1        

    return verb_tf 


def load_video_msr_caption(msrcaption_folder, video_name):

    file_pref = os.path.join(msrcaption_folder, video_name)
    
    # load msr caption
    with open(file_pref + '_msrcap.json') as json_file:
        msrcap_data = json.load(json_file) 

    msrcap_data = sorted(msrcap_data['imgblobs'], key=lambda x: int(x['img_path'].split('/')[-1].split('.')[0]))

    msrcap_dict = {}
    for item in msrcap_data:
        image_path = item['img_path']
        msrcap_dict[image_path] = {'caption_time': item['caption_time'], 'words': item['words']}

    return msrcap_data, msrcap_dict

def load_video_peopledet(peopled_folder, video_name):

    file_pref = os.path.join(peopled_folder, video_name)

    # load recognition
    with open(file_pref + '_openpd.json') as json_file:
        pd_data = json.load(json_file)

    pd_data = sorted(pd_data['img_blobs'], key=lambda x: int(x['img_name'].split('.')[0]))
    
    return pd_data


def load_video_ocr(ocr_folder, video_name):
    file_pref = os.path.join(ocr_folder, video_name)
    
    # load recognition
    with open(file_pref + '_ocr.json') as json_file:
        ocr_data = json.load(json_file)

    ocr_data = sorted(ocr_data['img_blobs'], key=lambda x: int(x['img_name'].split('.')[0]))
    
    return ocr_data

def load_video_dlibfd(dlibfd_folder, video_name):

    file_pref = os.path.join(dlibfd_folder, video_name)
    
    # load face detection
    with open(file_pref + '_dlibfd.json') as json_file:
        faced_data = json.load(json_file)

    faced_data = sorted(faced_data['img_blobs'], key=lambda x: int(x['img_name'].split('.')[0]))
    
    return faced_data

def load_video_rcnn(rcnn_folder, video_name):
    
    file_pref = os.path.join(rcnn_folder, video_name)
    
    # load face detection
    with open(file_pref + '_rcnnrecog.json') as json_file:
        rcnn_data = json.load(json_file)

    rcnn_data = sorted(rcnn_data['imgblobs'], key=lambda x: int(x['image_path'].split('/')[-1].split('.')[0]))
    
    rcnn_dict = {}
    for item in rcnn_data:
        image_path = item['image_path']
        rcnn_dict[image_path] = {'rcnn_time': item['rcnn_time'], 'pred': item['pred']}

        
    return rcnn_data, rcnn_dict

    

def load_video_opencvfd(opencvfd_folder, video_name):
    file_pref = os.path.join(opencvfd_folder, video_name)
    
    # load face detection
    with open(file_pref + '_openfd.json') as json_file:
        faced_data = json.load(json_file)

    faced_data = sorted(faced_data['img_blobs'], key=lambda x: int(x['img_name'].split('.')[0]))
    
    return faced_data


def load_video_recog(recog_folder, video_name):
    
    file_pref = os.path.join(recog_folder, video_name)
    
    # load recognition
    with open(file_pref + '_recog.json') as json_file:
        recog_data = json.load(json_file)

    recog_data = sorted(recog_data['imgblobs'], key=lambda x: int(x['img_path'].split('/')[-1].split('.')[0]))
  
    recog_dict = {} 
    for item in recog_data:
        image_path = item['img_path']
        recog_dict[image_path] = {'pred': item['pred']}
     
    return recog_data, recog_dict

def load_video_caption(caption_folder, video_name):

    file_pref = os.path.join(caption_folder, video_name)

    # load caption
    with open(file_pref + '_5_caption.json') as json_file:
        caption_data = json.load(json_file)

    # sort caption results based on frame number
    caption_data = sorted(caption_data['imgblobs'], key=lambda x:int(x['img_path'].split('/')[-1].split('.')[0]))

    caption_dict = {}
    for item in caption_data:
        image_path = item['img_path']
        caption_dict[image_path] = {'rnn_time': item['rnn_time'], 'candidate': item['candidate']}

    return caption_data, caption_dict


def load_video_blur(blur_folder, video_name):

    file_pref = os.path.join(BLUR_folder, video_name)

    # load blurinfo
    with open(file_pref + '_blur.json') as json_file:
        blur_data = json.load(json_file)

    blur_data = sorted(blur_data['img_blobs'], key=lambda x:int(x['img_name'].split('.')[0]))

    return blur_data



def load_video_summary(summary_folder, video_name):

    file_pref = os.path.join(summary_folder, video_name)

    # load caption
    with open(file_pref + '_5_caption.json') as json_file:
        caption_data = json.load(json_file)

    # sort caption results based on frame number
    caption_data = sorted(caption_data['imgblobs'], key=lambda x:int(x['img_path'].split('/')[-1].split('.')[0]))

    # load recognition
    with open(file_pref + '_recog.json') as json_file:
        recog_data = json.load(json_file)

    recog_data = sorted(recog_data['imgblobs'], key=lambda x: int(x['img_path'].split('/')[-1].split('.')[0]))

    # load blurinfo
    with open(file_pref + '_blur.json') as json_file:
        blur_data = json.load(json_file)

    blur_data = sorted(blur_data['img_blobs'], key=lambda x:int(x['img_name'].split('.')[0]))

    return caption_data, recog_data, blur_data

