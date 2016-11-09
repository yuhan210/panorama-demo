import redis
import pickle
import math
with open('./lib/data/video_list.txt') as fh:
    video_names = fh.read().split()

with open('../data/stream_rates.pickle') as fh:
    video_frame_rate = pickle.load(fh)    

with open('./lib/data/video_frame_num.pickle') as fh:
    video_lengths = pickle.load(fh)
 

if __name__ == "__main__":

    video_length_in_sec = {}
    for video_name in video_names:
        frame_num = video_lengths[video_name]
        video_length_in_sec[video_name] = int(math.floor(video_lengths[video_name]/video_frame_rate[video_name][0]))

    _redis = redis.StrictRedis()
    for vid, video_name in enumerate(video_names):
        is_none = False
        if vid > 366:
            break
        for ts in xrange(5, video_length_in_sec[video_name]):
            redis_feature_key = str(ts) + ':' + str(vid)
            feature_pickle = _redis.get(redis_feature_key)  
            
            if feature_pickle != None:
                feature_dict =  pickle.loads(feature_pickle)
                #print feature_dict
            else:
                is_none = True
                print ts, video_length_in_sec[video_name], video_lengths[video_name], video_frame_rate[video_name][0]
        if is_none:
            print vid, video_name
